# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 2.6 — Synchroniser les backends NFt-IPt. Patron #2 (formulaire
court, un seul champ). Logique identique a
interfaces/cli/actions.py::action_2_6_sync_backends."""
from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Select, Static

from omega_fire.application.commands.sync_backends import SyncBackendsCommand
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.support.action_audit import log_action_result

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ACTION_TITLE = "2.6 Synchroniser les backends"
_ALL_BACKENDS = "__all__"


class SyncBackendsScreen(OmegaScreen):
    """Reconciliation des backends pare-feu entre eux (Nft <-> Ipt)."""

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container
        self._supported_backends = self._detect_supported_backends()

    def _detect_supported_backends(self) -> list[str]:
        supported = ["nftables", "iptables", "ip6tables"]
        try:
            if self._container.get_firewall_port("fail2ban") is not None:
                supported.append("fail2ban")
        except Exception:
            pass
        return supported

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="omega-form-panel"):
            yield Static("SYNCHRONISER LES BACKENDS", classes="omega-title")
            yield Static("Backend(s) a synchroniser", classes="omega-subtitle")
            options = [("Tous les backends", _ALL_BACKENDS)] + [
                (name, name) for name in self._supported_backends
            ]
            yield Select(options, value=_ALL_BACKENDS, id="backend-select")
            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button("Synchroniser", id="launch", variant="primary")
                with Container(classes="omega-btn-frame"):
                    yield Button("Retour", id="back")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss()
            return
        if event.button.id != "launch":
            return

        choice = str(self.query_one("#backend-select", Select).value)
        target_backends = (
            list(self._supported_backends) if choice == _ALL_BACKENDS else [choice]
        )

        adapters = {}
        for name in self._supported_backends:
            try:
                adapters[name] = self._container.get_firewall_port(name)
            except Exception:
                adapters[name] = None

        result = SyncBackendsCommand(adapters=adapters).execute(target_backends=target_backends)

        for outcome in result.outcomes:
            for err in outcome.errors:
                self.app.notify(f"Echec pour {err}", title=outcome.backend, severity="error")
            if outcome.added_count > 0:
                self.app.notify(f"{outcome.added_count} IP(s) manquante(s) ajoutee(s).", title=outcome.backend, severity="information")
            elif not outcome.errors:
                self.app.notify("Deja a jour (0 IP a ajouter).", title=outcome.backend, severity="information")

        if result.total_added == 0:
            self.app.notify("Tous les backends cibles etaient deja parfaitement synchronises.")
        else:
            self.app.notify(f"Synchronisation terminee : {result.total_added} IP(s) au total realignees.")

        log_action_result(self._container, _ACTION_TITLE, status="success")
        self.dismiss()
