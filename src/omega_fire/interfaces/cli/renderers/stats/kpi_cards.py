# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text

from omega_fire.core.stats.models import LogStatsSummary
from omega_fire.interfaces.cli.themes.registry import theme_registry


def render_kpi_cards(summary: LogStatsSummary) -> Layout:
    """Rendu des 4 cartes KPI principales avec les styles du thème actif."""
    layout = Layout(name="kpi_container")

    border_style = theme_registry.get_style("border.default")
    style_main = theme_registry.get_style("text.main")
    style_muted = theme_registry.get_style("text.muted")
    style_danger = theme_registry.get_style("text.danger")
    style_warning = theme_registry.get_style("text.warning")
    style_info = theme_registry.get_style("text.info")

    t1 = Text()
    t1.append(f"{summary.total_events:,}\n", style=style_info)
    t1.append(f"Logs scannés ({summary.data_source})", style=style_muted)
    p1 = Panel(t1, title="Événements", title_align="left", border_style=border_style, expand=True)

    t2 = Text()
    t2.append(f"{summary.total_bans:,}\n", style=style_danger)
    t2.append("Adresses IP bloquées", style=style_muted)
    p2 = Panel(t2, title="Total Bans", title_align="left", border_style=border_style, expand=True)

    t3 = Text()
    t3.append(f"{summary.top_jail_name}\n", style=style_warning)
    t3.append("Service le plus ciblé", style=style_muted)
    p3 = Panel(t3, title="Top Jail", title_align="left", border_style=border_style, expand=True)

    t4 = Text()
    t4.append(f"{summary.peak_hour}\n", style=style_main)
    t4.append(f"Pic ({summary.peak_count} évts)", style=style_muted)
    p4 = Panel(t4, title="Heure de Pointe", title_align="left", border_style=border_style, expand=True)

    layout.split_row(
        Layout(p1, name="kpi_events"),
        Layout(p2, name="kpi_bans"),
        Layout(p3, name="kpi_jail"),
        Layout(p4, name="kpi_peak"),
    )

    return layout
