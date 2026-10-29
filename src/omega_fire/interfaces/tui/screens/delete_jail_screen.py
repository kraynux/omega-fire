# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 4.5 — Supprimer un jail Fail2ban (arret, fichiers .conf/.local,
filtre associe, rechargement — tout gere par Fail2banPort.delete_jail()).
Patron #2 + confirmation destructive. Logique identique a
interfaces/cli/actions.py::action_4_5_delete_jail.

La collecte (list_configured_jail_files()/get_jail_status()) et la
suppression (delete_jail(), qui recharge le service) s'executent en
arriere-plan (run_blocking, voir _base.py) — synchrones dans __init__/le
handler de confirmation, elles gelaient TOUTE l'app (retour utilisateur
reel, mode degrade)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Select, Static

from omega_fire.application.queries.jail_status import get_jail_status
from omega_fire.domain.fail2ban.definitions import (
    BLOCKED_MAIN_CONFIG,
    BLOCKED_SHARED_FILE,
    ORIGIN_OMEGA_JAIL,
    JailDefinition,
)
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.screens.confirm import ConfirmScreen
from omega_fire.interfaces.tui.support.action_audit import log_action_result
from omega_fire.interfaces.tui.support.jail_origin import origin_label
from omega_fire.shared.i18n import _

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ACTION_TITLE = "4.5 Suppression et Désactivation de Jail Fail2ban"


class DeleteJailScreen(OmegaScreen):
    """Suppression complete (arret + config + filtre) d'un jail configure."""

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container
        self._fail2ban_port = None
        self._jail_files: dict[str, str] = {}
        self._definitions: dict[str, JailDefinition] = {}

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="omega-form-panel"):
            yield Static(_("SUPPRIMER UN JAIL"), classes="omega-title")
            yield Static(_("Chargement des jails..."), id="status-hint", classes="omega-hint")
            yield Static(_("Jail"), id="jail-label", classes="omega-subtitle omega-hidden")
            yield Select([], id="jail-select", classes="omega-hidden", prompt=_("Sélectionner"))
            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Supprimer"), id="launch", variant="error", disabled=True)
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Retour"), id="back")
        yield Footer()

    def on_mount(self) -> None:
        self.run_blocking(self._collect_jail_files, self._on_loaded, busy_message=_("Chargement des jails..."))

    def _collect_jail_files(self) -> tuple:
        try:
            fail2ban_port = self._container.get_fail2ban_port()
        except Exception:
            fail2ban_port = None

        jail_files: dict[str, str] = {}
        if fail2ban_port is not None:
            try:
                jail_files = dict(fail2ban_port.list_configured_jail_files())
            except Exception:
                jail_files = {}
        definitions: dict[str, JailDefinition] = {}
        if fail2ban_port is not None:
            try:
                definitions = dict(fail2ban_port.jail_definitions())
            except Exception:
                definitions = {}
        status_result = get_jail_status(fail2ban_port=fail2ban_port)
        for j in status_result.jails:
            if j.name not in jail_files:
                # Version 3.5 : le vrai fichier (section [nom]), sinon jail.local / jail.conf.
                definition = definitions.get(j.name)
                jail_files[j.name] = ", ".join(definition.files) if definition else _("(fichier introuvable)")
        return fail2ban_port, jail_files, definitions

    def _on_loaded(self, result) -> None:
        fail2ban_port, jail_files, definitions = result
        self._fail2ban_port = fail2ban_port
        self._jail_files = jail_files
        self._definitions = definitions

        if not jail_files:
            self.query_one("#status-hint", Static).update(
                _("Aucun jail personnalisé ou actif n'a été trouvé dans '/etc/fail2ban/jail.d/'.")
            )
            return

        self.query_one("#status-hint", Static).set_class(True, "omega-hidden")
        self.query_one("#jail-label", Static).set_class(False, "omega-hidden")
        jail_select = self.query_one("#jail-select", Select)
        jail_select.set_class(False, "omega-hidden")
        jail_select.set_options([
            (_("{name} — {origin} ({path})").format(
                name=name, path=path, origin=origin_label(getattr(self._definitions.get(name), "origin", None))), name)
            for name, path in sorted(jail_files.items())
        ])
        jail_select.value = sorted(jail_files)[0]
        self.query_one("#launch", Button).disabled = False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss()
            return
        if event.button.id != "launch" or not self._jail_files:
            return

        jail_name = str(self.query_one("#jail-select", Select).value)
        conf_file = self._jail_files.get(jail_name, "")
        definition = self._definitions.get(jail_name)
        # Version 3.5 (point 7) : jamais supprimer un fichier qui porte d'autres reglages.
        if definition is not None and definition.blocked == BLOCKED_MAIN_CONFIG:
            self.app.notify(
                _("« {jail_name} » est défini dans la configuration principale de fail2ban ({files}) : "
                  "omega-fire ne la modifie pas. Pour le désactiver, créez /etc/fail2ban/jail.d/{jail_name}.local "
                  "avec une section au nom du jail contenant « enabled = false », puis rechargez "
                  "fail2ban (4.10).").format(jail_name=jail_name, files=", ".join(definition.files)),
                severity="warning", timeout=15)
            return
        if definition is not None and definition.blocked == BLOCKED_SHARED_FILE:
            self.app.notify(
                _("« {jail_name} » partage son fichier ({files}) avec d'autres jails ({others}) : le "
                  "supprimer les effacerait aussi. Retirez sa section à la main, puis rechargez "
                  "fail2ban (4.10).").format(jail_name=jail_name, files=", ".join(definition.files),
                                              others=", ".join(definition.shared_with)),
                severity="warning", timeout=15)
            return
        message = _("Supprimer définitivement le jail '{jail_name}' ?\nFichier impacte : {conf_file}").format(
            jail_name=jail_name, conf_file=conf_file)
        if definition is not None and definition.origin == ORIGIN_OMEGA_JAIL:
            message += "\n\n" + _(
                "Ce jail a été installé par omega-jail : son filtre est supprimé avec lui. omega-jail le "
                "recréera à sa prochaine installation (« omega-jail --apply »). Pour l'écarter "
                "durablement, ne relancez pas cette installation, ou retirez-le du catalogue d'omega-jail.")
        self.app.push_screen(
            ConfirmScreen(title=_("CONFIRMER LA SUPPRESSION"), message=message),
            lambda confirmed: self._delete_if_confirmed(confirmed, jail_name),
        )

    def _delete_if_confirmed(self, confirmed: bool | None, jail_name: str) -> None:
        if not confirmed:
            return

        def _execute() -> None:
            if self._fail2ban_port is None:
                raise RuntimeError(_("Port Fail2ban indisponible (conteneur non initialisé)."))
            self._fail2ban_port.delete_jail(jail_name)

        def _on_done(_result: None) -> None:
            self.app.notify(_("Jail '{jail_name}' arrêté et supprimé. Service Fail2ban recharge.").format(jail_name=jail_name))
            log_action_result(self._container, _ACTION_TITLE, status="success")
            self.dismiss()

        def _on_error(error: Exception) -> None:
            self.app.notify(_("Erreur lors de la suppression du jail : {error}").format(error=error), severity="error")
            log_action_result(self._container, _ACTION_TITLE, status="failure", error=str(error))

        self.run_blocking(_execute, _on_done, busy_message=_("Suppression du jail '{jail_name}'...").format(jail_name=jail_name), on_error=_on_error)
