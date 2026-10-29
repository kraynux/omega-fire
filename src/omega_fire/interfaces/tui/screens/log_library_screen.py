# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 5.1 — Bibliotheque de logs (version 3.5). IMPORT des logs uniquement (decision
utilisateur 2026-10-28) : automatique depuis les instances omega-serv detectees (a chaque
ouverture), epinglage d'un chemin a la main, ou copie d'un log distant (SSH). Aucun
lanceur ici : la Bibliotheque alimente 5.2 Favoris et 5.3 Voir les logs."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, DataTable, Footer, Header, Input, Static

from omega_fire.application.commands.manage_log_library import LogLibraryCommand
from omega_fire.domain.logs.library import ACCESS_OMEGA_SERV, ACCESS_SSH, LogFile
from omega_fire.infrastructure.config.paths import RUNTIME_DIR
from omega_fire.infrastructure.probe.omega_serv_detector import detect_omega_serv_instances, instance_log_files
from omega_fire.infrastructure.storage.files.json_store import JsonStore
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.screens.confirm import ConfirmScreen
from omega_fire.interfaces.tui.support.action_audit import log_action_result
from omega_fire.shared.i18n import _

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ACTION_TITLE = "5.1 Bibliothèque"


def format_size(size: int | None) -> str:
    if size is None:
        return "—"
    if size >= 1 << 30:
        return _("{value} Go").format(value=f"{size / (1 << 30):.1f}")
    if size >= 1 << 20:
        return _("{value} Mo").format(value=f"{size / (1 << 20):.1f}")
    if size >= 1 << 10:
        return _("{value} Ko").format(value=f"{size / (1 << 10):.1f}")
    return _("{value} o").format(value=size)


def short_path(path: str, width: int = 46) -> str:
    """Chemin raccourci par le MILIEU (le nom du fichier reste visible en 80 colonnes)."""
    if len(path) <= width:
        return path
    name = path.rsplit("/", 1)[-1]
    head = max(width - len(name) - 2, 8)
    return f"{path[:head]}…/{name}" if len(name) < width - 8 else f"…{path[-(width - 1):]}"


def scroll_panel_home(screen: Any) -> None:
    """Le focus initial (tableau) fait defiler la zone : titre masque en 80x24."""
    screen.call_after_refresh(lambda: screen.query_one(".omega-panel").scroll_home(animate=False))


def origin_label(entry: LogFile) -> str:
    if entry.access == ACCESS_OMEGA_SERV:
        if entry.source and entry.source != "omega-serv":
            return _("omega-serv ({source})").format(source=entry.source)
        return "omega-serv"
    if entry.access == ACCESS_SSH:
        return _("SSH ({source})").format(source=entry.source or "?")
    return _("Épinglé")


def state_label(entry: LogFile) -> str:
    if not entry.exists:
        return _("absent")
    if entry.is_stale:
        return _("vide")
    return format_size(entry.size_bytes)


def library_command() -> LogLibraryCommand:
    return LogLibraryCommand(JsonStore(RUNTIME_DIR))


def omega_serv_logs() -> list[tuple[str, list]]:
    return [(instance.name, instance_log_files(instance)) for instance in detect_omega_serv_instances()]


class LogLibraryScreen(OmegaScreen):
    CSS = """
    LogLibraryScreen #library-table {
        height: auto;
        max-height: 14;
    }

    LogLibraryScreen #library-actions {
        width: 100%;
        height: auto;
        align: center middle;
        margin: 0;
    }
    """

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container
        self._library = library_command()
        self._entries: list[LogFile] = []

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="omega-panel"):
            yield Static(_("BIBLIOTHÈQUE DE LOGS"), classes="omega-title")
            yield Static(
                _("Les logs importés ici alimentent 5.2 Favoris et 5.3 Voir les logs. Les journaux "
                  "des instances omega-serv détectées sont importés automatiquement."),
                classes="omega-hint",
            )
            yield Static("", id="library-status", classes="omega-hint")
            yield DataTable(id="library-table")
            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Retirer"), id="remove", variant="error")
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Importer omega-serv"), id="import-serv")
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Sources SSH"), id="remote")

            yield Static(_("Épingler un chemin"), classes="omega-subtitle")
            yield Input(placeholder=_("Chemin absolu (ex. /var/log/nginx/access.log)"), id="path-input")
            with Horizontal(classes="omega-actions"), Container(classes="omega-btn-frame"):
                yield Button(_("Épingler"), id="pin", variant="primary")
        with Horizontal(classes="omega-actions", id="library-actions"), Container(classes="omega-btn-frame"):
            yield Button(_("Retour"), id="back")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#library-table", DataTable)
        table.cursor_type = "row"
        table.add_columns("#", _("Origine"), _("État"), _("Chemin"))
        # Mode automatique : journaux des instances omega-serv detectees (ajout seul, jamais un
        # journal retire a la main).
        result = self._library.import_omega_serv(omega_serv_logs(), automatic=True)
        if result.count:
            self.app.notify(result.message)
        self._refresh()
        scroll_panel_home(self)

    def on_screen_resume(self) -> None:
        self._refresh()

    def _refresh(self) -> None:
        self._entries = self._library.list_logs()
        table = self.query_one("#library-table", DataTable)
        table.clear()
        for index, entry in enumerate(self._entries, start=1):
            table.add_row(str(index), origin_label(entry), state_label(entry), short_path(entry.path), key=entry.path)
        status = self.query_one("#library-status", Static)
        status.update(_("{count} log(s) dans la Bibliothèque.").format(count=len(self._entries)) if self._entries
                      else _("Bibliothèque vide : épinglez un chemin ou importez des logs."))

    def _highlighted(self) -> LogFile | None:
        table = self.query_one("#library-table", DataTable)
        if not self._entries or table.cursor_row is None or not 0 <= table.cursor_row < len(self._entries):
            return None
        return self._entries[table.cursor_row]

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "back":
            self.dismiss()
        elif button_id == "pin":
            result = self._library.pin_path(self.query_one("#path-input", Input).value)
            self.app.notify(result.message, severity="information" if result.success else "warning")
            if result.success:
                self.query_one("#path-input", Input).value = ""
                if result.count:
                    log_action_result(self._container, _ACTION_TITLE, status="success")
                self._refresh()
        elif button_id == "import-serv":
            result = self._library.import_omega_serv(omega_serv_logs())
            self.app.notify(result.message, severity="information" if result.success else "warning")
            if result.count:
                log_action_result(self._container, _ACTION_TITLE, status="success")
            self._refresh()
        elif button_id == "remote":
            from omega_fire.interfaces.tui.screens.remote_log_sources_screen import RemoteLogSourcesScreen
            self.app.push_screen(RemoteLogSourcesScreen(container=self._container))
        elif button_id == "remove":
            entry = self._highlighted()
            if entry is None:
                self.app.notify(_("Sélectionnez un log."), severity="warning")
                return
            self.app.push_screen(
                ConfirmScreen(
                    title=_("RETIRER DE LA BIBLIOTHÈQUE"),
                    message=_("Retirer {path} de la Bibliothèque ?\nLe fichier n'est pas supprimé ; les "
                              "favoris qui l'utilisent ne pourront plus l'ouvrir.").format(path=entry.path),
                ),
                lambda confirmed: self._remove_if_confirmed(confirmed, entry.path),
            )

    def _remove_if_confirmed(self, confirmed: bool | None, path: str) -> None:
        if confirmed and self._library.remove([path]):
            self.app.notify(_("Retiré de la Bibliothèque : {path}").format(path=path))
            self._refresh()
