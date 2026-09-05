# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 6.3 — Exporter un rapport d'audit complet (TXT/HTML). Patron #3
(theme HTML conditionnel), meme structure que ExportStateScreen (1.7).
Logique identique a interfaces/cli/actions.py::action_6_3_export_audit."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Input, Select, Static

from omega_fire.infrastructure.config.paths import EXPORTS_DIR
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.support.action_audit import log_action_result

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ACTION_TITLE = "6.3 Rapport d'audit complet"

_HTML_THEMES: dict[str, str] = {
    "omega-base": "Omega-base (sombre bleu nuit / cyan - defaut)",
    "omega-burn": "Omega-burn (sombre braise rouge-orange)",
    "omega-neon": "Omega-neon (sombre cyberpunk cyan/magenta)",
    "light-basic": "Light-basic (clair sobre, rapport professionnel)",
    "light-alt": "Light-alt (clair papier creme / vert foret)",
}


class ExportAuditScreen(OmegaScreen):
    """Export du rapport d'audit complet (regles, IPs, jails, capacites)."""

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="omega-form-panel"):
            yield Static("RAPPORT D'AUDIT COMPLET", classes="omega-title")

            yield Static("Format", classes="omega-subtitle")
            yield Select(
                [("HTML (rapport visuel lisible)", "html"), ("TXT (rapport texte brut)", "txt")],
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
        self.query_one("#path-input", Input).value = str(EXPORTS_DIR / f"audit-rapport_{timestamp}.{fmt}")

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

        def _execute():
            from omega_fire.application.commands.export_audit_report import (
                ExportAuditReportCommand,
                ExportAuditReportRequest,
            )

            adapters = {
                "nftables": self._container.get_firewall_port("nftables"),
                "iptables": self._container.get_firewall_port("iptables"),
                "ip6tables": self._container.get_firewall_port("ip6tables"),
            }
            try:
                adapters["fail2ban"] = self._container.get_fail2ban_port()
            except Exception:
                adapters["fail2ban"] = None

            command = ExportAuditReportCommand(
                rule_repository=self._container.rule_repository,
                ban_repository=self._container.ban_repository,
                registry=self._container.capability_registry,
                adapters=adapters,
                audit_logger=self._container.audit_logger,
                db_connection=self._container.db_connection,
                html_exporter=self._container.html_exporter if fmt == "html" else None,
            )
            return command.execute(ExportAuditReportRequest(
                format=fmt, destination=destination, theme_name=theme_name,
            ))

        def _on_done(result) -> None:
            if not result.success:
                self.app.notify(f"Echec de la generation : {result.message}", severity="error")
                log_action_result(self._container, _ACTION_TITLE, status="failure", error=result.message)
                return
            self.app.notify(f"Rapport genere : {result.file_path}", severity="information")
            log_action_result(self._container, _ACTION_TITLE, status="success")
            self.dismiss()

        def _on_error(error: Exception) -> None:
            self.app.notify(f"Echec de la generation : {error}", severity="error")
            log_action_result(self._container, _ACTION_TITLE, status="failure", error=str(error))

        self.run_blocking(_execute, _on_done, busy_message="Generation du rapport en cours...", on_error=_on_error)
