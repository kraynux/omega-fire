# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran de gestion des modeles (presets) de jail, utilise par
CreateJailScreen (4.4, mode "Modele/Preset"). Meme patron liste + CRUD
que PinnedPathsScreen (Phase 2), avec un formulaire d'ajout a 8 champs
au lieu d'un seul. Logique identique au sous-menu presets de
interfaces/cli/actions.py::action_4_4_create_jail."""
from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, DataTable, Footer, Header, Input, Static

from omega_fire.application.commands.manage_jail_presets import ManageJailPresetsCommand
from omega_fire.infrastructure.config.paths import RUNTIME_DIR
from omega_fire.infrastructure.storage.files.json_store import JsonStore
from omega_fire.interfaces.tui.screens._base import OmegaScreen

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_FIELDS: tuple[tuple[str, str, str], ...] = (
    ("name", "Nom du preset (identifiant)", "ex. my-app-access"),
    ("desc", "Description courte", ""),
    ("log", "Chemin du fichier de log", ""),
    ("port", "Port(s) cible(s)", "ex. http,https ou ssh"),
    ("filter", "Nom du filtre Fail2ban", ""),
    ("retry", "Max Retry", "5"),
    ("find", "Findtime", "10m"),
    ("ban", "Bantime", "1h"),
)


class JailPresetsScreen(OmegaScreen):
    """Gestion des modeles de jail reutilisables (menu 4.4)."""

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container
        self._command = ManageJailPresetsCommand(JsonStore(RUNTIME_DIR))
        self._selected_name: str | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(classes="omega-panel"):
            yield Static("MODELES DE JAIL", classes="omega-title")
            yield DataTable(id="presets-table")

            yield Static("Ajouter un modele", classes="omega-subtitle")
            for key, label, placeholder in _FIELDS:
                yield Static(label, classes="omega-hint")
                yield Input(placeholder=placeholder, id=f"field-{key}")

            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button("Ajouter", id="add", variant="primary")
                with Container(classes="omega-btn-frame"):
                    yield Button("Retirer la selection", id="remove", variant="error")
                with Container(classes="omega-btn-frame"):
                    yield Button("Retour", id="back")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#presets-table", DataTable)
        table.cursor_type = "row"
        table.add_columns("Nom", "Description")
        self._refresh()

    def _refresh(self) -> None:
        table = self.query_one("#presets-table", DataTable)
        table.clear()
        for p in self._command.list_presets():
            table.add_row(p["name"], p["desc"], key=p["name"])

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        self._selected_name = str(event.row_key.value)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss()
            return
        if event.button.id == "add":
            self._add_preset()
            return
        if event.button.id == "remove":
            self._remove_selected()

    def _add_preset(self) -> None:
        new_preset: dict[str, str] = {}
        for key, label, _ in _FIELDS:
            value = self.query_one(f"#field-{key}", Input).value.strip()
            if not value:
                self.app.notify(f"Champ requis : {label}.", severity="warning")
                return
            new_preset[key] = value

        result = self._command.add_preset(new_preset)
        if result.success:
            self.app.notify(result.message)
            for key, _, _ in _FIELDS:
                self.query_one(f"#field-{key}", Input).value = ""
            self._refresh()
        else:
            self.app.notify(result.message, severity="error")

    def _remove_selected(self) -> None:
        if self._selected_name is None:
            self.app.notify("Selectionnez d'abord une ligne.", severity="warning")
            return
        result = self._command.remove_preset(self._selected_name)
        if result.success:
            self.app.notify(result.message)
        else:
            self.app.notify(result.message, severity="error")
        self._selected_name = None
        self._refresh()
