# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 7.1 — Sauvegarder l'etat complet (regles firewall, IPs bannies).
Patron #2 (un seul champ facultatif) + confirmation. Logique identique a
interfaces/cli/actions.py::action_7_1_backup_state."""
from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Input, Static

from omega_fire.application.commands.backup_state import BackupStateCommand, BackupStateRequest
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.screens.confirm import ConfirmScreen
from omega_fire.interfaces.tui.support.action_audit import log_action_result
from omega_fire.shared.i18n import _

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ACTION_TITLE = "7.1 Sauvegarder l'état"


class BackupStateScreen(OmegaScreen):
    """Sauvegarde de l'etat complet : regles + IPs bannies (tous backends)."""

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="omega-form-panel"):
            yield Static(_("SAUVEGARDER L'ÉTAT COMPLET"), classes="omega-title")
            yield Static(
                _("Capture l'état actuel : règles firewall, IPs bannies (nftables/iptables/fail2ban)."),
                classes="omega-hint",
            )
            yield Static(_("Description (optionnelle)"), classes="omega-subtitle")
            yield Input(id="description-input")
            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Sauvegarder"), id="launch", variant="primary")
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Retour"), id="back")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss()
            return
        if event.button.id != "launch":
            return

        description = self.query_one("#description-input", Input).value.strip()
        self.app.push_screen(
            ConfirmScreen(
                title=_("CONFIRMER LA SAUVEGARDE"),
                message=_("Description : {value}").format(value=description or _('(aucune)')),
            ),
            lambda confirmed: self._backup_if_confirmed(confirmed, description),
        )

    def _backup_if_confirmed(self, confirmed: bool | None, description: str) -> None:
        if not confirmed:
            return

        def _execute():
            persistence_port = self._container.get_persistence_port()
            adapters = {
                "nftables": self._container.get_firewall_port("nftables"),
                "iptables": self._container.get_firewall_port("iptables"),
                "ip6tables": self._container.get_firewall_port("ip6tables"),
            }
            try:
                adapters["fail2ban"] = self._container.get_fail2ban_port()
            except Exception:
                adapters["fail2ban"] = None
            return BackupStateCommand(persistence_port=persistence_port, adapters=adapters).execute(
                BackupStateRequest(description=description)
            )

        def _on_done(result) -> None:
            if not result.success:
                self.app.notify(_("Échec de la sauvegarde : {message}").format(message=result.message), severity="error")
                log_action_result(self._container, _ACTION_TITLE, status="failure", error=result.message)
                return

            self.app.notify(
                _("Sauvegarde réussie ({value}) — {rules_count} règle(s), {blacklist_count} IP(s), {jails_count} jail(s).").format(value=result.snapshot_id or _('N/A'), rules_count=result.rules_count, blacklist_count=result.blacklist_count, jails_count=result.jails_count),
            )
            log_action_result(self._container, _ACTION_TITLE, status="success")
            self.dismiss()

        def _on_error(error: Exception) -> None:
            self.app.notify(_("Échec de la sauvegarde : {error}").format(error=error), severity="error")
            log_action_result(self._container, _ACTION_TITLE, status="failure", error=str(error))

        self.run_blocking(_execute, _on_done, busy_message=_("Sauvegarde en cours..."), on_error=_on_error)
