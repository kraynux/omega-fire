# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecrans 1.1 (registre complet) et 1.4 (diagnostics recents = capacites
en incident uniquement) — meme donnee source (capability_registry.list_all()),
un seul ecran parametre plutot que deux quasi-identiques, meme raison que
_render_stats_report_screen() cote CLI pour 8.3/8.4."""
from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Static

from omega_fire.core.enums import CapabilityStatus
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.widgets.capabilities_table import CapabilitiesTable

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ISSUE_STATUSES = (CapabilityStatus.MISSING, CapabilityStatus.DEGRADED, CapabilityStatus.DISQUALIFIED)


class CapabilitiesScreen(OmegaScreen):
    """Registre des capacites (1.1) ou diagnostics recents (1.4, issues
    uniquement) selon `only_issues`."""

    def __init__(self, *, container: DependencyContainer, only_issues: bool = False) -> None:
        super().__init__()
        self._container = container
        self._only_issues = only_issues

    def compose(self) -> ComposeResult:
        title = "DIAGNOSTICS RECENTS" if self._only_issues else "REGISTRE DES CAPACITES"
        yield Header()
        with Vertical(classes="omega-panel"):
            yield Static(title, classes="omega-title")
            yield CapabilitiesTable(id="capabilities-table")
            with Horizontal(classes="omega-actions"), Container(classes="omega-btn-frame"):
                yield Button("Retour", id="back")
        yield Footer()

    def on_mount(self) -> None:
        capabilities = self._container.capability_registry.list_all()
        if self._only_issues:
            capabilities = [c for c in capabilities if c.status in _ISSUE_STATUSES]
        table = self.query_one(CapabilitiesTable)
        table.set_capabilities(capabilities)
        if self._only_issues and not capabilities:
            self.query_one("#capabilities-table", CapabilitiesTable).display = False
            self.mount(
                Static(
                    "Aucun incident ni diagnostic d'erreur. Tout le systeme est operationnel.",
                    classes="omega-hint",
                ),
                after=self.query_one(".omega-title"),
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss()
