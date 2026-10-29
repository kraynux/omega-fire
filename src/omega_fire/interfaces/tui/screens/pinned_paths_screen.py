# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran de gestion des fichiers epingles (menus 5.2/5.3/5.4/6.1/2.2/2.4/
2.8/4.3 — meme ManagePinnedLogPathsCommand/blocklist_analysis_pinned_paths.json
que corrige en Phase 0). Troisieme et dernier ecran de la Phase 2 : valide
le PATRON #4 ("liste + CRUD") sur une action reelle — DataTable + Input,
selection de ligne pour le retrait, adapte du patron
omega-check/screens/targets.py (D-008)."""
from __future__ import annotations

from typing import TYPE_CHECKING

import os

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, DataTable, Footer, Header, Input, Static

from omega_fire.application.commands.manage_pinned_log_paths import (
    DEFAULT_PINNED_LOG_PATHS,
    ManagePinnedLogPathsCommand,
)
from omega_fire.infrastructure.config.paths import DEFAULT_PINNED_FILES, RUNTIME_DIR
from omega_fire.infrastructure.storage.files.json_store import JsonStore
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.screens.checklist import CheckListScreen
from omega_fire.interfaces.tui.widgets.pinned_paths_table import PinnedPathsTable
from omega_fire.shared.i18n import _

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer


class PinnedPathsScreen(OmegaScreen):
    """Epingler/retirer des chemins de fichiers (blocklists) reutilisables
    dans les menus d'analyse/export."""

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container
        self._selected_path: str | None = None
        self._command = ManagePinnedLogPathsCommand(
            JsonStore(RUNTIME_DIR),
            relative_path="blocklist_analysis_pinned_paths.json",
            defaults=[str(p) for p in DEFAULT_PINNED_FILES],
        )

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="omega-panel"):
            yield Static(_("FICHIERS ÉPINGLÉS"), classes="omega-title")
            yield PinnedPathsTable(id="pinned-table")
            yield Input(placeholder=_("Chemin complet du fichier à épingler"), id="path-input")
            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Épingler"), id="pin", variant="primary")
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Presets"), id="presets")
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Retirer"), id="unpin", variant="error")
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Retour"), id="back")
        yield Footer()

    def on_mount(self) -> None:
        self._refresh()

    def _refresh(self) -> None:
        self.query_one(PinnedPathsTable).set_paths(self._command.list_paths())

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        self._selected_path = str(event.row_key.value)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss()
            return

        if event.button.id == "presets":
            self._open_presets()
            return

        if event.button.id == "pin":
            path_input = self.query_one("#path-input", Input)
            new_path = path_input.value.strip()
            if not new_path:
                self.app.notify(_("Saisissez un chemin de fichier."), severity="warning")
                return
            result = self._command.add_path(new_path)
            if result.success:
                self.app.notify(result.message, severity="information")
                path_input.value = ""
                self._refresh()
            else:
                self.app.notify(result.message, severity="warning")
            return

        if event.button.id == "unpin":
            if self._selected_path is None:
                self.app.notify(_("Sélectionnez d'abord une ligne."), severity="warning")
                return
            result = self._command.remove_path(self._selected_path)
            if result.success:
                self.app.notify(result.message, severity="information")
            else:
                self.app.notify(result.message, severity="warning")
            self._selected_path = None
            self._refresh()

    def _open_presets(self) -> None:
        """Presets a cocher (version 3.5) : chemins usuels (logs systeme, serveurs web,
        blocklists d'omega-fire) et logs de la Bibliotheque 5.1, seulement ceux presents
        sur cette machine. Seules les blocklists d'omega-fire restent epinglees d'office
        (fichiers de l'application, toujours presents) ; la liste des logs systeme ne sert
        plus que de presets."""
        from omega_fire.interfaces.tui.screens.log_library_screen import library_command

        library = [entry.path for entry in library_command().list_logs()]
        candidates = [str(p) for p in DEFAULT_PINNED_FILES] + DEFAULT_PINNED_LOG_PATHS + library
        presets = self._command.preset_candidates(candidates, os.path.isfile)
        if not presets:
            self.app.notify(_("Aucun preset disponible : les chemins usuels présents sur cette machine "
                              "sont déjà épinglés."), severity="information")
            return
        self.app.push_screen(
            CheckListScreen(
                title=_("PRESETS À ÉPINGLER"),
                message=_("Chemins usuels présents sur cette machine (et logs de la Bibliothèque 5.1). "
                          "Cochez ceux à épingler."),
                items=[(path, path) for path in presets],
                confirm_label=_("Épingler"),
            ),
            self._pin_presets,
        )

    def _pin_presets(self, paths: list[str] | None) -> None:
        if not paths:
            return
        result = self._command.add_paths(paths)
        self.app.notify(result.message, severity="information" if result.success else "warning")
        self._refresh()
