# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 8.2 — Etat des connexions (Conntrack). Instantane (pas de
rafraichissement automatique — relance manuelle via le bouton), avec
filtres protocole/etat/limite et export HTML. Logique identique a
interfaces/cli/actions.py::action_8_2_conntrack_status."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, DataTable, Footer, Header, Input, Select, Static

from omega_fire.application.queries.conntrack_status import get_conntrack_status
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.support.action_audit import log_action_result

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ACTION_TITLE = "8.2 Etat des connexions (Conntrack)"
_ALL = "__all__"

_HTML_THEMES: dict[str, str] = {
    "omega-base": "Omega-base (sombre bleu nuit / cyan - defaut)",
    "omega-burn": "Omega-burn (sombre braise rouge-orange)",
    "omega-neon": "Omega-neon (sombre cyberpunk cyan/magenta)",
    "light-basic": "Light-basic (clair sobre, rapport professionnel)",
    "light-alt": "Light-alt (clair papier creme / vert foret)",
}


class ConntrackScreen(OmegaScreen):
    """Instantane des connexions suivies par conntrack, filtrable."""

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container
        try:
            self._monitoring_port = container.get_monitoring_port()
        except Exception:
            self._monitoring_port = None
        self._result = None

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(classes="omega-panel"):
            yield Static("ETAT DES CONNEXIONS (CONNTRACK)", classes="omega-title")

            if self._monitoring_port is None:
                yield Static("Port de monitoring non disponible.", classes="omega-hint")
                with Horizontal(classes="omega-actions"), Container(classes="omega-btn-frame"):
                    yield Button("Retour", id="back")
                yield Footer()
                return

            yield Static("", id="summary-hint", classes="omega-hint")

            yield Select([("Tous les protocoles", _ALL)], value=_ALL, id="protocol-select")
            yield Select([("Tous les etats", _ALL)], value=_ALL, id="state-select")
            yield Input(value="100", id="limit-input")
            with Horizontal(classes="omega-actions"), Container(classes="omega-btn-frame"):
                yield Button("Filtrer / Rafraichir", id="filter", variant="primary")

            yield DataTable(id="connections-table")

            yield Select(
                [(label, name) for name, label in _HTML_THEMES.items()],
                value="omega-base",
                id="theme-select",
            )
            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button("Exporter HTML", id="export")
                with Container(classes="omega-btn-frame"):
                    yield Button("Retour", id="back")
        yield Footer()

    def on_mount(self) -> None:
        if self._monitoring_port is None:
            return
        table = self.query_one("#connections-table", DataTable)
        table.add_columns("Protocole", "Source", "Destination", "Etat", "Paquets", "Octets", "Timeout")
        self._fetch_and_render()

    def _fetch_and_render(self, protocol_filter: str = "", state_filter: str = "", limit: int = 100) -> None:
        self._result = get_conntrack_status(
            monitoring_port=self._monitoring_port,
            protocol_filter=protocol_filter,
            state_filter=state_filter,
            limit=limit,
        )
        result = self._result

        hint = self.query_one("#summary-hint", Static)
        filters_desc = []
        if protocol_filter:
            filters_desc.append(f"protocole={protocol_filter}")
        if state_filter:
            filters_desc.append(f"etat={state_filter}")
        filters_str = f" (filtres : {', '.join(filters_desc)})" if filters_desc else ""
        hint.update(f"{result.total_count} connexion(s) au total{filters_str}. {result.message}")

        protocol_select = self.query_one("#protocol-select", Select)
        protocol_select.set_options(
            [("Tous les protocoles", _ALL)] + [(f"{p} ({c})", p) for p, c in result.by_protocol.items()]
        )
        protocol_select.value = protocol_filter or _ALL

        state_select = self.query_one("#state-select", Select)
        state_select.set_options(
            [("Tous les etats", _ALL)] + [(f"{s} ({c})", s) for s, c in result.by_state.items()]
        )
        state_select.value = state_filter or _ALL

        table = self.query_one("#connections-table", DataTable)
        table.clear()
        for entry in result.entries:
            table.add_row(
                entry.protocol,
                f"{entry.source_ip}:{entry.source_port}" if entry.source_port else entry.source_ip,
                f"{entry.destination_ip}:{entry.destination_port}" if entry.destination_port else entry.destination_ip,
                entry.state,
                str(entry.packets),
                str(entry.bytes),
                str(entry.timeout),
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss()
            return
        if event.button.id == "filter":
            self._apply_filter()
            return
        if event.button.id == "export":
            self._export()

    def _apply_filter(self) -> None:
        protocol = self.query_one("#protocol-select", Select).value
        protocol_filter = "" if protocol in (None, Select.BLANK, _ALL) else str(protocol)
        state = self.query_one("#state-select", Select).value
        state_filter = "" if state in (None, Select.BLANK, _ALL) else str(state)
        limit_raw = self.query_one("#limit-input", Input).value.strip()
        try:
            limit = int(limit_raw) if limit_raw else 100
        except ValueError:
            self.app.notify("Nombre invalide, valeur precedente conservee.", severity="warning")
            limit = 100
        self._fetch_and_render(protocol_filter=protocol_filter, state_filter=state_filter, limit=limit)

    def _export(self) -> None:
        if self._result is None:
            return
        try:
            from omega_fire.infrastructure.config.paths import EXPORTS_DIR, TEMPLATES_DIR
            from omega_fire.infrastructure.exporters.html_exporter import HtmlExporter

            theme_name = str(self.query_one("#theme-select", Select).value)
            EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = EXPORTS_DIR / f"conntrack-rapport_{timestamp}.html"

            result = self._result
            data = {
                "page_title": "Export Conntrack - Omega-Fire",
                "heading": "Rapport des connexions Conntrack",
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "filters_label": "",
                "total_count": result.total_count,
                "by_protocol": result.by_protocol,
                "by_state": result.by_state,
                "entries": result.entries,
                "theme_name": theme_name,
            }
            exporter = HtmlExporter(templates_dir=TEMPLATES_DIR)
            exporter.export_data(data, output_path, template_name="conntrack_export.html.j2")
        except Exception as e:
            self.app.notify(f"Echec de l'export : {e}", severity="error")
            log_action_result(self._container, _ACTION_TITLE, status="failure", error=str(e))
            return

        self.app.notify(f"Rapport exporte : {output_path}")
        log_action_result(self._container, _ACTION_TITLE, status="success")
