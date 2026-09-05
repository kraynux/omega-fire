# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 1.2 (selection) — liste des capacites, la selection d'une ligne
pousse CapabilityDetailScreen. Meme patron que
omega-check/screens/history.py (D-008) : DataTable + selection de ligne
-> ecran de detail, plutot qu'une saisie de numero au clavier."""
from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, DataTable, Footer, Header, Static

from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.screens.capability_detail_screen import CapabilityDetailScreen
from omega_fire.interfaces.tui.widgets.capabilities_table import CapabilitiesTable

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer


class CapabilityPickerScreen(OmegaScreen):
    """Choix d'une capacite dans le registre, avant d'en voir le detail."""

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="omega-panel"):
            yield Static("DETAIL D'UNE CAPACITE", classes="omega-title")
            yield Static("Selectionnez une ligne pour voir le detail.", classes="omega-hint")
            yield CapabilitiesTable(id="capabilities-table")
            with Horizontal(classes="omega-actions"), Container(classes="omega-btn-frame"):
                yield Button("Retour", id="back")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(CapabilitiesTable).set_capabilities(self._container.capability_registry.list_all())

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self.app.push_screen(
            CapabilityDetailScreen(container=self._container, capability_id=str(event.row_key.value))
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss()
