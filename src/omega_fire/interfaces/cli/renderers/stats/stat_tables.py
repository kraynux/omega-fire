# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.style import Style

from omega_fire.core.stats.models import LogStatsSummary
from omega_fire.interfaces.cli.themes.registry import theme_registry


def _get_theme_style(style_key: str) -> Style:
    """Helper classique Omega-Fire pour obtenir un style du thème de manière sécurisée."""
    try:
        style = theme_registry.get_style(style_key)
        if isinstance(style, Style):
            return style
        if isinstance(style, str):
            return Style.parse(style)
    except Exception:
        pass
    return Style.null()


def render_stat_tables(summary: LogStatsSummary) -> Layout:
    """Rendu des tables Top IP et Activité par Jail avec les styles du thème actif."""
    layout = Layout(name="tables_container")

    # Style des en-têtes (clé officielle Omega-Fire)
    style_heading = _get_theme_style("text.heading")

    # --- Table 1 : Top IPs ---
    ip_table = Table(box=None, expand=True, padding=(0, 1), header_style=style_heading)
    ip_table.add_column("#", style=_get_theme_style("text.muted"), justify="right", width=3)
    ip_table.add_column("Adresse IP", style=_get_theme_style("text.main"))
    ip_table.add_column("Bans", style=_get_theme_style("text.danger"), justify="right")
    ip_table.add_column("Dernier Ban", style=_get_theme_style("text.muted"), justify="right")

    if not summary.top_ips:
        ip_table.add_row("-", "Aucune donnée", "0", "--:--")
    else:
        for idx, ip_stat in enumerate(summary.top_ips[:8], 1):
            last_ban_str = ip_stat.last_ban.strftime("%H:%M:%S")
            ip_table.add_row(
                str(idx),
                ip_stat.ip,
                str(ip_stat.total_bans),
                last_ban_str,
            )

    ip_panel = Panel(
        ip_table,
        title=Text("Top Adresses IP Ciblées", style=style_heading),
        title_align="left",
        border_style=_get_theme_style("border.default"),
        expand=True,
    )

    # --- Table 2 : Répartition par Jail ---
    jail_table = Table(box=None, expand=True, padding=(0, 1), header_style=style_heading)
    jail_table.add_column("Jail / Service", style=_get_theme_style("text.main"))
    jail_table.add_column("Statut", justify="center", width=10)
    jail_table.add_column("Bans", style=_get_theme_style("text.warning"), justify="right")
    jail_table.add_column("Part", justify="left")

    if not summary.top_jails:
        jail_table.add_row("Aucune donnée", "-", "0", "")
    else:
        for jail in summary.top_jails[:8]:
            if jail.is_active:
                status_text = Text("● Actif", style=_get_theme_style("status.available"))
            else:
                status_text = Text("○ Archivé", style=_get_theme_style("text.muted"))

            bar_len = int(jail.percentage / 10)
            bar = Text()
            bar.append("█" * bar_len, style=_get_theme_style("text.main"))
            bar.append("░" * (10 - bar_len), style=_get_theme_style("text.muted"))
            bar.append(f" {jail.percentage}%", style=_get_theme_style("text.muted"))

            jail_table.add_row(
                jail.name,
                status_text,
                str(jail.total_bans),
                bar,
            )

    jail_panel = Panel(
        jail_table,
        title=Text("Activité par Service (Jail)", style=style_heading),
        title_align="left",
        border_style=_get_theme_style("border.default"),
        expand=True,
    )

    layout.split_row(
        Layout(ip_panel, name="left_ip_table"),
        Layout(jail_panel, name="right_jail_table"),
    )

    return layout
