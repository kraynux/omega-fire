# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Daily trend chart renderer for Omega-Fire stats reports (menus 8.3/8.4).

Renders a day-by-day (or week-by-week for 30-day reports) horizontal bar
chart, distinct in shape from ascii_charts.py::render_hourly_chart()
(vertical 24-column bars) — this one uses horizontal bars, better suited
to a smaller number of data points (7 days, or ~4-5 weekly buckets).

This module performs no calculation — it receives already-aggregated
(label, count) pairs and only renders them.
"""
from rich.panel import Panel
from rich.text import Text

from omega_fire.interfaces.cli.themes.registry import theme_registry


def render_daily_trend_chart(
    data: list[tuple[str, int]],
    title: str = "Tendance Journalière",
) -> Panel:
    """Render a horizontal bar chart from (label, count) pairs.

    Args:
        data: Ordered list of (day_or_week_label, count) tuples,
            already chronologically sorted by the caller.
        title: Panel title, overridable for the weekly-bucket variant
            used by the 30-day report.

    Returns:
        A Rich Panel containing the rendered chart.
    """
    style_main = theme_registry.get_style("text.main")
    style_muted = theme_registry.get_style("text.muted")
    style_danger = theme_registry.get_style("text.danger")
    style_success = theme_registry.get_style("status.available")
    border_style = theme_registry.get_style("border.default")

    if not data:
        return Panel(
            Text("Aucune donnée disponible pour cette période.", style=style_muted),
            title=title,
            title_align="left",
            border_style=border_style,
            expand=True,
        )

    values = [count for _, count in data]
    max_val = max(values) if max(values) > 0 else 1
    label_width = max(len(label) for label, _ in data)
    bar_max_width = 30

    content = Text()
    for label, count in data:
        bar_len = int((count / max_val) * bar_max_width) if max_val > 0 else 0
        bar_style = style_danger if count == max_val and count > 0 else style_main

        content.append(f"  {label:<{label_width}} ", style=style_muted)
        content.append("█" * bar_len, style=bar_style)
        content.append("░" * (bar_max_width - bar_len), style=style_muted)
        content.append(f"  {count}\n", style=style_main)

    # Indicateur de tendance global (premier vs dernier point), affiché
    # uniquement si au moins deux points existent — sinon un delta n'a
    # pas de sens.
    trend_suffix = ""
    if len(data) >= 2:
        first_val, last_val = data[0][1], data[-1][1]
        if last_val > first_val:
            trend_suffix = " ▲"
        elif last_val < first_val:
            trend_suffix = " ▼"
        else:
            trend_suffix = " ="

    display_title = f"{title}{trend_suffix}"

    return Panel(
        content,
        title=display_title,
        title_align="left",
        border_style=border_style,
        expand=True,
    )


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Rendu du graphique de tendance jour-par-jour (8.3) ou semaine-par-
#   semaine (8.4) — barres horizontales, distinct visuellement de
#   ascii_charts.py::render_hourly_chart() (barres verticales 24h).
#
# Pourquoi dans interfaces/cli/renderers/stats/ (charte) :
# - Rendu pur, aucun calcul — reçoit des paires (label, count) déjà
#   agrégées par LogAggregator (voir étape 4 du chantier 8.3/8.4).
# - Utilise uniquement theme_registry pour les styles, aucune couleur
#   codée en dur.
#
# Ce qu'il ne contient PAS :
# ❌ Pas de logique d'agrégation (regroupement par jour/semaine —
#    délégué à LogAggregator)
# ❌ Pas d'accès fichier/SQLite
# ❌ Pas de dépendance vers domain/, application/, ou infrastructure/
#
# Points clés :
# - render_daily_trend_chart(data, title) : data = liste de tuples
#   (label, count) déjà triée chronologiquement par l'appelant
# - Barres horizontales (contrairement aux barres verticales de
#   render_hourly_chart) — mieux adaptées à un petit nombre de points
# - Indicateur de tendance ▲/▼/= en titre, basé sur premier vs dernier
#   point (affiché seulement si ≥ 2 points)
# - title paramétrable : "Tendance Journalière" (8.3, 7 barres) vs un
#   titre "hebdomadaire" pour 8.4 (4-5 barres)
#
# Comment il sera utilisé (aperçu) :
# - domain/reports/service.py::build_stats_report() (étape 5) construira
#   la section correspondante à partir des mêmes données
# - interfaces/cli/actions.py (8.3/8.4) appellera ce renderer directement
#   pour l'affichage CLI (indépendamment du chemin d'export HTML)
#---------------------------------------------------------------------->
