# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecrans 8.3 (7 jours) et 8.4 (30 jours) — rapports statistiques. Un seul
ecran parametre par periode (meme raison que CapabilitiesScreen pour 1.1/1.4,
et que interfaces/cli/actions.py::_render_stats_report_screen deja partagee
par les deux actions cote CLI). Meme source de donnees
(BuildStatsReportQuery), rapport reconstruit a la demande (pas de
set_interval — le rapport ne varie pas en continu entre deux actions
utilisateur, meme choix que 5.8/8.2). Contenu (KPI/histogramme/tendance/
tableaux/gestion/evolution) porte ligne a ligne depuis
_build_kpi_table/_build_top_tables_columns/_build_management_evolution_columns
(actions.py) et ascii_charts.py/daily_trend_chart.py/management_panel.py/
rules_evolution_panel.py, avec la palette d'extension omega-fire a la place
de theme_registry.get_style()."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, DataTable, Footer, Header, Select, Static

from omega_fire.application.queries.build_stats_report import (
    BuildStatsReportQuery,
    BuildStatsReportRequest,
)
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.support.action_audit import log_action_result

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_CHART_HEIGHT = 4
_CHART_BLOCKS = [" ", " ", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
_TREND_BAR_WIDTH = 30

_HTML_THEMES: dict[str, str] = {
    "omega-base": "Omega-base (sombre bleu nuit / cyan - defaut)",
    "omega-burn": "Omega-burn (sombre braise rouge-orange)",
    "omega-neon": "Omega-neon (sombre cyberpunk cyan/magenta)",
    "light-basic": "Light-basic (clair sobre, rapport professionnel)",
    "light-alt": "Light-alt (clair papier creme / vert foret)",
}


class StatsReportScreen(OmegaScreen):
    """8.3/8.4 — rapport statistique complet sur 7 ou 30 jours."""

    def __init__(self, *, container: DependencyContainer, period_code: str, period_label: str, title: str, period_suffix: str) -> None:
        super().__init__()
        self._container = container
        self._period_code = period_code
        self._period_label = period_label
        self._title = title
        self._period_suffix = period_suffix
        self._result = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="omega-panel"):
            yield Static(self._title, classes="omega-title")
            yield Static("", id="report-hint", classes="omega-hint")

            with Horizontal(id="kpi-row"):
                yield Static(id="kpi-events", classes="omega-dash-box dash-box-short")
                yield Static(id="kpi-bans", classes="omega-dash-box dash-box-short")
                yield Static(id="kpi-top-jail", classes="omega-dash-box dash-box-short")
                yield Static(id="kpi-peak", classes="omega-dash-box dash-box-short")

            yield Static(id="box-hourly-chart", classes="omega-dash-box")
            yield Static(id="box-trend-chart", classes="omega-dash-box")

            with Horizontal(id="tables-row"):
                yield DataTable(id="top-ips-table")
                yield DataTable(id="top-jails-table")

            with Horizontal(id="mgmt-row"):
                yield Static(id="box-management", classes="omega-dash-box")
                yield Static(id="box-evolution", classes="omega-dash-box")

            yield Select(
                [(label, name) for name, label in _HTML_THEMES.items()],
                value="omega-base",
                id="theme-select",
            )
            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button("Rafraichir", id="refresh", variant="primary")
                with Container(classes="omega-btn-frame"):
                    yield Button("Exporter HTML", id="export")
                with Container(classes="omega-btn-frame"):
                    yield Button("Retour", id="back")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#top-ips-table", DataTable).add_columns("#", "Adresse IP", "Bans", "Dernier Ban")
        self.query_one("#top-jails-table", DataTable).add_columns("Jail / Service", "Statut", "Bans", "Part")
        self._refresh()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "back":
            self.dismiss()
            return
        if button_id == "refresh":
            self._refresh()
            return
        if button_id == "export":
            self._export()

    def _colors(self) -> dict[str, str]:
        v = self.app.get_css_variables()
        return {
            "main": v.get("foreground", ""),
            "danger": v.get("error", ""),
            "warning": v.get("warning", ""),
            "info": v.get("secondary", ""),
            "heading": f"bold {v.get('primary', '')}".strip(),
            "available": v.get("status-available", ""),
        }

    def _refresh(self) -> None:
        colors = self._colors()

        audit_port = self._safe(getattr(self._container, "get_audit_port", None))
        persistence_port = self._safe(getattr(self._container, "get_persistence_port", None))

        result = BuildStatsReportQuery(
            audit_port=audit_port, persistence_port=persistence_port,
        ).execute(BuildStatsReportRequest(period_code=self._period_code, period_label=self._period_label))
        self._result = result

        hint = self.query_one("#report-hint", Static)
        if not result.success:
            hint.update(result.message)
            log_action_result(self._container, self._title, status="failure", error=result.message)
            return
        hint.update(f"Source : {result.kpi.get('data_source', 'Inconnue')}")

        self.query_one("#kpi-events", Static).update(
            Text(f"Evenements\n\n{result.kpi.get('total_events', 0)}\n", style=colors["info"])
            + Text(f"Logs scannes ({result.kpi.get('data_source', 'Inconnue')})", style="dim")
        )
        self.query_one("#kpi-bans", Static).update(
            Text(f"Total Bans\n\n{result.kpi.get('total_bans', 0)}\n", style=colors["danger"])
            + Text("Adresses IP bloquees", style="dim")
        )
        self.query_one("#kpi-top-jail", Static).update(
            Text(f"Top Jail\n\n{result.kpi.get('top_jail_name', 'Aucun')}\n", style=colors["warning"])
            + Text("Service le plus cible", style="dim")
        )
        self.query_one("#kpi-peak", Static).update(
            Text(f"Heure de Pointe\n\n{result.kpi.get('peak_hour', '--:--')}\n", style=colors["main"])
            + Text(f"Pic ({result.kpi.get('peak_count', 0)} evts)", style="dim")
        )

        self.query_one("#box-hourly-chart", Static).update(
            self._render_hourly_chart(colors, result.hourly_series, "box-hourly-chart")
        )
        self.query_one("#box-trend-chart", Static).update(
            self._render_daily_trend(colors, result.daily_trend)
        )

        ips_table = self.query_one("#top-ips-table", DataTable)
        ips_table.clear()
        if not result.top_ips:
            ips_table.add_row("-", "Aucune donnee", "0", "--:--")
        else:
            for idx, ip_stat in enumerate(result.top_ips[:8], 1):
                ips_table.add_row(str(idx), ip_stat["ip"], str(ip_stat["total_bans"]), ip_stat["last_ban"][11:19])

        jails_table = self.query_one("#top-jails-table", DataTable)
        jails_table.clear()
        if not result.top_jails:
            jails_table.add_row("Aucune donnee", "-", "0", "")
        else:
            for jail in result.top_jails[:8]:
                status = Text("● Actif", style=colors["available"]) if jail["is_active"] else Text("○ Archive", style="dim")
                bar_len = int(jail["percentage"] / 10)
                part = f"{'█' * bar_len}{'░' * (10 - bar_len)} {jail['percentage']}%"
                jails_table.add_row(jail["name"], status, str(jail["total_bans"]), part)

        self.query_one("#box-management", Static).update(self._render_management(colors, result.management))
        self.query_one("#box-evolution", Static).update(self._render_evolution(colors, result.rules_evolution))

        log_action_result(self._container, self._title, status="success")

    @staticmethod
    def _safe(factory):
        if factory is None:
            return None
        try:
            return factory()
        except Exception:
            return None

    def _render_hourly_chart(self, colors: dict, data: list[int], widget_id: str) -> Text:
        max_val = max(data) if data and max(data) > 0 else 1
        box = self.query_one(f"#{widget_id}", Static)
        available_width = max(48, (box.size.width - 4) or 70)
        spacing_factor = max(1, (available_width - 24) // 23)
        gap = " " * spacing_factor

        lines: list[Text] = []
        for level in range(_CHART_HEIGHT, 0, -1):
            line_text = Text()
            for idx, val in enumerate(data):
                scaled = (val / max_val) * _CHART_HEIGHT
                if scaled >= level:
                    style = colors["danger"] if (val == max_val and val > 0) else colors["main"]
                    line_text.append("█", style=style)
                elif scaled > level - 1:
                    b_idx = int((scaled - (level - 1)) * (len(_CHART_BLOCKS) - 1))
                    line_text.append(_CHART_BLOCKS[b_idx], style=colors["main"])
                else:
                    line_text.append(" ")
                if idx < len(data) - 1:
                    line_text.append(gap)
            lines.append(line_text)

        hours_top = gap.join(f"{h:02d}"[0] + (" " if spacing_factor > 1 else "") for h in range(24))
        hours_bottom = gap.join(f"{h:02d}"[1] + (" " if spacing_factor > 1 else "") for h in range(24))
        chart_width = len(lines[0].plain) if lines else available_width

        content = Text()
        content.append(f"Distribution Horaire (24h) — Max: {max_val} bans/h\n\n", style=colors["heading"])
        for line in lines:
            content.append_text(line)
            content.append("\n")
        content.append("─" * chart_width + "\n", style="dim")
        content.append(hours_top + "\n", style="dim")
        content.append(hours_bottom, style="dim")
        return content

    def _render_daily_trend(self, colors: dict, data: list[tuple[str, int]]) -> Text:
        content = Text()
        if not data:
            content.append("Tendance Journaliere\n\n", style=colors["heading"])
            content.append("Aucune donnee disponible pour cette periode.", style="dim")
            return content

        values = [count for _, count in data]
        max_val = max(values) if max(values) > 0 else 1
        label_width = max(len(label) for label, _ in data)

        first_val, last_val = data[0][1], data[-1][1]
        trend_suffix = " ▲" if last_val > first_val else (" ▼" if last_val < first_val else " =")
        content.append(f"Tendance Journaliere{trend_suffix}\n\n", style=colors["heading"])

        for label, count in data:
            bar_len = int((count / max_val) * _TREND_BAR_WIDTH) if max_val > 0 else 0
            bar_style = colors["danger"] if count == max_val and count > 0 else colors["main"]
            content.append(f"  {label:<{label_width}} ", style="dim")
            content.append("█" * bar_len, style=bar_style)
            content.append("░" * (_TREND_BAR_WIDTH - bar_len), style="dim")
            content.append(f"  {count}\n", style=colors["main"])
        return content

    def _render_management(self, colors: dict, management: dict) -> Text:
        content = Text()
        content.append("── ACTIVITE ─────────────────\n", style=colors["heading"])
        content.append(f"  Changements de profil / regles : {management.get('rule_changes', 0)}\n", style=colors["main"])
        content.append(f"  Sauvegardes effectuees         : {management.get('backups', 0)}\n", style=colors["main"])
        content.append(f"  Restaurations effectuees       : {management.get('restores', 0)}\n", style=colors["main"])

        success_rate = management.get("success_rate", 0.0)
        total_actions = management.get("total_actions", 0)
        content.append("\n── FIABILITE ────────────────\n", style=colors["heading"])
        rate_style = colors["available"] if success_rate >= 95 else (colors["warning"] if success_rate >= 80 else colors["danger"])
        content.append("  Taux de succes : ", style=colors["main"])
        content.append(f"{success_rate:.1f}%", style=rate_style)
        content.append(f"  ({total_actions} action(s) au total)\n", style="dim")

        recent_entries = management.get("recent_entries", [])
        if recent_entries:
            content.append("\n── DERNIERES ACTIONS ────────\n", style=colors["heading"])
            for time_label, description, success in recent_entries:
                symbol = "✔" if success else "✗"
                style = colors["available"] if success else colors["danger"]
                content.append(f"  [{time_label}] ", style="dim")
                content.append(f"{symbol} ", style=style)
                content.append(f"{description}\n", style=colors["main"])
        else:
            content.append("\n  Aucune action enregistree sur cette periode.\n", style="dim")
        return content

    def _render_evolution(self, colors: dict, points: list[tuple[str, int, int]]) -> Text:
        content = Text()
        content.append("── EVOLUTION DES REGLES & IPs BANNIES ──\n\n", style=colors["heading"])
        if not points:
            content.append(
                "Aucun snapshot disponible sur cette periode — impossible de "
                "mesurer l'evolution des regles/IPs bannies. Voir menu 7.1.\n",
                style="dim",
            )
            return content

        rules_values = [r for _, r, _ in points]
        ips_values = [i for _, _, i in points]
        spark_chars = "▁▂▃▄▅▆▇█"

        def sparkline(values: list[int]) -> str:
            max_val = max(values) if max(values) > 0 else 1
            return "".join(
                spark_chars[min(int((v / max_val) * (len(spark_chars) - 1)), len(spark_chars) - 1)]
                for v in values
            )

        content.append(
            f"{len(points)} point(s) de mesure sur la periode.\n"
            f"Reflete les sauvegardes disponibles, pas un suivi continu.\n\n",
            style="dim",
        )
        content.append("  Regles actives : ", style=colors["main"])
        content.append(sparkline(rules_values), style=colors["info"])
        content.append(f"   ({rules_values[0]} → {rules_values[-1]})\n", style="dim")
        content.append("  IPs bannies    : ", style=colors["main"])
        content.append(sparkline(ips_values), style=colors["danger"])
        content.append(f"   ({ips_values[0]} → {ips_values[-1]})\n\n", style="dim")

        content.append("── DETAIL DES POINTS ────────\n", style=colors["heading"])
        for date_label, rules_count, ips_count in points:
            content.append(f"  {date_label:<14} ", style="dim")
            content.append(f"Regles: {rules_count:<4} ", style=colors["info"])
            content.append(f"IPs: {ips_count}\n", style=colors["danger"])
        return content

    def _export(self) -> None:
        if self._result is None or not self._result.success:
            self.app.notify("Aucun rapport a exporter.", severity="warning")
            return
        try:
            from omega_fire.domain.reports.serializers import report_to_serializable
            from omega_fire.infrastructure.config.paths import EXPORTS_DIR, TEMPLATES_DIR
            from omega_fire.infrastructure.exporters.html_exporter import HtmlExporter

            theme_name = str(self.query_one("#theme-select", Select).value)
            EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = EXPORTS_DIR / f"stats_report_{self._period_suffix}_{timestamp}.html"

            data = report_to_serializable(self._result.report)
            data["theme_name"] = theme_name

            exporter = HtmlExporter(templates_dir=TEMPLATES_DIR)
            exporter.export_data(data, output_path, template_name="stats_report.html.j2")
        except Exception as e:
            self.app.notify(f"Echec de l'export : {e}", severity="error")
            log_action_result(self._container, self._title, status="failure", error=str(e))
            return

        self.app.notify(f"Rapport exporte : {output_path}")
        log_action_result(self._container, self._title, status="success")
