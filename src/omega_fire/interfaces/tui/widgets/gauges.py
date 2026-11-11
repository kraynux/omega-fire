# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
# Porte d'omega-log (interfaces/tui/widgets/gauges.py) le 2026-11-09 (OMEGA-FIRE_PLAN_LOGS_NIVEAU_SERV_LOG.md) : garder identique a la source.
"""Jauges horizontales en texte pour les ecrans de statistiques (2026-11-06) : une barre pleine
proportionnelle a la valeur sur une piste grisee, meme lecture que les barres du rapport HTML."""
from __future__ import annotations

from rich.cells import cell_len, set_cell_size
from rich.text import Text

FULL = "█"
EMPTY = "░"


def gauge(value: float, maximum: float, width: int) -> tuple[str, str]:
    """(partie pleine, partie vide). Une valeur non nulle garde toujours au moins un bloc."""
    if maximum <= 0 or value <= 0:
        return "", EMPTY * width
    filled = max(1, round(value / maximum * width))
    filled = min(width, filled)
    return FULL * filled, EMPTY * (width - filled)


def fit(label: str, width: int) -> str:
    """Libelle ajuste a `width` cellules (coupe avec « … », complete d'espaces)."""
    shown = label if cell_len(label) <= width else set_cell_size(label, width - 1) + "…"
    return shown + " " * (width - cell_len(shown))


def append_gauge_line(
    content: Text, label: str, value: int, maximum: int, *, label_width: int, bar_width: int,
    style: str, suffix: str = "",
) -> None:
    filled, empty = gauge(value, maximum, bar_width)
    content.append(" " + fit(label, label_width) + " ")
    content.append(filled, style=style)
    content.append(empty, style="dim")
    content.append(f" {value:>7}", style="bold")
    content.append(f"{suffix}\n")
