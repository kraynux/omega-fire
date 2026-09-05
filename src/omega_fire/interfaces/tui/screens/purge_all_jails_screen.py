# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 4.7 — Purge generale : vider TOUS les jails Fail2ban. Inventaire
affiche avant confirmation (patron #1), execution groupee via
Fail2banPort.flush_all_jails(). Logique identique a
interfaces/cli/actions.py::action_4_7_purge_all_jails.

get_jail_status()/flush_all_jails() (fail2ban-client, jusqu'a 10s de
timeout chacun) s'executent en arriere-plan (run_blocking, voir
_base.py) — synchrones dans __init__/le handler de confirmation, elles
gelaient TOUTE l'app (retour utilisateur reel, mode degrade)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, DataTable, Footer, Header, Static

from omega_fire.application.queries.jail_status import get_jail_status
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.screens.confirm import ConfirmScreen
from omega_fire.interfaces.tui.support.action_audit import log_action_result

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ACTION_TITLE = "4.7 Purge generale : vider tous les jails"


class PurgeAllJailsScreen(OmegaScreen):
    """Purge groupee (debannissement) de tous les jails Fail2ban."""

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container
        self._fail2ban_port = None
        self._jails: list[tuple[str, int]] = []
        self._total_banned = 0

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="omega-panel"):
            yield Static("PURGE GENERALE DES JAILS FAIL2BAN", classes="omega-title")
            yield Static("Chargement des jails...", id="status-hint", classes="omega-hint")
            yield DataTable(id="inventory-table", classes="omega-hidden")
            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button("Purger tout", id="launch", variant="error", disabled=True)
                with Container(classes="omega-btn-frame"):
                    yield Button("Retour", id="back")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#inventory-table", DataTable).add_columns("Nom du Jail", "IPs Bannies", "Statut")

        def _fetch():
            try:
                fail2ban_port = self._container.get_fail2ban_port()
            except Exception:
                fail2ban_port = None
            status = get_jail_status(fail2ban_port=fail2ban_port)
            return fail2ban_port, [(j.name, j.banned_count) for j in status.jails], status.total_banned_ips

        self.run_blocking(_fetch, self._on_loaded, busy_message="Chargement des jails...")

    def _on_loaded(self, result) -> None:
        fail2ban_port, jails, total_banned = result
        self._fail2ban_port = fail2ban_port
        self._jails = jails
        self._total_banned = total_banned

        if not jails:
            self.query_one("#status-hint", Static).update("Impossible de communiquer avec le service Fail2ban.")
            return

        self.query_one("#status-hint", Static).set_class(True, "omega-hidden")
        table = self.query_one("#inventory-table", DataTable)
        table.set_class(False, "omega-hidden")
        for name, count in jails:
            table.add_row(name, str(count), "Nettoyage requis" if count > 0 else "Deja vide")
        self.query_one("#launch", Button).disabled = False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss()
            return
        if event.button.id != "launch" or not self._jails:
            return
        if self._total_banned == 0:
            self.app.notify("Tous les jails sont deja vides.", severity="information")
            return

        self.app.push_screen(
            ConfirmScreen(
                title="CONFIRMER LA PURGE GENERALE",
                message=f"Debannir {self._total_banned} IP(s) sur {len(self._jails)} jail(s) ?",
            ),
            self._purge_if_confirmed,
        )

    def _purge_if_confirmed(self, confirmed: bool | None) -> None:
        if not confirmed:
            return

        def _on_done(purged_count: int) -> None:
            self.app.notify(f"Purge generale terminee : {purged_count} IP(s) debannie(s).")
            log_action_result(self._container, _ACTION_TITLE, status="success")
            self.dismiss()

        def _on_error(error: Exception) -> None:
            self.app.notify(f"Erreur lors de la purge globale : {error}", severity="error")
            log_action_result(self._container, _ACTION_TITLE, status="failure", error=str(error))

        self.run_blocking(
            self._fail2ban_port.flush_all_jails, _on_done,
            busy_message="Purge generale en cours...", on_error=_on_error,
        )
