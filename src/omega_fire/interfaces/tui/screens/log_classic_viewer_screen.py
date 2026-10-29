# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Lecteur CLASSIQUE (5.2 Favoris, 5.3 Voir les logs ; version 3.5) : dernieres lignes d'un
log, puis suivi en direct a la demande. Repris d'omega-serv (`LogViewerScreen`, refonte du
2026-10-15) ; lecture depuis la fin du fichier (infrastructure/logs/tail_reader.py) au lieu
du fichier entier."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.timer import Timer
from textual.widgets import Button, Footer, Header, RichLog, Static

from omega_fire.infrastructure.logs.tail_reader import FileTailReader, read_last_lines
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.shared.i18n import _

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_TAIL_INTERVAL_SECONDS = 1.0
_INITIAL_LINES = 500


class LogClassicViewerScreen(OmegaScreen):
    CSS = """
    LogClassicViewerScreen #log-content {
        height: 1fr;
    }

    LogClassicViewerScreen #viewer-actions {
        width: 100%;
        height: auto;
        align: center middle;
        margin: 0;
    }
    """

    def __init__(self, *, container: DependencyContainer, path: str) -> None:
        super().__init__()
        self._container = container
        self._path = path
        self._tail_reader: FileTailReader | None = None
        self._following = False
        self._timer: Timer | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="omega-panel"):
            yield Static(_("LECTEUR CLASSIQUE — {path}").format(path=self._path), classes="omega-title")
            yield Static("", id="viewer-error", classes="omega-hint")
            yield RichLog(id="log-content", wrap=False, highlight=False, markup=False)
        with Horizontal(classes="omega-actions", id="viewer-actions"):
            with Container(classes="omega-btn-frame"):
                yield Button(_("Suivre en direct"), id="follow", variant="primary")
            with Container(classes="omega-btn-frame"):
                yield Button(_("Retour"), id="back")
        yield Footer()

    def on_mount(self) -> None:
        self._open_log()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss()
        elif event.button.id == "follow":
            self._toggle_follow()

    def _open_log(self) -> None:
        error_widget = self.query_one("#viewer-error", Static)
        path = Path(self._path)
        log_widget = self.query_one("#log-content", RichLog)
        log_widget.clear()
        try:
            lines = read_last_lines(path, _INITIAL_LINES)
            self._tail_reader = FileTailReader(path)
        except FileNotFoundError:
            error_widget.update(_("Fichier introuvable : {path}").format(path=path))
            return
        except OSError as exc:
            error_widget.update(_("Impossible de lire {path} : {exc}").format(path=path, exc=exc))
            return
        error_widget.update(_("Fichier vide.") if not lines else _("{count} dernière(s) ligne(s).").format(count=len(lines)))
        for line in lines:
            log_widget.write(line)

    def _toggle_follow(self) -> None:
        if self._tail_reader is None:
            self.query_one("#viewer-error", Static).update(_("Aucun fichier valide à suivre."))
            return
        if self._following:
            self._stop_following()
        else:
            self._following = True
            self.query_one("#follow", Button).label = _("Arrêter le suivi")
            self._timer = self.set_interval(_TAIL_INTERVAL_SECONDS, self._poll_new_lines)

    def _stop_following(self) -> None:
        self._following = False
        if self._timer is not None:
            self._timer.stop()
            self._timer = None
        if self.is_mounted:
            self.query_one("#follow", Button).label = _("Suivre en direct")

    def on_unmount(self) -> None:
        if self._timer is not None:
            self._timer.stop()

    def _poll_new_lines(self) -> None:
        if not self._following or self._tail_reader is None:
            return
        try:
            new_lines = self._tail_reader.read_new_lines()
        except OSError as exc:
            self.query_one("#log-content", RichLog).write(_("(suivi interrompu : {exc})").format(exc=exc))
            self._stop_following()
            return
        log_widget = self.query_one("#log-content", RichLog)
        for line in new_lines:
            log_widget.write(line)
