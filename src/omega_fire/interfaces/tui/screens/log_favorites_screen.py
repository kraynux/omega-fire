# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 5.2 — Favoris (version 3.5, repris d'omega-serv / omega-log) : combiner des logs de
la Bibliotheque, les enregistrer sous un nom avec un lecteur, puis lancer directement le
favori. Garde-fou : 2 logs ou plus -> lnav seul (refus a l'enregistrement)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, DataTable, Footer, Header, Input, Select, Static

from omega_fire.application.commands.manage_log_library import LogFavoritesCommand
from omega_fire.domain.logs.favorite import Favorite
from omega_fire.domain.logs.library import LogFile
from omega_fire.domain.logs.viewer_type import ViewerType
from omega_fire.infrastructure.config.paths import RUNTIME_DIR
from omega_fire.infrastructure.storage.files.json_store import JsonStore
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.screens.confirm import ConfirmScreen
from omega_fire.interfaces.tui.screens.log_library_screen import (
    library_command,
    origin_label,
    scroll_panel_home,
    short_path,
    state_label,
)
from omega_fire.interfaces.tui.support.action_audit import log_action_result
from omega_fire.interfaces.tui.support.log_viewers import open_viewer, viewer_label
from omega_fire.shared.i18n import _

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ACTION_TITLE = "5.2 Favoris"


class LogFavoritesScreen(OmegaScreen):
    CSS = """
    LogFavoritesScreen #favorites-table,
    LogFavoritesScreen #library-table {
        height: auto;
        max-height: 10;
    }

    LogFavoritesScreen #favorites-actions {
        width: 100%;
        height: auto;
        align: center middle;
        margin: 0;
    }
    """

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container
        self._favorites_command = LogFavoritesCommand(JsonStore(RUNTIME_DIR))
        self._favorites: list[Favorite] = []
        self._library_entries: list[LogFile] = []

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="omega-panel"):
            yield Static(_("FAVORIS"), classes="omega-title")
            yield Static("", id="favorites-status", classes="omega-hint")
            yield DataTable(id="favorites-table")
            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Lancer"), id="launch", variant="primary")
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Supprimer"), id="delete", variant="error")

            yield Static(_("Créer un favori (logs de la Bibliothèque)"), classes="omega-subtitle")
            yield Static(
                _("Un seul log : lecteur au choix. Plusieurs logs combinés : lnav seul, le seul lecteur "
                  "qui sait les fusionner."),
                classes="omega-hint",
            )
            yield DataTable(id="library-table")
            yield Input(placeholder=_("Numéros des logs, séparés par des virgules (ex. 1,3)"), id="selection-input")
            yield Input(placeholder=_("Nom du favori"), id="name-input")
            yield Select(
                [(viewer_label(v), v.value) for v in ViewerType],
                value=ViewerType.LNAV.value, id="viewer-select", allow_blank=False,
            )
            with Horizontal(classes="omega-actions"), Container(classes="omega-btn-frame"):
                yield Button(_("Enregistrer"), id="save")
        with Horizontal(classes="omega-actions", id="favorites-actions"), Container(classes="omega-btn-frame"):
            yield Button(_("Retour"), id="back")
        yield Footer()

    def on_mount(self) -> None:
        favorites = self.query_one("#favorites-table", DataTable)
        favorites.cursor_type = "row"
        favorites.add_columns(_("Nom"), _("Lecteur"), _("Logs"))
        library = self.query_one("#library-table", DataTable)
        library.cursor_type = "row"
        library.add_columns("#", _("Origine"), _("État"), _("Chemin"))
        self._refresh()
        scroll_panel_home(self)

    def on_screen_resume(self) -> None:
        self._refresh()

    def _refresh(self) -> None:
        self._favorites = self._favorites_command.list_favorites()
        table = self.query_one("#favorites-table", DataTable)
        table.clear()
        for favorite in self._favorites:
            table.add_row(favorite.name, viewer_label(favorite.viewer),
                          ", ".join(p.rsplit("/", 1)[-1] for p in favorite.paths), key=favorite.name)
        self.query_one("#favorites-status", Static).update(
            "" if self._favorites else _("Aucun favori : créez-en un ci-dessous."))

        self._library_entries = library_command().list_logs()
        library = self.query_one("#library-table", DataTable)
        library.clear()
        for index, entry in enumerate(self._library_entries, start=1):
            library.add_row(str(index), origin_label(entry), state_label(entry), short_path(entry.path))

    def _highlighted(self) -> Favorite | None:
        table = self.query_one("#favorites-table", DataTable)
        if not self._favorites or table.cursor_row is None or not 0 <= table.cursor_row < len(self._favorites):
            return None
        return self._favorites[table.cursor_row]

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "back":
            self.dismiss()
        elif button_id == "launch":
            favorite = self._highlighted()
            if favorite is None:
                self.app.notify(_("Sélectionnez un favori."), severity="warning")
                return
            if open_viewer(self.app, self._container, favorite.viewer, list(favorite.paths)):
                log_action_result(self._container, _ACTION_TITLE, status="success")
        elif button_id == "delete":
            favorite = self._highlighted()
            if favorite is None:
                self.app.notify(_("Sélectionnez un favori."), severity="warning")
                return
            self.app.push_screen(
                ConfirmScreen(title=_("SUPPRIMER CE FAVORI ?"), message=favorite.name),
                lambda confirmed: self._delete_if_confirmed(confirmed, favorite.name),
            )
        elif button_id == "save":
            self._save()

    def _delete_if_confirmed(self, confirmed: bool | None, name: str) -> None:
        if confirmed and self._favorites_command.remove(name):
            self._refresh()

    def _save(self) -> None:
        paths: list[str] = []
        for token in self.query_one("#selection-input", Input).value.split(","):
            token = token.strip()
            if not token:
                continue
            if not token.isdigit() or not 1 <= int(token) <= len(self._library_entries):
                self.app.notify(_("Numéro invalide : {token}.").format(token=token), severity="warning")
                return
            path = self._library_entries[int(token) - 1].path
            if path not in paths:
                paths.append(path)
        result = self._favorites_command.create(
            name=self.query_one("#name-input", Input).value, paths=paths,
            viewer=ViewerType(str(self.query_one("#viewer-select", Select).value)),
        )
        self.app.notify(result.message, severity="information" if result.success else "warning")
        if result.success:
            self.query_one("#selection-input", Input).value = ""
            self.query_one("#name-input", Input).value = ""
            log_action_result(self._container, _ACTION_TITLE, status="success")
            self._refresh()
