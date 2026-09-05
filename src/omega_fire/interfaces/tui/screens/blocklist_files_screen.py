# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 2.7 — Gestion des fichiers blocklist (liste principale). Patron
#4 (liste + CRUD) : DataTable des fichiers, import depuis un chemin
externe (epingle ou saisie manuelle), creation d'un fichier vide,
selection de ligne -> ecran de detail (BlocklistFileDetailScreen), qui
porte le reste du CRUD (ajouter/retirer IP, renommer, supprimer, bannir
le contenu). Logique identique a la boucle principale de
interfaces/cli/actions.py::action_2_7_import_file.

La ligne d'import (2 Input + 1 Button dans un seul Horizontal) provoquait
un ascenseur horizontal qui cachait les boutons (retour utilisateur
reel) — chaque Input est desormais sur sa propre ligne, comme partout
ailleurs dans l'appli. Gestion des epingles ajoutee (meme mecanisme que
2.2/2.4/2.8/4.3/5.2/5.3/5.4 — blocklist_analysis_pinned_paths.json),
absente de cet ecran jusqu'ici bien que le CLI proposait deja une source
epinglee pour l'import."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, DataTable, Footer, Header, Input, Static

from omega_fire.application.commands.manage_blocklist_file import ManageBlocklistFileCommand
from omega_fire.application.commands.manage_pinned_log_paths import ManagePinnedLogPathsCommand
from omega_fire.infrastructure.config.paths import BLOCKLIST_DIR, DEFAULT_PINNED_FILES, RUNTIME_DIR
from omega_fire.infrastructure.storage.files.json_store import JsonStore
from omega_fire.infrastructure.storage.files.text_store import TextStore
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.screens.blocklist_file_detail_screen import BlocklistFileDetailScreen
from omega_fire.interfaces.tui.screens.pinned_paths_screen import PinnedPathsScreen
from omega_fire.interfaces.tui.widgets.pinned_paths_table import PinnedPathsTable

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer


class BlocklistFilesScreen(OmegaScreen):
    """Liste des fichiers blocklist geres, import (epingle ou manuel) et creation."""

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container
        self._manager = ManageBlocklistFileCommand(TextStore(BLOCKLIST_DIR))
        self._pinned_command = ManagePinnedLogPathsCommand(
            JsonStore(RUNTIME_DIR),
            relative_path="blocklist_analysis_pinned_paths.json",
            defaults=[str(p) for p in DEFAULT_PINNED_FILES],
        )

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="omega-panel"):
            yield Static("GESTION DES FICHIERS BLOCKLIST", classes="omega-title")
            yield DataTable(id="files-table")

            yield Static("Fichiers epingles (selectionnez pour prefiller le chemin source)", classes="omega-subtitle")
            yield PinnedPathsTable(id="pinned-table")
            with Horizontal(classes="omega-actions"), Container(classes="omega-btn-frame"):
                yield Button("Gerer les epingles", id="manage-pins")

            yield Static("Importer un fichier existant (epingle ou chemin manuel)", classes="omega-subtitle")
            yield Input(placeholder="Chemin complet du fichier source", id="import-path-input")
            yield Input(placeholder="Nom de destination (optionnel)", id="import-name-input")
            with Horizontal(classes="omega-actions"), Container(classes="omega-btn-frame"):
                yield Button("Importer", id="import")

            yield Static("Creer un nouveau fichier vide", classes="omega-subtitle")
            yield Input(placeholder="ex. custom.txt", id="create-name-input")
            with Horizontal(classes="omega-actions"), Container(classes="omega-btn-frame"):
                yield Button("Creer", id="create")

            with Horizontal(classes="omega-actions"), Container(classes="omega-btn-frame"):
                yield Button("Retour", id="back")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#files-table", DataTable)
        table.cursor_type = "row"
        table.add_columns("Fichier", "IPs valides", "A corriger")
        self._refresh()
        self._refresh_pinned()

    def _refresh_pinned(self) -> None:
        self.query_one(PinnedPathsTable).set_paths(self._pinned_command.list_paths())

    def _on_pins_closed(self, _result: None) -> None:
        self._refresh_pinned()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.data_table.id != "pinned-table":
            return
        self.query_one("#import-path-input", Input).value = str(event.row_key.value)

    def _refresh(self) -> None:
        table = self.query_one("#files-table", DataTable)
        table.clear()
        for f in self._manager.list_files():
            content = self._manager.load_file(f.name)
            table.add_row(
                f.name,
                str(len(content.valid_ips)) if content.success else "-",
                str(len(content.rejected_lines)) if content.success and content.rejected_lines else "-",
                key=f.name,
            )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self.app.push_screen(
            BlocklistFileDetailScreen(container=self._container, manager=self._manager, file_name=str(event.row_key.value)),
            lambda _result: self._refresh(),
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss()
            return

        if event.button.id == "manage-pins":
            self.app.push_screen(PinnedPathsScreen(container=self._container), self._on_pins_closed)
            return

        if event.button.id == "import":
            source_path = self.query_one("#import-path-input", Input).value.strip()
            if not source_path:
                self.app.notify("Saisissez le chemin du fichier source.", severity="warning")
                return
            dest_name = self.query_one("#import-name-input", Input).value.strip() or Path(source_path).name
            result = self._manager.import_from_path(source_path, dest_name)
            self.app.notify(result.message, severity="information" if result.success else "error")
            if result.success:
                if result.rejected_lines:
                    self.app.notify(f"{len(result.rejected_lines)} ligne(s) invalide(s) ignoree(s) a l'import.", severity="warning")
                self.query_one("#import-path-input", Input).value = ""
                self.query_one("#import-name-input", Input).value = ""
                self._refresh()
            return

        if event.button.id == "create":
            new_name = self.query_one("#create-name-input", Input).value.strip()
            if not new_name:
                self.app.notify("Saisissez un nom de fichier.", severity="warning")
                return
            result = self._manager.create_file(new_name)
            self.app.notify(result.message, severity="information" if result.success else "error")
            if result.success:
                self.query_one("#create-name-input", Input).value = ""
                self._refresh()
