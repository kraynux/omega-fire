# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 4.6 — Vider toutes les IPs bannies d'un jail. Patron #2 + une
confirmation destructive (patron #1). Logique identique a
interfaces/cli/actions.py::action_4_6_clear_jail : selection du jail,
confirmation, debannissement groupe via Fail2banPort.flush_jail().

get_jail_status()/flush_jail() (fail2ban-client, jusqu'a 10s de timeout
chacun) s'executent en arriere-plan (run_blocking, voir _base.py) —
synchrones dans __init__/le handler de confirmation, ils gelaient TOUTE
l'app (retour utilisateur reel, mode degrade)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Select, Static

from omega_fire.application.queries.jail_status import get_jail_status
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.screens.confirm import ConfirmScreen
from omega_fire.interfaces.tui.support.action_audit import log_action_result

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ACTION_TITLE = "4.6 Vider les IPs d'un Jail Fail2ban"


class ClearJailScreen(OmegaScreen):
    """Vidage complet (debannissement groupe) d'un jail choisi."""

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container
        self._fail2ban_port = None
        self._jails: dict[str, int] = {}

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="omega-form-panel"):
            yield Static("VIDER LES IPs D'UN JAIL", classes="omega-title")
            yield Static("Chargement des jails...", id="status-hint", classes="omega-hint")
            yield Static("Jail", id="jail-label", classes="omega-subtitle omega-hidden")
            yield Select([], id="jail-select", classes="omega-hidden")
            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button("Vider", id="launch", variant="error", disabled=True)
                with Container(classes="omega-btn-frame"):
                    yield Button("Retour", id="back")
        yield Footer()

    def on_mount(self) -> None:
        def _fetch():
            try:
                fail2ban_port = self._container.get_fail2ban_port()
            except Exception:
                fail2ban_port = None
            status = get_jail_status(fail2ban_port=fail2ban_port)
            return fail2ban_port, {j.name: j.banned_count for j in status.jails}

        self.run_blocking(_fetch, self._on_loaded, busy_message="Chargement des jails...")

    def _on_loaded(self, result) -> None:
        fail2ban_port, jails = result
        self._fail2ban_port = fail2ban_port
        self._jails = jails

        if not jails:
            self.query_one("#status-hint", Static).update("Impossible de communiquer avec le service Fail2ban.")
            return

        self.query_one("#status-hint", Static).set_class(True, "omega-hidden")
        self.query_one("#jail-label", Static).set_class(False, "omega-hidden")
        jail_select = self.query_one("#jail-select", Select)
        jail_select.set_class(False, "omega-hidden")
        jail_select.set_options([(f"{name} ({count} IP(s) bannie(s))", name) for name, count in jails.items()])
        jail_select.value = next(iter(jails))
        self.query_one("#launch", Button).disabled = False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss()
            return
        if event.button.id != "launch" or not self._jails:
            return

        jail_name = str(self.query_one("#jail-select", Select).value)
        ip_count = self._jails.get(jail_name, 0)
        if ip_count == 0:
            self.app.notify(f"Le jail '{jail_name}' est deja totalement vide.", severity="information")
            return

        self.app.push_screen(
            ConfirmScreen(
                title="CONFIRMER LE VIDAGE",
                message=f"Debannir {ip_count} IP(s) du jail '{jail_name}' ?",
            ),
            lambda confirmed: self._clear_if_confirmed(confirmed, jail_name),
        )

    def _clear_if_confirmed(self, confirmed: bool | None, jail_name: str) -> None:
        if not confirmed:
            return

        def _execute() -> int:
            return self._fail2ban_port.flush_jail(jail_name)

        def _on_done(unbanned_count: int) -> None:
            self.app.notify(f"Jail '{jail_name}' totalement vide ({unbanned_count} IP(s) retiree(s)).")
            log_action_result(self._container, _ACTION_TITLE, status="success")
            self.dismiss()

        def _on_error(error: Exception) -> None:
            self.app.notify(f"Echec du vidage du jail '{jail_name}' : {error}", severity="error")
            log_action_result(self._container, _ACTION_TITLE, status="failure", error=str(error))

        self.run_blocking(_execute, _on_done, busy_message=f"Vidage du jail '{jail_name}'...", on_error=_on_error)
