# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 6.2 — Exporter les regles (nftables/iptables, ruleset). Patron
#3 (filtre de contenu + theme HTML conditionnel). Logique identique a
interfaces/cli/actions.py::action_6_2_export_rules."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Input, Select, Static

from omega_fire.application.queries.export_rules_summary import (
    ExportRulesSummaryQuery,
    ExportRulesSummaryRequest,
)
from omega_fire.infrastructure.config.paths import EXPORTS_DIR
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.support.action_audit import log_action_result

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ACTION_TITLE = "6.2 Exporter les regles"

_HTML_THEMES: dict[str, str] = {
    "omega-base": "Omega-base (sombre bleu nuit / cyan - defaut)",
    "omega-burn": "Omega-burn (sombre braise rouge-orange)",
    "omega-neon": "Omega-neon (sombre cyberpunk cyan/magenta)",
    "light-basic": "Light-basic (clair sobre, rapport professionnel)",
    "light-alt": "Light-alt (clair papier creme / vert foret)",
}

_CONTENT_OPTIONS: dict[str, tuple[str, bool, str]] = {
    "all": ("all", False, "Toutes les regles"),
    "active": ("all", True, "Regles actives uniquement"),
    "managed": ("managed", False, "Regles Omega-Fire uniquement (creees via 3.1)"),
    "imported": ("imported", False, "Regles Systeme importees uniquement (detectees via 3.3)"),
}


class ExportRulesScreen(OmegaScreen):
    """Export du ruleset nftables/iptables (fail2ban a son propre export, 4.8)."""

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="omega-form-panel"):
            yield Static("EXPORTER LES REGLES", classes="omega-title")
            yield Static(
                "Fail2ban dispose de son propre export (menu 4.8) — ici, uniquement nftables/iptables.",
                classes="omega-hint",
            )

            yield Static("Contenu a exporter", classes="omega-subtitle")
            yield Select(
                [(label, key) for key, (_, __, label) in _CONTENT_OPTIONS.items()],
                value="all",
                id="content-select",
            )

            yield Static("Format", classes="omega-subtitle")
            yield Select(
                [("HTML (rapport visuel lisible)", "html"), ("JSON (donnees brutes structurees)", "json"),
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
        self.query_one("#path-input", Input).value = str(EXPORTS_DIR / f"rules-nft-ipt_{timestamp}.{fmt}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss()
            return
        if event.button.id != "launch":
            return

        rule_repository = getattr(self._container, "rule_repository", None)
        if rule_repository is None:
            self.app.notify("Le conteneur ou le depot de regles n'est pas disponible.", severity="error")
            return

        content_key = str(self.query_one("#content-select", Select).value)
        origin_filter, active_only, filter_label = _CONTENT_OPTIONS[content_key]
        result = ExportRulesSummaryQuery(rule_repository).execute(
            ExportRulesSummaryRequest(origin_filter=origin_filter, active_only=active_only)
        )
        if not result.success or not result.full_list:
            self.app.notify(result.message, severity="warning")
            return

        fmt = str(self.query_one("#format-select", Select).value)
        theme_name = str(self.query_one("#theme-select", Select).value) if fmt == "html" else "omega-base"
        path_raw = self.query_one("#path-input", Input).value.strip()
        if not path_raw:
            self.app.notify("Saisissez un chemin de destination.", severity="warning")
            return
        output_path = Path(path_raw)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            if fmt == "html":
                groups_data = []
                for group in result.groups:
                    rep = group.representative
                    chain_val = rep.chain.value.upper() if hasattr(rep.chain, "value") else str(rep.chain).upper()
                    action_val = rep.action.value.upper() if hasattr(rep.action, "value") else str(rep.action).upper()
                    proto_val = rep.protocol.value.upper() if rep.protocol and hasattr(rep.protocol, "value") else "ALL"
                    origins = []
                    for r in group.rules:
                        label = "OMEGA" if r.origin == "managed" else "SYSTEME"
                        if label not in origins:
                            origins.append(label)
                    groups_data.append({
                        "backend": rep.backend, "origins": origins, "chain": chain_val, "action": action_val,
                        "protocol": proto_val, "port": str(rep.port_start) if rep.port_start else "ANY",
                        "source": rep.source_cidr or "ANY", "destination": rep.dest_cidr or "ANY",
                        "state": "ACTIF" if rep.enabled else "INACTIF", "count": group.count, "names": group.names,
                    })
                html_data = {
                    "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "filter_label": filter_label, "total_rules": len(result.full_list),
                    "total_groups": len(result.groups), "groups": groups_data, "theme_name": theme_name,
                }
                exporter = self._container.get_exporter_port("html")
                exporter.export_data(html_data, output_path, template_name="ruleset.html.j2")
            else:
                rules_data = [
                    {
                        "id": r.rule_id, "backend": r.backend, "origin": r.origin,
                        "chain": r.chain.value if hasattr(r.chain, "value") else str(r.chain),
                        "action": r.action.value if hasattr(r.action, "value") else str(r.action),
                        "protocol": r.protocol.value if r.protocol and hasattr(r.protocol, "value") else None,
                        "port_start": r.port_start, "port_end": r.port_end, "source_cidr": r.source_cidr,
                        "dest_cidr": r.dest_cidr, "comment": r.comment, "enabled": r.enabled,
                        "external_ref": r.external_ref, "interface": r.interface,
                    }
                    for r in result.full_list
                ]
                exporter = self._container.get_exporter_port(fmt)
                exporter.export_data(rules_data, output_path)
        except Exception as e:
            self.app.notify(f"Erreur lors de l'export : {e}", severity="error")
            log_action_result(self._container, _ACTION_TITLE, status="failure", error=str(e))
            return

        app_logger = getattr(self._container, "app_logger", None)
        if app_logger:
            app_logger.info(f"Export des regles ({fmt}, {filter_label}) : {output_path}")

        self.app.notify(f"Export termine : {output_path}")
        log_action_result(self._container, _ACTION_TITLE, status="success")
        self.dismiss()
