# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 4.8 — Exporter les IPs d'un jail (JSON/TXT/HTML). Patron #3
(theme HTML conditionnel + chemin prerempli selon jail/format).
Logique identique a interfaces/cli/actions.py::action_4_8_export_jail.

get_jail_status() (fail2ban-client, jusqu'a 10s de timeout) s'execute en
arriere-plan (run_blocking, voir _base.py) — synchrone dans __init__,
elle gelait TOUTE l'app a l'ouverture de cet ecran (retour utilisateur
reel, mode degrade). L'export lui-meme (ecriture fichier locale) reste
synchrone : rapide, pas de risque de gel comparable."""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Input, Select, Static

from omega_fire.application.queries.jail_status import get_jail_status
from omega_fire.infrastructure.config.paths import EXPORTS_DIR
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.support.action_audit import log_action_result

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ACTION_TITLE = "4.8 Exporter les IP d'un jail"

_HTML_THEMES: dict[str, str] = {
    "omega-base": "Omega-base (sombre bleu nuit / cyan - defaut)",
    "omega-burn": "Omega-burn (sombre braise rouge-orange)",
    "omega-neon": "Omega-neon (sombre cyberpunk cyan/magenta)",
    "light-basic": "Light-basic (clair sobre, rapport professionnel)",
    "light-alt": "Light-alt (clair papier creme / vert foret)",
}

_EXT_MAP = {"json": "json", "txt": "txt", "html": "html"}


class ExportJailScreen(OmegaScreen):
    """Export des IPs bannies d'un jail choisi, vers JSON/TXT/HTML."""

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container
        self._jails: dict[str, list[str]] = {}

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="omega-form-panel"):
            yield Static("EXPORTER LES IPs D'UN JAIL", classes="omega-title")
            yield Static("Chargement des jails...", id="status-hint", classes="omega-hint")

            yield Static("Jail", id="jail-label", classes="omega-subtitle omega-hidden")
            yield Select([], id="jail-select", classes="omega-hidden")

            yield Static("Format", id="format-label", classes="omega-subtitle omega-hidden")
            yield Select(
                [("JSON (brut structure)", "json"),
                 ("TXT (1 IP par ligne, reinjectable)", "txt"),
                 ("HTML (rapport visuel 3 colonnes)", "html")],
                value="json",
                id="format-select",
                classes="omega-hidden",
            )

            yield Static("Theme HTML", id="theme-label", classes="omega-subtitle omega-hidden")
            yield Select(
                [(label, name) for name, label in _HTML_THEMES.items()],
                value="omega-base",
                id="theme-select",
                classes="omega-hidden",
            )

            yield Static("Chemin de destination", id="path-label", classes="omega-subtitle omega-hidden")
            yield Input(id="path-input", classes="omega-hidden")

            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button("Exporter", id="launch", variant="primary", disabled=True)
                with Container(classes="omega-btn-frame"):
                    yield Button("Retour", id="back")
        yield Footer()

    def on_mount(self) -> None:
        def _fetch():
            try:
                fail2ban_port = self._container.get_fail2ban_port()
            except Exception:
                fail2ban_port = None
            status = get_jail_status(fail2ban_port=fail2ban_port)
            return {j.name: sorted({str(ip) for ip in j.banned_ips}) for j in status.jails}

        self.run_blocking(_fetch, self._on_loaded, busy_message="Chargement des jails...")

    def _on_loaded(self, jails: dict[str, list[str]]) -> None:
        self._jails = jails
        if not jails:
            self.query_one("#status-hint", Static).update("Impossible de contacter Fail2ban.")
            return

        self.query_one("#status-hint", Static).set_class(True, "omega-hidden")
        for widget_id in ("jail-label", "jail-select", "format-label", "format-select", "path-label", "path-input"):
            self.query_one(f"#{widget_id}").set_class(False, "omega-hidden")

        jail_select = self.query_one("#jail-select", Select)
        jail_select.set_options([(f"{name} ({len(ips)} IP(s))", name) for name, ips in jails.items()])
        jail_select.value = next(iter(jails))

        self.query_one("#launch", Button).disabled = False
        self._refresh_default_path(next(iter(jails)), "json")

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "format-select":
            fmt = str(event.value)
            is_html = fmt == "html"
            self.query_one("#theme-label", Static).set_class(not is_html, "omega-hidden")
            self.query_one("#theme-select", Select).set_class(not is_html, "omega-hidden")
            self._refresh_default_path(str(self.query_one("#jail-select", Select).value), fmt)
        elif event.select.id == "jail-select":
            fmt = str(self.query_one("#format-select", Select).value)
            self._refresh_default_path(str(event.value), fmt)

    def _refresh_default_path(self, jail_name: str, fmt: str) -> None:
        self.query_one("#path-input", Input).value = str(EXPORTS_DIR / f"list-{jail_name}-f2b.{fmt}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss()
            return
        if event.button.id != "launch":
            return
        if not self._jails:
            self.app.notify("Impossible de contacter Fail2ban.", severity="error")
            return

        jail_name = str(self.query_one("#jail-select", Select).value)
        ips_list = self._jails.get(jail_name, [])
        if not ips_list:
            self.app.notify(f"Le jail '{jail_name}' ne contient aucune IP bannie a exporter.", severity="warning")
            return

        fmt = str(self.query_one("#format-select", Select).value)
        theme_name = str(self.query_one("#theme-select", Select).value) if fmt == "html" else "omega-base"
        final_path = self.query_one("#path-input", Input).value.strip()
        if not final_path:
            self.app.notify("Saisissez un chemin de destination.", severity="warning")
            return

        try:
            target_dir = os.path.dirname(final_path)
            if target_dir and not os.path.exists(target_dir):
                os.makedirs(target_dir, exist_ok=True)

            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if fmt == "json":
                export_data = {
                    "source": "Omega-Fire", "jail": jail_name, "exported_at": now_str,
                    "total_ips": len(ips_list), "ips": ips_list,
                }
                with open(final_path, "w", encoding="utf-8") as f:
                    json.dump(export_data, f, indent=4, ensure_ascii=False)

            elif fmt == "txt":
                lines = [
                    f"# Omega-Fire Blocklist Export - Jail: {jail_name}",
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
                        "page_title": f"Exportation Jail Fail2ban - {jail_name}",
                        "heading": f"Rapport d'exportation Jail : {jail_name}",
                        "source_label": "Jail Source", "source_value": jail_name,
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
