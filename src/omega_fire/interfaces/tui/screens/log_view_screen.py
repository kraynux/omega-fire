# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 5.3 — Voir les logs (version 3.5) : voir un log de la Bibliotheque sans
configuration, lecteur au choix — Simple (tableau de bord temps reel), Classique (lecture +
suivi) ou lnav. Pour combiner plusieurs logs : 5.2 Favoris."""
from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, DataTable, Footer, Header, Static

from omega_fire.domain.logs.library import LogFile
from omega_fire.domain.logs.viewer_type import ViewerType
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.screens.log_library_screen import (
    library_command,
    origin_label,
    scroll_panel_home,
    short_path,
    state_label,
)
from omega_fire.interfaces.tui.support.action_audit import log_action_result
from omega_fire.interfaces.tui.support.log_viewers import open_viewer
from omega_fire.shared.i18n import _

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ACTION_TITLE = "5.3 Voir les logs"
_BUTTONS = (("view-simple", ViewerType.SIMPLE), ("view-classic", ViewerType.CLASSIC), ("view-lnav", ViewerType.LNAV))


class LogViewScreen(OmegaScreen):
    CSS = """
    LogViewScreen #library-table {
        height: auto;
        max-height: 14;
    }

    LogViewScreen #view-actions {
        width: 100%;
        height: auto;
        align: center middle;
        margin: 0;
    }
    """

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container
        self._entries: list[LogFile] = []

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="omega-panel"):
            yield Static(_("VOIR LES LOGS"), classes="omega-title")
            yield Static(
                _("Choisissez un log de la Bibliothèque (5.1), puis le lecteur. Pour combiner plusieurs "
                  "logs : 5.2 Favoris."),
                classes="omega-hint",
            )
            yield Static("", id="view-status", classes="omega-hint")
            yield DataTable(id="library-table")
        with Horizontal(classes="omega-actions", id="view-actions"):
            with Container(classes="omega-btn-frame"):
                yield Button(_("Simple"), id="view-simple", variant="primary")
            with Container(classes="omega-btn-frame"):
                yield Button(_("Classique"), id="view-classic")
            with Container(classes="omega-btn-frame"):
                yield Button("lnav", id="view-lnav")
            with Container(classes="omega-btn-frame"):
                yield Button(_("Retour"), id="back")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#library-table", DataTable)
        table.cursor_type = "row"
        table.add_columns("#", _("Origine"), _("État"), _("Chemin"))
        self._refresh()
        scroll_panel_home(self)

    def on_screen_resume(self) -> None:
        self._refresh()

    def _refresh(self) -> None:
        self._entries = library_command().list_logs()
        table = self.query_one("#library-table", DataTable)
        cursor = table.cursor_row
        table.clear()
        for index, entry in enumerate(self._entries, start=1):
            table.add_row(str(index), origin_label(entry), state_label(entry), short_path(entry.path))
        if self._entries and cursor is not None and 0 < cursor < len(self._entries):
            table.move_cursor(row=cursor)
        self.query_one("#view-status", Static).update(
            "" if self._entries else _("Bibliothèque vide : importez ou épinglez des logs en 5.1."))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss()
            return
        viewer = dict(_BUTTONS).get(event.button.id or "")
        if viewer is None:
            return
        table = self.query_one("#library-table", DataTable)
        if not self._entries or table.cursor_row is None or not 0 <= table.cursor_row < len(self._entries):
            self.app.notify(_("Sélectionnez un log."), severity="warning")
            return
        entry = self._entries[table.cursor_row]
        if not entry.exists:
            self.app.notify(_("Fichier introuvable : {path}").format(path=entry.path), severity="warning")
            return
        if open_viewer(self.app, self._container, viewer, [entry.path]):
            log_action_result(self._container, _ACTION_TITLE, status="success")
