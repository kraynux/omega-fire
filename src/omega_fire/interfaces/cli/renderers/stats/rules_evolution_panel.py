# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Rules/bans evolution panel renderer for Omega-Fire stats reports
(menus 8.3/8.4).

Renders the evolution of active rules count and banned IPs count across
the report period, sourced from snapshot history (menus 7.1/7.2/3.4) —
distinct from the continuous ban activity already covered by
LogAggregator (fail2ban-sourced). Snapshots are POINT-IN-TIME captures,
not a continuous measurement, so this panel is always explicit about how
many data points actually exist over the period.

This module performs no calculation — it receives already-filtered
(date_label, rules_count, ips_count) points, chronologically sorted,
computed upstream from list_snapshots().
"""
from rich.panel import Panel
from rich.text import Text

from omega_fire.interfaces.cli.themes.registry import theme_registry


_SPARK_CHARS = "▁▂▃▄▅▆▇█"


def _build_sparkline(values: list[int]) -> str:
    """Build a compact sparkline string from a list of integer values."""
    if not values:
        return ""
    max_val = max(values) if max(values) > 0 else 1
    chars = []
    for v in values:
        ratio = v / max_val
        idx = int(ratio * (len(_SPARK_CHARS) - 1))
        idx = min(idx, len(_SPARK_CHARS) - 1)
        chars.append(_SPARK_CHARS[idx])
    return "".join(chars)


def render_rules_evolution_panel(
    points: list[tuple[str, int, int]],
    title: str = "Évolution des Règles & IPs Bannies",
) -> Panel:
    """Render the rules/bans evolution panel from snapshot history.

    Args:
        points: Ordered list of (date_label, rules_count, ips_count)
            tuples, one per available snapshot in the report period,
            already chronologically sorted by the caller.
        title: Panel title.

    Returns:
        A Rich Panel containing the rendered summary.
    """
    style_main = theme_registry.get_style("text.main")
    style_muted = theme_registry.get_style("text.muted")
    style_heading = theme_registry.get_style("text.heading")
    style_info = theme_registry.get_style("text.info")
    style_danger = theme_registry.get_style("text.danger")
    border_style = theme_registry.get_style("border.default")

    content = Text()

    if not points:
        content.append(
            "Aucun snapshot disponible sur cette période — impossible de "
            "mesurer l'évolution des règles/IPs bannies. Voir menu 7.1.\n",
            style=style_muted,
        )
        return Panel(content, title=title, title_align="left", border_style=border_style, expand=True)

    rules_values = [r for _, r, _ in points]
    ips_values = [i for _, _, i in points]

    content.append(
        f"{len(points)} point(s) de mesure sur la période.\n"
        f"Reflète les sauvegardes disponibles, pas un suivi continu.\n\n",
        style=style_muted,
    )

    content.append("  Règles actives : ", style=style_main)
    content.append(_build_sparkline(rules_values), style=style_info)
    content.append(f"   ({rules_values[0]} → {rules_values[-1]})\n", style=style_muted)

    content.append("  IPs bannies    : ", style=style_main)
    content.append(_build_sparkline(ips_values), style=style_danger)
    content.append(f"   ({ips_values[0]} → {ips_values[-1]})\n\n", style=style_muted)

    content.append("── DÉTAIL DES POINTS ────────\n", style=style_heading)
    for date_label, rules_count, ips_count in points:
        content.append(f"  {date_label:<14} ", style=style_muted)
        content.append(f"Règles: {rules_count:<4} ", style=style_info)
        content.append(f"IPs: {ips_count}\n", style=style_danger)

    return Panel(
        content,
        title=title,
        title_align="left",
        border_style=border_style,
        expand=True,
    )


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Rendu de l'évolution du nombre de règles actives et d'IPs bannies
#   sur la période, à partir de l'historique des snapshots (7.1/7.2/3.4)
#   — distinct de l'activité de ban continue déjà couverte par
#   LogAggregator (source fail2ban).
#
# Pourquoi dans interfaces/cli/renderers/stats/ (charte) :
# - Rendu pur, aucun calcul — reçoit des points déjà filtrés/triés
#   depuis list_snapshots() (agrégés en amont dans
#   application/queries/build_stats_report.py, étape 6).
# - Utilise uniquement theme_registry, aucune couleur codée en dur.
#
# Ce qu'il ne contient PAS :
# ❌ Pas d'appel à list_snapshots() ni à PersistencePort
# ❌ Pas de filtrage par date (délégué en amont)
# ❌ Pas de dépendance vers domain/, application/, ou infrastructure/
#
# Points clés :
# - render_rules_evolution_panel() : liste de points (date, règles, IPs)
# - _build_sparkline() : compacte une série de valeurs en une ligne
#   Unicode (▁▂▃▄▅▆▇█) — distinct des barres horizontales
#   (daily_trend_chart.py) et verticales (ascii_charts.py) déjà
#   utilisées ailleurs dans le même rapport
# - Avertissement explicite sur la nature ponctuelle des snapshots —
#   jamais laisser croire à un suivi continu que la source ne permet pas
# - Détail ligne par ligne de chaque point, en complément de la
#   sparkline compacte
#
# Comment il sera utilisé (aperçu) :
# - domain/reports/service.py::build_stats_report() (étape 5) construira
#   la section "Évolution des Règles" à partir des mêmes données
# - interfaces/cli/actions.py (8.3/8.4) appellera ce renderer directement
#   pour l'affichage CLI
#---------------------------------------------------------------------->
