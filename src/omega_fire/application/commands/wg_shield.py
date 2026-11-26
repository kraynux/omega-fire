# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Bouclier du port WireGuard (3.7.0, omega-lib D-018, demande omega-tail lot 8).

Table `netdev omega_bouclier_wg` posee devant tailscaled : poignees de main limitees par source, budget pour les
sources qui ne sont pas des pairs connus, paquets mal formes refuses ; observation d'abord (rien n'est refuse,
les compteurs disent ce qui l'aurait ete). Tout le texte (table, script, service) vient d'omega_lib.shield : le
meme bouclier pose par omega-tail sans omega-fire est reconnu ici et se reprend d'un bouton.

Le bouclier n'est pas une regle de la base : une ligne a part dans la liste des regles (3.3), avec son origine
(l'outil qui l'a demande) et son gestionnaire (l'outil qui le remet au demarrage et lance ses commandes).

Raisons rendues (`reason`, codes stables lus par omega-tail, jamais traduits ici) : pose, mode, gestion, repose,
retire, absent, port-aleatoire, aucune-carte, invalide, echec."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from omega_lib.shield.models import ShieldMode, ShieldSettings, ShieldSpec, ShieldStatus
from omega_lib.shield.policies import kernel_supports_egress, validate
from omega_lib.shield.system import (
    install_commands,
    manager_commands,
    mode_commands,
    remove_commands,
    repose_commands,
    staged_files,
)

from omega_fire.ports.wg_shield import CommandLine, WgShieldPort

OMEGA_FIRE = "omega-fire"


@dataclass(frozen=True)
class ShieldView:
    settings: ShieldSettings | None
    status: ShieldStatus | None
    now: float
    port: int
    """Port de tailscaled lu sur la machine (0 : au hasard)."""
    devices: tuple[str, ...]
    egress: bool
    init: str

    @property
    def installed(self) -> bool:
        return self.settings is not None

    @property
    def stale(self) -> bool:
        """Bouclier enregistre dont l'etat est absent ou trop ancien : son service ne tourne plus."""
        return self.installed and (self.status is None or self.status.stale(self.now))

    @property
    def present(self) -> bool:
        return self.status is not None and self.status.present

    @property
    def missing(self) -> bool:
        """Enregistre mais plus dans le noyau : un autre outil l'a efface (alerte, on ne repose pas seul)."""
        return self.installed and self.status is not None and not self.status.present

    @property
    def requested_by(self) -> str:
        if self.settings is not None:
            return self.settings.spec.requested_by
        return self.status.requested_by if self.status is not None else ""

    @property
    def manager(self) -> str:
        return self.settings.manager if self.settings is not None else ""


@dataclass(frozen=True)
class ShieldOutcome:
    ok: bool
    reason: str
    view: ShieldView
    lines: list[CommandLine] = field(default_factory=list)

    @property
    def error(self) -> str:
        failed = [line for line in self.lines if line.code != 0]
        return failed[-1].detail if failed else ""


class WgShieldService:
    def __init__(self, system: WgShieldPort) -> None:
        self._system = system

    def view(self, *, refresh: bool = True) -> ShieldView:
        system = self._system
        return ShieldView(system.settings(), system.status(refresh=refresh), system.now(), system.tailscaled_port(),
                          system.devices(), kernel_supports_egress(system.kernel_release()), system.init_name())

    def _done(self, ok: bool, reason: str, lines: list[CommandLine]) -> ShieldOutcome:
        return ShieldOutcome(ok and all(line.code == 0 for line in lines), reason if ok else "echec", self.view(),
                             lines)

    def _apply(self, settings: ShieldSettings, commands_for: str, mode: ShieldMode | None = None) -> list[CommandLine]:
        system = self._system
        init = system.init_name()
        staging = system.stage(staged_files(settings, init))
        if commands_for == "pose":
            return system.run(install_commands(staging, init, system.runit_dir()))
        if commands_for == "mode" and mode is not None:
            return system.run(mode_commands(staging, mode))
        return system.run(manager_commands(staging))

    def pose(self, mode: ShieldMode, requested_by: str, *, port: int | None = None,
             devices: tuple[str, ...] | None = None) -> ShieldOutcome:
        """Poser (ou reposer avec de nouveaux reglages) : omega-fire en devient le gestionnaire."""
        view = self.view(refresh=False)
        chosen_port = view.port if port is None else port
        if not self._system.modules_ready():
            return ShieldOutcome(False, "redemarrage", view)
        if chosen_port == 0:
            return ShieldOutcome(False, "port-aleatoire", view)
        chosen_devices = view.devices if devices is None else devices
        if not chosen_devices:
            return ShieldOutcome(False, "aucune-carte", view)
        try:
            spec = validate(ShieldSpec(chosen_port, tuple(chosen_devices), mode, requested_by, egress=view.egress))
        except ValueError:
            return ShieldOutcome(False, "invalide", view)
        return self._done(True, "pose", self._apply(ShieldSettings(spec, OMEGA_FIRE), "pose"))

    def set_mode(self, mode: ShieldMode) -> ShieldOutcome:
        settings = self._system.settings()
        if settings is None:
            return ShieldOutcome(False, "absent", self.view(refresh=False))
        updated = ShieldSettings(replace(settings.spec, mode=mode), settings.manager)
        return self._done(True, "mode", self._apply(updated, "mode", mode))

    def take_over(self) -> ShieldOutcome:
        """Reprise par omega-fire d'un bouclier gere par omega-tail : seul le gestionnaire inscrit change (table,
        compteurs, pairs appris et service intacts)."""
        settings = self._system.settings()
        if settings is None:
            return ShieldOutcome(False, "absent", self.view(refresh=False))
        if settings.manager == OMEGA_FIRE:
            return ShieldOutcome(True, "gestion", self.view(refresh=False))
        return self._done(True, "gestion", self._apply(ShieldSettings(settings.spec, OMEGA_FIRE), "manager"))

    def repose(self) -> ShieldOutcome:
        """Remettre la table enregistree (effacee par un autre outil) : compteurs et pairs repartent de zero."""
        if self._system.settings() is None:
            return ShieldOutcome(False, "absent", self.view(refresh=False))
        if not self._system.modules_ready():
            return ShieldOutcome(False, "redemarrage", self.view(refresh=False))
        return self._done(True, "repose", self._system.run(repose_commands()))

    def remove(self) -> ShieldOutcome:
        """Retrait complet (table, fichiers, service), meme demande par un autre outil (decision B du lot 8 :
        omega-tail affiche ensuite « retire depuis omega-fire »)."""
        system = self._system
        if system.settings() is None and not (system.status(refresh=True) or ShieldStatus(False, 0)).present:
            return ShieldOutcome(True, "absent", self.view(refresh=False))
        lines = system.run(remove_commands(system.init_name(), system.runit_dir()), keep_going=True)
        view = self.view(refresh=False)
        # Arreter un service deja arrete n'est pas une erreur (commandes tolerantes d'omega-lib)
        ok = view.settings is None and all(line.code == 0 for line in lines)
        return ShieldOutcome(ok, "retire" if ok else "echec", view, lines)
