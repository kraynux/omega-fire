# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Sources distantes (SSH) de la Bibliotheque de logs (5.1, version 3.5), reprises
d'omega-serv : enregistrer une source (hote, chemin distant, utilisateur, port, cle), puis
« Recuperer maintenant » copie le log par scp dans var/log/remote/ et l'ajoute a la
Bibliotheque. Aucun mot de passe : authentification par cle / agent SSH (BatchMode, jamais
d'invite qui bloquerait l'interface)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, DataTable, Footer, Header, Input, Static

from omega_fire.application.commands.manage_log_library import LibraryActionResult, RemoteLogSourcesCommand
from omega_fire.domain.logs.remote_source import RemoteLogSource
from omega_fire.infrastructure.config.paths import RUNTIME_DIR, VAR_DIR
from omega_fire.infrastructure.logs.scp_runner import run_scp
from omega_fire.infrastructure.storage.files.json_store import JsonStore
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.screens.confirm import ConfirmScreen
from omega_fire.interfaces.tui.screens.log_library_screen import library_command, scroll_panel_home
from omega_fire.interfaces.tui.support.action_audit import log_action_result
from omega_fire.shared.i18n import _

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ACTION_TITLE = "5.1 Bibliothèque"
REMOTE_CACHE_DIR = VAR_DIR / "log" / "remote"


def _scp(command: list[str]) -> tuple[bool, str]:
    result = run_scp(command)
    return result.ok, result.detail


class RemoteLogSourcesScreen(OmegaScreen):
    CSS = """
    RemoteLogSourcesScreen #sources-table {
        height: auto;
        max-height: 10;
    }

    RemoteLogSourcesScreen #remote-actions {
        width: 100%;
        height: auto;
        align: center middle;
        margin: 0;
    }
    """

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container
        self._sources_command = RemoteLogSourcesCommand(JsonStore(RUNTIME_DIR))
        self._sources: list[RemoteLogSource] = []

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="omega-panel"):
            yield Static(_("SOURCES DISTANTES (SSH)"), classes="omega-title")
            yield Static(
                _("Copie un log d'une autre machine par scp dans {path}, puis l'ajoute à la Bibliothèque. "
                  "Authentification par clé ou agent SSH (aucun mot de passe demandé ni enregistré).").format(
                    path=REMOTE_CACHE_DIR),
                classes="omega-hint",
            )
            yield Static("", id="sources-status", classes="omega-hint")
            yield DataTable(id="sources-table")
            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Récupérer maintenant"), id="fetch", variant="primary")
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Supprimer"), id="delete", variant="error")

            yield Static(_("Ajouter une source"), classes="omega-subtitle")
            yield Input(placeholder=_("Label"), id="label-input")
            yield Input(placeholder=_("Hôte (ex. backend1 ou 192.168.1.10)"), id="host-input")
            yield Input(placeholder=_("Chemin distant (ex. /var/log/nginx/access.log)"), id="remote-path-input")
            yield Input(placeholder=_("Utilisateur (optionnel)"), id="user-input")
            yield Input(placeholder=_("Port (optionnel)"), id="port-input")
            yield Input(placeholder=_("Chemin de la clé privée (optionnel)"), id="identity-input")
            with Horizontal(classes="omega-actions"), Container(classes="omega-btn-frame"):
                yield Button(_("Enregistrer"), id="save")
        with Horizontal(classes="omega-actions", id="remote-actions"), Container(classes="omega-btn-frame"):
            yield Button(_("Retour"), id="back")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#sources-table", DataTable)
        table.cursor_type = "row"
        table.add_columns(_("Label"), _("Hôte"), _("Chemin distant"))
        self._refresh()
        scroll_panel_home(self)

    def _refresh(self) -> None:
        self._sources = self._sources_command.list_sources()
        table = self.query_one("#sources-table", DataTable)
        table.clear()
        for source in self._sources:
            host = f"{source.user}@{source.host}" if source.user else source.host
            if source.port:
                host += f":{source.port}"
            table.add_row(source.label, host, source.remote_path, key=source.label)
        self.query_one("#sources-status", Static).update(
            "" if self._sources else _("Aucune source enregistrée."))

    def _highlighted(self) -> RemoteLogSource | None:
        table = self.query_one("#sources-table", DataTable)
        if not self._sources or table.cursor_row is None or not 0 <= table.cursor_row < len(self._sources):
            return None
        return self._sources[table.cursor_row]

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "back":
            self.dismiss()
        elif button_id == "save":
            self._save()
        elif button_id == "delete":
            source = self._highlighted()
            if source is None:
                self.app.notify(_("Sélectionnez une source."), severity="warning")
                return
            self.app.push_screen(
                ConfirmScreen(title=_("SUPPRIMER CETTE SOURCE ?"),
                              message=_("{label} — la copie locale déjà récupérée reste dans la Bibliothèque.").format(label=source.label)),
                lambda confirmed: self._delete_if_confirmed(confirmed, source.label),
            )
        elif button_id == "fetch":
            source = self._highlighted()
            if source is None:
                self.app.notify(_("Sélectionnez une source."), severity="warning")
                return
            self.run_blocking(
                lambda: self._sources_command.fetch(source, REMOTE_CACHE_DIR, library_command(), _scp),
                self._fetched,
                busy_message=_("Récupération en cours..."),
            )

    def _save(self) -> None:
        values = {key: self.query_one(f"#{key}-input", Input).value
                  for key in ("label", "host", "remote-path", "user", "port", "identity")}
        result = self._sources_command.save_source(
            label=values["label"], host=values["host"], remote_path=values["remote-path"],
            user=values["user"], port=values["port"], identity_file=values["identity"])
        self.app.notify(result.message, severity="information" if result.success else "warning")
        if result.success:
            for key in values:
                self.query_one(f"#{key}-input", Input).value = ""
            self._refresh()

    def _delete_if_confirmed(self, confirmed: bool | None, label: str) -> None:
        if confirmed:
            self._sources_command.remove(label)
            self._refresh()

    def _fetched(self, result: LibraryActionResult) -> None:
        self.app.notify(result.message, severity="information" if result.success else "error", timeout=10)
        log_action_result(self._container, _ACTION_TITLE, status="success" if result.success else "failure",
                          error=None if result.success else result.message)
