# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 5.8 — Statistiques des logs. Meme source de donnees que
interfaces/cli/views/log_stats_view.py::show_log_stats_dashboard
(LogAggregator().get_summary(period_code)), mais recalcul a la demande
(changement de periode / bouton Rafraichir) plutot qu'une boucle Live —
meme choix que l'ecran 8.2 (conntrack) : la donnee source ne change pas
en continu entre deux actions utilisateur, un set_interval serait un
travail de rafraichissement sans valeur ajoutee (voir conntrack_screen.py).
KPI/graphique/tableaux portes ligne a ligne depuis kpi_cards.py/
ascii_charts.py/stat_tables.py (memes donnees, palette d'extension
omega-fire a la place de theme_registry.get_style())."""
from __future__ import annotations

from typing import TYPE_CHECKING

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, DataTable, Footer, Header, Static

from omega_fire.infrastructure.logging.stats.log_aggregator import LogAggregator
from omega_fire.interfaces.tui.screens._base import OmegaScreen

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_PERIODS: dict[str, str] = {"24h": "24h", "7d": "7 jours", "30d": "30 jours"}
_CHART_HEIGHT = 4
_CHART_BLOCKS = [" ", " ", "▂", "▃", "▄", "▅", "▆", "▇", "█"]


class LogStatsScreen(OmegaScreen):
    """5.8 — KPI + histogramme horaire + top IPs/jails, periode 24h/7j/30j."""

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container
        self._aggregator = LogAggregator()
        self._period = "24h"

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="omega-panel"):
            yield Static("STATISTIQUES DES LOGS", classes="omega-title")
            yield Static("", id="stats-hint", classes="omega-hint")
            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button("24h", id="period-24h")
                with Container(classes="omega-btn-frame"):
                    yield Button("7 jours", id="period-7d")
                with Container(classes="omega-btn-frame"):
                    yield Button("30 jours", id="period-30d")
                with Container(classes="omega-btn-frame"):
                    yield Button("Rafraichir", id="refresh", variant="primary")

            with Horizontal(id="kpi-row"):
                yield Static(id="kpi-events", classes="omega-dash-box dash-box-short")
                yield Static(id="kpi-bans", classes="omega-dash-box dash-box-short")
                yield Static(id="kpi-top-jail", classes="omega-dash-box dash-box-short")
                yield Static(id="kpi-peak", classes="omega-dash-box dash-box-short")

            yield Static(id="box-chart", classes="omega-dash-box")

            with Horizontal(id="tables-row"):
                yield DataTable(id="top-ips-table")
                yield DataTable(id="top-jails-table")

            with Horizontal(classes="omega-actions"), Container(classes="omega-btn-frame"):
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
        if button_id == "period-24h":
            self._period = "24h"
        elif button_id == "period-7d":
            self._period = "7d"
        elif button_id == "period-30d":
            self._period = "30d"
        self._refresh()

    def _colors(self) -> dict[str, str]:
        v = self.app.get_css_variables()
        return {
            "main": v.get("foreground", ""),
            "danger": v.get("error", ""),
            "warning": v.get("warning", ""),
            "heading": f"bold {v.get('primary', '')}".strip(),
        }

    def _refresh(self) -> None:
        colors = self._colors()
        summary = self._aggregator.get_summary(period_code=self._period)

        self.query_one("#stats-hint", Static).update(
            f"Periode : {_PERIODS[self._period]}  │  Source : {summary.data_source}"
        )

        self.query_one("#kpi-events", Static).update(
            Text(f"Evenements\n\n{summary.total_events}\n", style=colors["heading"])
            + Text(f"Logs scannes ({summary.data_source})", style="dim")
        )
        self.query_one("#kpi-bans", Static).update(
            Text(f"Total Bans\n\n{summary.total_bans}", style=colors["heading"])
        )
        self.query_one("#kpi-top-jail", Static).update(
            Text(f"Top Jail\n\n{summary.top_jail_name}", style=colors["heading"])
        )
        self.query_one("#kpi-peak", Static).update(
            Text(f"Heure de Pointe\n\n{summary.peak_hour}\n", style=colors["heading"])
            + Text(f"Pic ({summary.peak_count} evts)", style="dim")
        )

        self.query_one("#box-chart", Static).update(self._render_chart(colors, summary.hourly_series))

        ips_table = self.query_one("#top-ips-table", DataTable)
        ips_table.clear()
        for i, ip_stat in enumerate(summary.top_ips[:8], 1):
            ips_table.add_row(str(i), ip_stat.ip, str(ip_stat.total_bans), ip_stat.last_ban.strftime("%H:%M:%S"))

        jails_table = self.query_one("#top-jails-table", DataTable)
        jails_table.clear()
        for jail in summary.top_jails[:8]:
            status = Text("● Actif", style=colors["main"]) if jail.is_active else Text("○ Archive", style="dim")
            bar_filled = int(jail.percentage / 10)
            part = f"{'█' * bar_filled}{'░' * (10 - bar_filled)} {jail.percentage}%"
            jails_table.add_row(jail.name, status, str(jail.total_bans), part)

    def _render_chart(self, colors: dict, data: list[int]) -> Text:
        max_val = max(data) if max(data) > 0 else 1

        box = self.query_one("#box-chart", Static)
        available_width = max(48, box.size.width - 4 or 70)
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
