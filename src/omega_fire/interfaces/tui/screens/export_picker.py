# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Modale de choix d'un fichier exporte (version 3.5) : 5.5 y charge une liste d'IPs
exportee en 5.4 (Top N), 6.1 (blacklist) ou 4.8 (jail). Retourne le chemin choisi, ou
None (Annuler / echap)."""
from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Static

from omega_fire.infrastructure.exporters.export_catalog import ExportFile
from omega_fire.interfaces.tui.support.export_kinds import export_row
from omega_fire.shared.i18n import _


class ExportPickerScreen(ModalScreen[Path | None]):
    BINDINGS: ClassVar[list[BindingType]] = [Binding("escape", "back", _("Annuler"), show=True)]

    def __init__(self, *, title: str, message: str, files: list[ExportFile]) -> None:
        super().__init__()
        self._title = title
        self._message = message
        self._files = files

    def compose(self) -> ComposeResult:
        with Vertical(classes="omega-confirm-box omega-choice-box"):
            yield Static(self._title, classes="omega-confirm-title omega-choice-title")
            yield Static(self._message, classes="omega-hint")
            yield DataTable(id="export-files")
            with Horizontal(classes="omega-actions omega-checklist-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Choisir"), id="choose", variant="primary")
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Annuler"), id="cancel")

    def on_mount(self) -> None:
        table = self.query_one("#export-files", DataTable)
        table.cursor_type = "row"
        table.add_columns(_("Type"), _("Fichier"), _("Date"), _("Taille"))
        for export in self._files:
            table.add_row(*export_row(export))
        table.focus()

    def _choose(self) -> None:
        table = self.query_one("#export-files", DataTable)
        row = table.cursor_row
        if row is None or not 0 <= row < len(self._files):
            return
        self.dismiss(self._files[row].path)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self._choose()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "choose":
            self._choose()
        else:
            self.dismiss(None)

    def action_back(self) -> None:
        self.dismiss(None)
