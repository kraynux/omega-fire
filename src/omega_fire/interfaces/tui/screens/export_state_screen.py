# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 1.7 — Exporter l'etat systeme (JSON/HTML/TXT). Patron #3 (champ
conditionnel) : le choix du theme HTML n'apparait que pour le format
HTML, meme mecanisme que JailBanUnbanScreen (Phase 2). Logique identique
a action_1_7_export_state : chemin par defaut pre-rempli et editable,
execution via application/commands/export_report.py::plan_export_report."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Input, Select, Static

from omega_fire.infrastructure.config.paths import EXPORTS_DIR
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.support.action_audit import log_action_result

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ACTION_TITLE = "1.7 Exporter l'etat et les diagnostics"

_HTML_THEMES: dict[str, str] = {
    "omega-base": "Omega-base (sombre bleu nuit / cyan - defaut)",
    "omega-burn": "Omega-burn (sombre braise rouge-orange)",
    "omega-neon": "Omega-neon (sombre cyberpunk cyan/magenta)",
    "light-basic": "Light-basic (clair sobre, rapport professionnel)",
    "light-alt": "Light-alt (clair papier creme / vert foret)",
}


class ExportStateScreen(OmegaScreen):
    """Formulaire d'export de l'etat systeme (capacites/diagnostics)."""

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="omega-form-panel"):
            yield Static("EXPORTER L'ETAT SYSTEME", classes="omega-title")

            yield Static("Format", classes="omega-subtitle")
            yield Select(
                [("JSON (donnees brutes structurees)", "json"),
                 ("HTML (rapport visuel lisible)", "html"),
                 ("TXT (rapport texte brut)", "txt")],
                value="html",
                id="format-select",
            )

            yield Static("Theme HTML", id="theme-label", classes="omega-subtitle")
            yield Select(
                [(label, name) for name, label in _HTML_THEMES.items()],
                value="omega-base",
                id="theme-select",
            )

            yield Static("Chemin de destination", classes="omega-subtitle")
            yield Input(id="path-input")

            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button("Exporter", id="launch", variant="primary")
                with Container(classes="omega-btn-frame"):
                    yield Button("Retour", id="back")
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_default_path("html")

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id != "format-select":
            return
        fmt = str(event.value)
        is_html = fmt == "html"
        self.query_one("#theme-label", Static).set_class(not is_html, "omega-hidden")
        self.query_one("#theme-select", Select).set_class(not is_html, "omega-hidden")
        self._refresh_default_path(fmt)

    def _refresh_default_path(self, fmt: str) -> None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_path = Path(EXPORTS_DIR) / f"rapport_systeme_{timestamp}.{fmt}"
        self.query_one("#path-input", Input).value = str(default_path)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss()
            return
        if event.button.id != "launch":
            return

        fmt = str(self.query_one("#format-select", Select).value)
        theme_name = str(self.query_one("#theme-select", Select).value) if fmt == "html" else "omega-base"
        destination = self.query_one("#path-input", Input).value.strip()
        if not destination:
            self.app.notify("Saisissez un chemin de destination.", severity="warning")
            return

        try:
            from omega_fire.application.commands.export_report import plan_export_report

            plan = plan_export_report(
                report_name="Rapport d'etat systeme Omega-Fire",
                format=fmt,
                destination=destination,
                registry=self._container.capability_registry,
                theme_name=theme_name,
            )
            for step in plan.steps:
                if step.execute:
                    step.execute()
        except Exception as e:
            self.app.notify(f"Echec de l'export : {e}", severity="error")
            log_action_result(self._container, _ACTION_TITLE, status="failure", error=str(e))
            return

        self.app.notify(f"Rapport exporte : {destination}", severity="information")
        log_action_result(self._container, _ACTION_TITLE, status="success")
        self.dismiss()
