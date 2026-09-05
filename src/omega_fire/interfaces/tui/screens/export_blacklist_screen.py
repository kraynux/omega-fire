# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 6.1 — Exporter la blacklist complete (JSON/TXT/HTML). Patron #3
(source epinglee/manuelle, theme HTML conditionnel). Logique identique a
interfaces/cli/actions.py::action_6_1_export_blacklist.

Simplification assumee : en cas de conflit de nom de fichier, le CLI
propose un sous-menu (renommer automatiquement / ecraser) — ici,
toujours renommer automatiquement avec horodatage (comportement par
defaut du CLI sur Entree), sans sous-dialogue supplementaire."""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Input, Select, Static

from omega_fire.application.commands.manage_pinned_log_paths import ManagePinnedLogPathsCommand
from omega_fire.infrastructure.config.paths import (
    BLOCKLIST_DIR,
    DEFAULT_BLOCKLIST_FILE,
    DEFAULT_PINNED_FILES,
    EXPORTS_DIR,
    RUNTIME_DIR,
)
from omega_fire.infrastructure.storage.files.json_store import JsonStore
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.screens.pinned_paths_screen import PinnedPathsScreen
from omega_fire.interfaces.tui.support.action_audit import log_action_result

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ACTION_TITLE = "6.1 Exporter la blacklist"
_SRC_MANUAL = "__manual__"

_HTML_THEMES: dict[str, str] = {
    "omega-base": "Omega-base (sombre bleu nuit / cyan - defaut)",
    "omega-burn": "Omega-burn (sombre braise rouge-orange)",
    "omega-neon": "Omega-neon (sombre cyberpunk cyan/magenta)",
    "light-basic": "Light-basic (clair sobre, rapport professionnel)",
    "light-alt": "Light-alt (clair papier creme / vert foret)",
}


class ExportBlacklistScreen(OmegaScreen):
    """Export de la blacklist complete vers JSON/TXT/HTML."""

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container
        self._pinned_command = ManagePinnedLogPathsCommand(
            JsonStore(RUNTIME_DIR),
            relative_path="blocklist_analysis_pinned_paths.json",
            defaults=[str(p) for p in DEFAULT_PINNED_FILES],
        )

    def _source_options(self) -> list[tuple[str, str]]:
        return [(p, p) for p in self._pinned_command.list_paths()] + [("Chemin manuel", _SRC_MANUAL)]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="omega-form-panel"):
            yield Static("EXPORTER LA BLACKLIST COMPLETE", classes="omega-title")

            yield Static("Fichier source", classes="omega-subtitle")
            yield Select(self._source_options(), id="source-select")
            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button("Gerer les epingles", id="manage-pins")

            yield Static("Chemin manuel", id="manual-label", classes="omega-subtitle omega-hidden")
            yield Input(value=str(DEFAULT_BLOCKLIST_FILE), id="manual-input", classes="omega-hidden")

            yield Static("Format", classes="omega-subtitle")
            yield Select(
                [("JSON (brut structure)", "json"), ("TXT (1 IP par ligne, reinjectable)", "txt"),
                 ("HTML (rapport visuel 3 colonnes)", "html")],
                value="json",
                id="format-select",
            )

            yield Static("Theme HTML", id="theme-label", classes="omega-subtitle omega-hidden")
            yield Select(
                [(label, name) for name, label in _HTML_THEMES.items()],
                value="omega-base",
                id="theme-select",
                classes="omega-hidden",
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
        options = self._source_options()
        if options:
            self.query_one("#source-select", Select).value = options[0][1]
        self._refresh_default_path("json")

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "source-select":
            is_manual = str(event.value) == _SRC_MANUAL
            self.query_one("#manual-label", Static).set_class(not is_manual, "omega-hidden")
            self.query_one("#manual-input", Input).set_class(not is_manual, "omega-hidden")
        elif event.select.id == "format-select":
            fmt = str(event.value)
            is_html = fmt == "html"
            self.query_one("#theme-label", Static).set_class(not is_html, "omega-hidden")
            self.query_one("#theme-select", Select).set_class(not is_html, "omega-hidden")
            self._refresh_default_path(fmt)

    def _refresh_default_path(self, fmt: str) -> None:
        target_dir = EXPORTS_DIR if fmt == "html" else BLOCKLIST_DIR
        self.query_one("#path-input", Input).value = str(target_dir / f"export-blacklist.{fmt}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss()
            return
        if event.button.id == "manage-pins":
            self.app.push_screen(PinnedPathsScreen(container=self._container), self._refresh_source_select)
            return
        if event.button.id != "launch":
            return
        self._launch()

    def _refresh_source_select(self, _result: None) -> None:
        self.query_one("#source-select", Select).set_options(self._source_options())

    def _launch(self) -> None:
        source = self.query_one("#source-select", Select).value
        if source == _SRC_MANUAL or source is None or source == Select.BLANK:
            selected_source = self.query_one("#manual-input", Input).value.strip()
        else:
            selected_source = str(source)
        if not selected_source or not os.path.isfile(selected_source):
            self.app.notify(f"Fichier introuvable : {selected_source}", severity="error")
            return

        try:
            with open(selected_source, "r", encoding="utf-8") as f:
                ips_list = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        except Exception as e:
            self.app.notify(f"Impossible de lire le fichier source : {e}", severity="error")
            return
        if not ips_list:
            self.app.notify(f"Le fichier '{selected_source}' ne contient aucune IP valide a exporter.", severity="warning")
            return

        fmt = str(self.query_one("#format-select", Select).value)
        theme_name = str(self.query_one("#theme-select", Select).value) if fmt == "html" else "omega-base"
        final_path = self.query_one("#path-input", Input).value.strip()
        if not final_path:
            self.app.notify("Saisissez un chemin de destination.", severity="warning")
            return

        if os.path.exists(final_path):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_dir = os.path.dirname(final_path)
            name, ext = os.path.splitext(os.path.basename(final_path))
            final_path = os.path.join(base_dir, f"{name}_{timestamp}{ext}")

        try:
            dest_folder = os.path.dirname(final_path)
            if dest_folder and not os.path.exists(dest_folder):
                os.makedirs(dest_folder, exist_ok=True)

            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if fmt == "json":
                export_data = {
                    "source": "Omega-Fire", "type": "Blacklist Export", "source_file": selected_source,
                    "exported_at": now_str, "total_ips": len(ips_list), "ips": ips_list,
                }
                with open(final_path, "w", encoding="utf-8") as f:
                    json.dump(export_data, f, indent=4, ensure_ascii=False)

            elif fmt == "txt":
                lines = [
                    "# Omega-Fire Blacklist Export", f"# Source : {selected_source}",
                    f"# Genere le : {now_str}", f"# Total IPs : {len(ips_list)}", "",
                ]
                lines.extend(ips_list)
                with open(final_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines) + "\n")

            elif fmt == "html":
                col_size = (len(ips_list) + 2) // 3
                col1, col2, col3 = ips_list[0:col_size], ips_list[col_size:col_size * 2], ips_list[col_size * 2:]
                max_rows = max(len(col1), len(col2), len(col3))
                ip_rows = [
                    (col1[r] if r < len(col1) else "", col2[r] if r < len(col2) else "", col3[r] if r < len(col3) else "")
                    for r in range(max_rows)
                ]
                exporter = self._container.get_exporter_port("html")
                exporter.export_data(
                    {
                        "page_title": "Exportation Blacklist - Omega-Fire",
                        "heading": "Rapport d'exportation Blacklist",
                        "source_label": "Source", "source_value": "Blacklist Globale",
                        "generated_at": now_str, "total_ips": len(ips_list),
                        "ip_rows": ip_rows, "theme_name": theme_name,
                    },
                    final_path,
                    template_name="ip_export.html.j2",
                )
        except Exception as e:
            self.app.notify(f"Erreur lors de l'ecriture du fichier d'export : {e}", severity="error")
            log_action_result(self._container, _ACTION_TITLE, status="failure", error=str(e))
            return

        self.app.notify(f"Export reussi : {len(ips_list)} IP(s) enregistree(s) dans '{final_path}'.")
        log_action_result(self._container, _ACTION_TITLE, status="success")
        self.dismiss()
