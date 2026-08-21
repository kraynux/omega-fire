# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
from rich.panel import Panel
from rich.text import Text

from omega_fire.core.stats.models import LogStatsSummary
from omega_fire.interfaces.cli.themes.registry import theme_registry
from omega_fire.interfaces.cli.renderers.styles import get_terminal_width


def render_hourly_chart(summary: LogStatsSummary, height: int = 4) -> Panel:
    """Rendu de l'histogramme horaire adapté dynamiquement à la largeur du terminal."""
    data = summary.hourly_series
    blocks = [" ", " ", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
    max_val = max(data) if max(data) > 0 else 1

    style_main = theme_registry.get_style("text.main")
    style_danger = theme_registry.get_style("text.danger")
    style_muted = theme_registry.get_style("text.muted")
    border_style = theme_registry.get_style("border.default")

    # Calcul dynamique de la largeur disponible dans le panneau
    term_width = get_terminal_width()
    # Marge pour les bordures et les paddings (environ 6 caractères)
    available_width = max(48, term_width - 6)
    
    # Espace entre chaque bâton (24 heures = 23 intervalles)
    spacing_factor = max(1, (available_width - 24) // 23)
    gap = " " * spacing_factor

    lines = []
    for level in range(height, 0, -1):
        line_text = Text()
        for idx, val in enumerate(data):
            scaled = (val / max_val) * height
            if scaled >= level:
                char_style = style_danger if (val == max_val and val > 0) else style_main
                line_text.append("█", style=char_style)
            elif scaled > level - 1:
                b_idx = int((scaled - (level - 1)) * (len(blocks) - 1))
                line_text.append(blocks[b_idx], style=style_main)
            else:
                line_text.append(" ")
            
            if idx < len(data) - 1:
                line_text.append(gap)
        lines.append(line_text)

    # Alignement des étiquettes d'heures (00 à 23)
    hours_top = gap.join([f"{h:02d}"[0] + " " if spacing_factor > 1 else f"{h:02d}"[0] for h in range(24)])
    hours_bottom = gap.join([f"{h:02d}"[1] + " " if spacing_factor > 1 else f"{h:02d}"[1] for h in range(24)])
    
    chart_width = len(lines[0].plain) if lines else available_width
    separator = Text("─" * chart_width, style=border_style)

    chart_content = Text()
    for line in lines:
        chart_content.append_text(line)
        chart_content.append("\n")

    chart_content.append_text(separator)
    chart_content.append("\n")
    chart_content.append_text(Text(hours_top, style=style_muted))
    chart_content.append("\n")
    chart_content.append_text(Text(hours_bottom, style=style_muted))

    title_text = f"Distribution Horaire (24h) — Max: {max_val} bans/h"
    return Panel(
        chart_content,
        title=title_text,
        title_align="left",
        border_style=border_style,
        expand=True,
    )
