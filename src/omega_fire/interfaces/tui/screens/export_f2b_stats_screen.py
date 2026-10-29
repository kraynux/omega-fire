# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 6.4 — Exporter les statistiques Fail2ban (TXT/HTML). Meme
structure que ExportAuditScreen (6.3). Logique identique a
interfaces/cli/actions.py::action_6_4_export_f2b_stats."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Input, Select, Static

from omega_fire.interfaces.tui.export_language import export_translation
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.support.action_audit import log_action_result
from omega_fire.shared.i18n import _, translating_as

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ACTION_TITLE = "6.4 Rapport détaillé Fail2ban"

_HTML_THEMES: dict[str, str] = {
    "omega-base": _("Omega-base (sombre bleu nuit / cyan - défaut)"),
    "omega-burn": _("Omega-burn (sombre braise rouge-orange)"),
    "omega-neon": _("Omega-neon (sombre cyberpunk cyan/magenta)"),
    "light-basic": _("Light-basic (clair sobre, rapport professionnel)"),
    "light-alt": _("Light-alt (clair papier crème / vert forêt)"),
}


class ExportF2bStatsScreen(OmegaScreen):
    """Export du rapport detaille Fail2ban (jails, bans, service, historique)."""

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="omega-form-panel"):
            yield Static(_("RAPPORT DÉTAILLÉ FAIL2BAN"), classes="omega-title")

            yield Static(_("Format"), classes="omega-subtitle")
            yield Select(
                [(_("HTML (rapport visuel lisible)"), "html"), (_("TXT (rapport texte brut)"), "txt")],
                value="html",
                id="format-select",
            )

            yield Static(_("Thème HTML"), id="theme-label", classes="omega-subtitle")
            yield Select(
                [(label, name) for name, label in _HTML_THEMES.items()],
                value="omega-base",
                id="theme-select",
            )

            yield Static(_("Chemin de destination"), classes="omega-subtitle")
            yield Input(id="path-input")

            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Exporter"), id="launch", variant="primary")
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Retour"), id="back")
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
        self.query_one("#path-input", Input).value = str(self._container.exports_dir / f"f2b-rapport_{timestamp}.{fmt}")

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
            self.app.notify(_("Saisissez un chemin de destination."), severity="warning")
            return

        # Lue ici (fil de l'interface), appliquee dans le thread qui produit le rapport.
        export_state = export_translation(self, self._container)

        def _execute():
            from omega_fire.application.commands.export_f2b_report import (
                ExportF2bReportCommand,
                ExportF2bReportRequest,
            )
            from omega_fire.infrastructure.backends.fail2ban.history_reader import Fail2banHistoryReader
            from omega_fire.infrastructure.backends.fail2ban.service_controller import (
                Fail2banServiceController,
            )

            command = ExportF2bReportCommand(
                fail2ban_adapter=self._container.get_fail2ban_port(),
                service_controller=Fail2banServiceController(),
                history_reader=Fail2banHistoryReader(),
                html_exporter=self._container.html_exporter if fmt == "html" else None,
            )
            with translating_as(export_state):
                return command.execute(ExportF2bReportRequest(
                    format=fmt, destination=destination, theme_name=theme_name,
                ))

        def _on_done(result) -> None:
            if not result.success:
                self.app.notify(_("Échec de la génération : {message}").format(message=result.message), severity="error")
                log_action_result(self._container, _ACTION_TITLE, status="failure", error=result.message)
                return
            self.app.notify(_("Rapport généré : {file_path}").format(file_path=result.file_path), severity="information")
            log_action_result(self._container, _ACTION_TITLE, status="success")
            self.dismiss()

        def _on_error(error: Exception) -> None:
            self.app.notify(_("Échec de la génération : {error}").format(error=error), severity="error")
            log_action_result(self._container, _ACTION_TITLE, status="failure", error=str(error))

        self.run_blocking(_execute, _on_done, busy_message=_("Génération du rapport en cours..."), on_error=_on_error)
