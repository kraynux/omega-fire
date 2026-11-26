# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 3.6 — Bouclier du port WireGuard (3.7.0, omega-lib D-018, demande omega-tail lot 8).

Etat, origine (outil qui l'a demande), gestionnaire, mode et compteurs du bouclier pose devant tailscaled ;
poser, passer en actif ou en observation, reprendre la gestion d'un bouclier pose par omega-tail, reposer
une table effacee par un autre outil, retirer. Les commandes passent par application/commands/wg_shield.py."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from omega_lib.shield.models import ShieldMode
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, DataTable, Footer, Header, Static

from omega_fire.application.commands.wg_shield import (
    OMEGA_FIRE,
    ShieldOutcome,
    ShieldView,
    WgShieldService,
)
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.screens.confirm import ConfirmScreen
from omega_fire.shared.i18n import N_, _

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

COUNTER_LABELS: tuple[tuple[str, str, str], ...] = (
    ("peer", N_("Pairs connus"), N_("admis")),
    ("init", N_("Poignées de main"), N_("admises")),
    ("init_over", N_("Poignées de main en excès (par source)"), N_("refusées")),
    ("unknown", N_("Sources inconnues, paquets bien formés"), N_("admis")),
    ("unknown_over", N_("Sources inconnues en excès (par source)"), N_("refusés")),
    ("global_over", N_("Excès de l'ensemble des sources inconnues"), N_("refusés")),
    ("other", N_("Paquets qui ne sont pas du WireGuard"), N_("refusés")),
)
REASON_MESSAGES: dict[str, str] = {
    "pose": N_("Bouclier posé : omega-fire le remet en place à chaque démarrage."),
    "mode": N_("Mode changé : compteurs et pairs connus gardés."),
    "gestion": N_("omega-fire gère maintenant le bouclier (rien d'autre n'a changé)."),
    "repose": N_("Bouclier remis en place (compteurs remis à zéro)."),
    "retire": N_("Bouclier retiré : table, fichiers et service supprimés."),
    "absent": N_("Aucun bouclier enregistré sur cette machine."),
    "port-aleatoire": N_("tailscaled tire son port au hasard (--port 0) : aucun bouclier possible. "
                         "Fixez un port (PORT= dans /etc/default/tailscaled)."),
    "aucune-carte": N_("Aucune carte réseau matérielle trouvée."),
    "invalide": N_("Réglages refusés (port ou carte réseau invalide)."),
    "redemarrage": N_("Le noyau a été mis à jour sans redémarrage : ses modules ne peuvent plus être chargés et "
                      "la table serait refusée. Redémarrez la machine, puis recommencez."),
}


def view_lines(view: ShieldView) -> Text:
    """Etat lisible (aussi lu par les essais)."""
    text = Text()
    settings, status = view.settings, view.status
    if not view.installed and not view.present:
        text.append(_("Aucun bouclier sur cette machine.") + "\n", style="bold")
        text.append(_("Port de tailscaled : {port} ; cartes réseau : {devices}.").format(
            port=view.port or _("au hasard"), devices=", ".join(view.devices) or "—") + "\n")
        if not view.egress:
            text.append(_("Noyau antérieur à 5.16 : sans liste des pairs, seuls le tri des paquets et la limite "
                          "des poignées de main seront posés.") + "\n")
        return text
    if view.missing:
        text.append(_("ABSENT : la table a été effacée par un autre outil (nft flush ruleset, redémarrage d'un "
                      "service de pare-feu…). « Reposer » la remet.") + "\n", style="bold red")
    elif view.stale:
        text.append(_("État non mis à jour depuis plus de 3 minutes : le service omega-bouclier-wg est-il "
                      "arrêté ?") + "\n", style="bold yellow")
    elif status is not None and status.mode is ShieldMode.ACTIVE:
        text.append(_("ACTIF : les paquets en excès et ceux qui ne sont pas du WireGuard sont refusés.") + "\n",
                    style="bold green")
    else:
        text.append(_("OBSERVATION : rien n'est refusé ; les compteurs disent ce qui l'aurait été.") + "\n",
                    style="bold")
    text.append(_("Origine : {tool} (outil qui l'a demandé).").format(tool=view.requested_by or "?") + "\n")
    text.append(_("Géré par : {tool}.").format(tool=view.manager or "?") + "\n")
    if settings is not None:
        spec = settings.spec
        text.append(_("Port {port}/udp ; cartes réseau : {devices}.").format(
            port=spec.port, devices=", ".join(spec.devices)) + "\n")
        if not spec.egress:
            text.append(_("Sans liste des pairs (noyau antérieur à 5.16).") + "\n")
    if status is not None and status.present:
        text.append(_("Pairs connus : {count}.").format(count=status.peers) + "\n")
    return text


class WgShieldScreen(OmegaScreen):
    def __init__(self, *, container: DependencyContainer | None = None,
                 service: WgShieldService | None = None) -> None:
        super().__init__()
        self._container = container
        self._service = service
        self._view: ShieldView | None = None

    def _shield(self) -> WgShieldService:
        if self._service is None:
            if self._container is not None:
                self._service = self._container.wg_shield
            else:
                from omega_fire.app.dependency_container import DependencyContainer

                self._service = DependencyContainer().wg_shield
        return self._service

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="omega-panel"):
            yield Static(_("BOUCLIER DU PORT WIREGUARD"), classes="omega-title")
            yield Static(_("Devant tailscaled (Tailscale) : poignées de main limitées par source, budget pour les "
                           "sources qui ne sont pas des pairs connus, paquets qui ne sont pas du WireGuard "
                           "refusés. Commencez en observation."), classes="omega-hint")
            yield Static("", id="shield-state")
            yield DataTable(id="shield-counters")
            yield Static("", id="shield-result", classes="omega-hint")
        with Horizontal(classes="omega-actions", id="shield-actions"):
            for button_id, label, variant in (("pose", _("Poser (observation)"), "primary"),
                                              ("mode", _("Passer en actif"), "default"),
                                              ("take", _("Reprendre la gestion"), "default"),
                                              ("repose", _("Reposer"), "primary"),
                                              ("remove", _("Retirer"), "error")):
                with Container(classes="omega-btn-frame", id=f"frame-{button_id}"):
                    yield Button(label, id=button_id, variant=variant)  # type: ignore[arg-type]
        with Horizontal(classes="omega-actions"):
            with Container(classes="omega-btn-frame"):
                yield Button(_("Actualiser"), id="refresh")
            with Container(classes="omega-btn-frame"):
                yield Button(_("Retour"), id="back")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#shield-counters", DataTable)
        table.add_columns(_("Compteur"), _("Paquets"), _("Effet"))
        self.refresh_view()

    def refresh_view(self) -> None:
        self.run_blocking(lambda: self._shield().view(), self._show, busy_message=None)

    def _show(self, view: ShieldView) -> None:
        self._view = view
        self.query_one("#shield-state", Static).update(view_lines(view))
        table = self.query_one("#shield-counters", DataTable)
        table.clear()
        status = view.status
        active = status is not None and status.mode is ShieldMode.ACTIVE
        if status is not None and status.present:
            for field_name, label, effect in COUNTER_LABELS:
                shown = _(effect) if active or effect in (N_("admis"), N_("admises")) else _("auraient été refusés")
                table.add_row(_(label), str(getattr(status.counters, field_name)), shown)
        visible = {
            "pose": not view.installed and not view.present,
            "mode": view.installed and view.present,
            "take": view.installed and view.manager != OMEGA_FIRE,
            "repose": view.missing,
            "remove": view.installed or view.present,
        }
        for button_id, shown_button in visible.items():
            self.query_one(f"#frame-{button_id}").display = shown_button
        self.query_one("#mode", Button).label = _("Passer en observation") if active else _("Passer en actif")

    def _after(self, outcome: ShieldOutcome) -> None:
        if outcome.ok:
            message = _(REASON_MESSAGES.get(outcome.reason, outcome.reason))
            self.app.notify(message)
        else:
            message = _(REASON_MESSAGES[outcome.reason]) if outcome.reason in REASON_MESSAGES else _(
                "Échec : {error}").format(error=outcome.error or "?")
            self.app.notify(message, severity="error")
        self.query_one("#shield-result", Static).update(Text(message))
        self._show(outcome.view)

    def _act(self, work: Callable[[], ShieldOutcome]) -> None:
        self.run_blocking(work, self._after)

    def _confirm(self, title: str, message: str, work: Callable[[], ShieldOutcome]) -> None:
        def done(confirmed: bool | None) -> None:
            if confirmed:
                self._act(work)
        self.app.push_screen(ConfirmScreen(title=title, message=message, help_node="3.6"), done)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button = event.button.id or ""
        service, view = self._shield(), self._view
        if button == "back":
            self.dismiss()
        elif button == "refresh":
            self.refresh_view()
        elif button == "pose":
            self._act(lambda: service.pose(ShieldMode.OBSERVE, OMEGA_FIRE))
        elif button == "mode" and view is not None:
            status = view.status
            if status is not None and status.mode is ShieldMode.ACTIVE:
                self._act(lambda: service.set_mode(ShieldMode.OBSERVE))
                return
            refused = status.counters.refused if status is not None else 0
            self._confirm(_("Passer le bouclier en actif"),
                          _("En observation, {count} paquet(s) auraient été refusés. En actif, ils le seront. "
                            "Les pairs connus ne sont jamais limités.").format(count=refused),
                          lambda: service.set_mode(ShieldMode.ACTIVE))
        elif button == "take":
            self._act(service.take_over)
        elif button == "repose":
            self._act(service.repose)
        elif button == "remove" and view is not None:
            origin = view.requested_by
            extra = (_(" Il a été demandé par {tool}, qui l'affichera « retiré depuis omega-fire ».").format(
                tool=origin) if origin and origin != OMEGA_FIRE else "")
            self._confirm(_("Retirer le bouclier"),
                          _("La table, ses fichiers et son service seront supprimés ; tailscaled ne sera plus "
                            "protégé contre les flots de paquets.") + extra, service.remove)
