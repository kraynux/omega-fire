# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 6.5 — Voir tous les exports (version 3.5) : tous les fichiers exportes au meme
endroit, sans terminal ni gestionnaire de fichiers. Un rapport HTML s'ouvre dans le
navigateur de l'utilisateur (infrastructure/desktop/browser_opener.py) ; JSON / TXT se
lisent dans omega-fire (lecteur Classique de 5.3). Sans session graphique (SSH,
serveur), le chemin du HTML est affiche."""
from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, DataTable, Footer, Header, Static

from omega_fire.infrastructure.config.paths import BLOCKLIST_DIR
from omega_fire.infrastructure.desktop.browser_opener import OpenResult, open_in_browser
from omega_fire.infrastructure.exporters.export_catalog import VIEWABLE_SUFFIXES, ExportFile, list_exports
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.screens.confirm import ConfirmScreen
from omega_fire.interfaces.tui.screens.log_classic_viewer_screen import LogClassicViewerScreen
from omega_fire.interfaces.tui.screens.log_library_screen import scroll_panel_home
from omega_fire.interfaces.tui.support.action_audit import log_action_result
from omega_fire.interfaces.tui.support.export_kinds import export_row
from omega_fire.shared.i18n import _

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ACTION_TITLE = "6.5 Voir tous les exports"


class ExportsScreen(OmegaScreen):
    CSS = """
    ExportsScreen #exports-table {
        height: auto;
        max-height: 16;
    }

    ExportsScreen #exports-actions {
        width: 100%;
        height: auto;
        align: center middle;
        margin: 0;
    }
    """

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container
        self._files: list[ExportFile] = []

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="omega-panel"):
            yield Static(_("TOUS LES EXPORTS"), classes="omega-title")
            yield Static(
                _("Dossier d'exports : {path} (modifiable dans Réglages). HTML : ouvert dans votre "
                  "navigateur. JSON / TXT : lus ici.").format(path=self._container.exports_dir),
                classes="omega-hint",
            )
            yield Static("", id="exports-status", classes="omega-hint")
            yield DataTable(id="exports-table")
            yield Static("", id="exports-path", classes="omega-hint")
        with Horizontal(classes="omega-actions", id="exports-actions"):
            with Container(classes="omega-btn-frame"):
                yield Button(_("Ouvrir"), id="open", variant="primary")
            with Container(classes="omega-btn-frame"):
                yield Button(_("Copier le chemin"), id="copy")
            with Container(classes="omega-btn-frame"):
                yield Button(_("Supprimer"), id="delete", variant="error")
            with Container(classes="omega-btn-frame"):
                yield Button(_("Retour"), id="back")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#exports-table", DataTable)
        table.cursor_type = "row"
        table.add_columns(_("Type"), _("Fichier"), _("Date"), _("Taille"))
        self._refresh()
        scroll_panel_home(self)

    def on_screen_resume(self) -> None:
        self._refresh()

    def _refresh(self) -> None:
        self._files = list_exports(self._container.exports_dir, BLOCKLIST_DIR)
        table = self.query_one("#exports-table", DataTable)
        cursor = table.cursor_row
        table.clear()
        for export in self._files:
            table.add_row(*export_row(export))
        if self._files and cursor is not None and 0 < cursor < len(self._files):
            table.move_cursor(row=cursor)
        self.query_one("#exports-status", Static).update(
            _("{count} fichier(s).").format(count=len(self._files)) if self._files
            else _("Aucun export pour l'instant (menus 5.4 et 6.1 à 6.4)."))
        self._show_path()

    def _highlighted(self) -> ExportFile | None:
        table = self.query_one("#exports-table", DataTable)
        if not self._files or table.cursor_row is None or not 0 <= table.cursor_row < len(self._files):
            return None
        return self._files[table.cursor_row]

    def _show_path(self) -> None:
        export = self._highlighted()
        self.query_one("#exports-path", Static).update(str(export.path) if export else "")

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        self._show_path()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self._open()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "back":
            self.dismiss()
            return
        export = self._highlighted()
        if export is None:
            self.app.notify(_("Sélectionnez un fichier."), severity="warning")
            return
        if button_id == "open":
            self._open()
        elif button_id == "copy":
            self.app.copy_to_clipboard(str(export.path))
            self.app.notify(_("Chemin copié : {path}").format(path=export.path))
        elif button_id == "delete":
            self.app.push_screen(
                ConfirmScreen(title=_("SUPPRIMER CET EXPORT ?"),
                              message=_("{path}\nLe fichier est supprimé définitivement.").format(path=export.path)),
                lambda confirmed: self._delete_if_confirmed(confirmed, export),
            )

    def _open(self) -> None:
        export = self._highlighted()
        if export is None:
            return
        if not export.path.is_file():
            self.app.notify(_("Fichier introuvable : {path}").format(path=export.path), severity="warning")
            self._refresh()
            return
        if export.is_html:
            self.run_blocking(lambda: open_in_browser(export.path), lambda result: self._opened(result, export),
                              busy_message=_("Ouverture dans le navigateur..."))
        elif export.path.suffix.lower() in VIEWABLE_SUFFIXES:
            self.app.push_screen(LogClassicViewerScreen(container=self._container, path=str(export.path)))
            log_action_result(self._container, _ACTION_TITLE, status="success")
        else:
            self.app.notify(_("Format non lisible ici : {path}").format(path=export.path), severity="warning")

    def _opened(self, result: OpenResult, export: ExportFile) -> None:
        if result.ok:
            message = _("Ouvert dans le navigateur.")
            if result.opened_path and result.opened_path != str(export.path):
                message += " " + _("(copie lisible par votre utilisateur : {path})").format(path=result.opened_path)
            self.app.notify(message)
            log_action_result(self._container, _ACTION_TITLE, status="success")
            return
        if result.reason == "no_session":
            message = _("Pas de session graphique (SSH ou serveur) : ouvrez ce fichier depuis un poste avec "
                        "navigateur : {path}").format(path=export.path)
        elif result.reason == "no_xdg_open":
            message = _("xdg-open introuvable (paquet xdg-utils) : ouvrez {path} dans votre navigateur.").format(
                path=export.path)
        else:
            message = _("Le navigateur n'a pas pu être lancé ({detail}) : {path}").format(
                detail=result.detail or result.reason, path=export.path)
        self.app.notify(message, severity="warning", timeout=12)
        log_action_result(self._container, _ACTION_TITLE, status="failure", error=result.reason)

    def _delete_if_confirmed(self, confirmed: bool | None, export: ExportFile) -> None:
        if not confirmed:
            return
        try:
            export.path.unlink()
        except OSError as e:
            self.app.notify(_("Suppression impossible : {e}").format(e=e), severity="error")
            return
        self.app.notify(_("Export supprimé : {name}").format(name=export.path.name))
        self._refresh()
