# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 1.5 — Voir le journal applicatif. Meme source de donnees
qu'action_1_5_app_log (lecture directe de APP_LOG_PATH, filtre par
mot-cle, N dernieres lignes, coloration par niveau [ERROR]/[CRITICAL]/
[WARNING]) — Input + DataTable remplacent la boucle de saisie
sequentielle du CLI. La gestion/purge (4 modes) est un sous-ecran dedie
(purge_app_log_screen.py, patron #3), meme convention que 7.3.

Seules les lignes d'ENTETE d'evenement (format "[date heure] [NIVEAU]
[logger]: message", produit par AppLogger) sont affichees — les lignes
de continuation d'une trace Python (logging.error(..., exc_info=...)
ecrit la trace complete sur plusieurs lignes brutes, sans prefixe) sont
exclues de cette vue rapide (retour utilisateur reel : "ce sont des
erreurs qui s'affichent a la place des evenements" — une seule exception
peut ecrire des dizaines de lignes de trace qui noient les vrais
evenements dans la fenetre des N dernieres lignes). La trace complete
reste dans le fichier lui-meme pour un diagnostic approfondi (editeur de
texte), hors perimetre de cette vue.

La lecture du fichier journal (potentiellement volumineux) s'execute en
arriere-plan (run_blocking, voir _base.py)."""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, DataTable, Footer, Header, Input, Static

from omega_fire.infrastructure.config.paths import APP_LOG_PATH
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.screens.purge_app_log_screen import PurgeAppLogScreen

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ACTION_TITLE = "1.5 Voir le journal applicatif"
_DEFAULT_MAX_LINES = 50
_ENTRY_PATTERN = re.compile(r"^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\] \[")


class AppLogScreen(OmegaScreen):
    """1.5 — journal applicatif filtrable, N dernieres lignes, avec gestion/purge."""

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="omega-panel"):
            yield Static("JOURNAL APPLICATIF", classes="omega-title")
            yield Input(placeholder="Filtrer par mot-cle (vide = aucun filtre)", id="filter-input")
            yield Input(value=str(_DEFAULT_MAX_LINES), placeholder="Nombre de lignes", id="lines-input")
            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button("Filtrer", id="filter", variant="primary")
                with Container(classes="omega-btn-frame"):
                    yield Button("Gerer / Purger", id="manage", variant="error")
                with Container(classes="omega-btn-frame"):
                    yield Button("Retour", id="back")

            yield DataTable(id="log-table")
            yield Static("", id="log-hint", classes="omega-hint")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#log-table", DataTable).add_columns("Entree du journal applicatif")
        self._refresh()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "back":
            self.dismiss()
            return
        if button_id == "filter":
            self._refresh()
            return
        if button_id == "manage":
            self.app.push_screen(PurgeAppLogScreen(container=self._container), self._on_purge_closed)

    def _on_purge_closed(self, _result: None) -> None:
        self._refresh()

    def _colors(self) -> dict[str, str]:
        v = self.app.get_css_variables()
        return {"danger": v.get("error", ""), "warning": v.get("warning", "")}

    def _refresh(self) -> None:
        keyword = self.query_one("#filter-input", Input).value.strip()
        raw_lines = self.query_one("#lines-input", Input).value.strip()
        max_lines = int(raw_lines) if raw_lines.isdigit() and int(raw_lines) > 0 else _DEFAULT_MAX_LINES

        def _fetch() -> list[str]:
            if not APP_LOG_PATH.exists():
                return []
            with open(APP_LOG_PATH, "r", encoding="utf-8") as f:
                lines = [
                    line.strip() for line in f.readlines()
                    if line.strip() and _ENTRY_PATTERN.match(line)
                ]
            if keyword:
                lines = [l for l in lines if keyword.lower() in l.lower()]
            return lines[-max_lines:]

        self.run_blocking(_fetch, self._on_loaded, busy_message="Lecture du journal...")

    def _on_loaded(self, recent_lines: list[str]) -> None:
        colors = self._colors()
        table = self.query_one("#log-table", DataTable)
        table.clear()

        if not APP_LOG_PATH.exists():
            self.query_one("#log-hint", Static).update(f"Le fichier journal '{APP_LOG_PATH}' n'existe pas encore.")
            return
        if not recent_lines:
            self.query_one("#log-hint", Static).update("Aucune entree ne correspond aux criteres.")
            return

        self.query_one("#log-hint", Static).update(f"{len(recent_lines)} entree(s) affichee(s).")
        for line in recent_lines:
            if "[ERROR]" in line or "[CRITICAL]" in line:
                text = Text(line, style=colors["danger"])
            elif "[WARNING]" in line:
                text = Text(line, style=colors["warning"])
            else:
                text = Text(line)
            table.add_row(text)
