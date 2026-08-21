# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Management activity panel renderer for Omega-Fire stats reports
(menus 8.3/8.4).

Renders a summary of administrative actions taken during the report
period, sourced from audit.log (AuditEntry) — distinct from the ban/jail
activity already covered by LogAggregator's KPI cards and charts. This
panel answers "what did the operator do" rather than "what did the
firewall block".

This module performs no calculation — it receives already-aggregated
counters and a short list of recent entries, both computed upstream.
"""
from rich.panel import Panel
from rich.text import Text

from omega_fire.interfaces.cli.themes.registry import theme_registry


def render_management_panel(
    rule_changes: int,
    backups: int,
    restores: int,
    total_actions: int,
    success_rate: float,
    recent_entries: list[tuple[str, str, bool]],
    title: str = "Gestion & Administration",
) -> Panel:
    """Render the management/administration activity panel.

    Args:
        rule_changes: Count of profile changes / manual rule create-
            delete events over the period.
        backups: Count of backups created (menu 7.1) over the period.
        restores: Count of state restorations (menu 7.2) over the
            period.
        total_actions: Total number of audited actions over the
            period (any type), for the success rate denominator.
        success_rate: Percentage (0.0-100.0) of successful actions
            over the period.
        recent_entries: Up to a handful of (time_label, description,
            success) tuples, most recent first, already selected and
            formatted by the caller.
        title: Panel title.

    Returns:
        A Rich Panel containing the rendered summary.
    """
    style_main = theme_registry.get_style("text.main")
    style_muted = theme_registry.get_style("text.muted")
    style_heading = theme_registry.get_style("text.heading")
    style_success = theme_registry.get_style("status.available")
    style_danger = theme_registry.get_style("text.danger")
    style_warning = theme_registry.get_style("text.warning")
    border_style = theme_registry.get_style("border.default")

    content = Text()

    content.append("── ACTIVITÉ ─────────────────\n", style=style_heading)
    content.append(f"  Changements de profil / règles : {rule_changes}\n", style=style_main)
    content.append(f"  Sauvegardes effectuées         : {backups}\n", style=style_main)
    content.append(f"  Restaurations effectuées       : {restores}\n", style=style_main)

    content.append("\n── FIABILITÉ ────────────────\n", style=style_heading)
    rate_style = style_success if success_rate >= 95 else (style_warning if success_rate >= 80 else style_danger)
    content.append(f"  Taux de succès : ", style=style_main)
    content.append(f"{success_rate:.1f}%", style=rate_style)
    content.append(f"  ({total_actions} action(s) au total)\n", style=style_muted)

    if recent_entries:
        content.append("\n── DERNIÈRES ACTIONS ────────\n", style=style_heading)
        for time_label, description, success in recent_entries:
            status_symbol = "✔" if success else "✗"
            status_style = style_success if success else style_danger
            content.append(f"  [{time_label}] ", style=style_muted)
            content.append(f"{status_symbol} ", style=status_style)
            content.append(f"{description}\n", style=style_main)
    else:
        content.append("\n  Aucune action enregistrée sur cette période.\n", style=style_muted)

    return Panel(
        content,
        title=title,
        title_align="left",
        border_style=border_style,
        expand=True,
    )


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Rendu du panneau d'activité administrative (8.3/8.4) — répond à
#   "qu'a fait l'opérateur" (changements de profil, backups,
#   restaurations, taux de succès), distinct de l'activité de ban/jail
#   déjà couverte par les KPI cards et graphiques issus de LogAggregator.
#
# Pourquoi dans interfaces/cli/renderers/stats/ (charte) :
# - Rendu pur, aucun calcul — reçoit des compteurs déjà agrégés depuis
#   audit.log (via AuditLogger.get_all_since(), filtré et compté en
#   amont dans application/queries/build_stats_report.py, étape 6).
# - Utilise uniquement theme_registry, aucune couleur codée en dur.
#
# Ce qu'il ne contient PAS :
# ❌ Pas de lecture d'audit.log (délégué à l'orchestration en amont)
# ❌ Pas de filtrage par type d'événement (délégué en amont)
# ❌ Pas de dépendance vers domain/, application/, ou infrastructure/
#
# Points clés :
# - render_management_panel() : compteurs simples + liste courte
#   d'événements récents (time_label, description, success)
# - Taux de succès coloré selon seuil (≥95% succès, ≥80% avertissement,
#   sinon danger) — mêmes seuils que le pattern déjà établi ailleurs
#   dans le projet (ex. render_logs_live.py::_render_stats_panel)
# - Style "carnet de bord" avec icônes ✔/✗, distinct des barres
#   proportionnelles déjà utilisées par stat_tables.py et
#   daily_trend_chart.py dans le même rapport
#
# Comment il sera utilisé (aperçu) :
# - domain/reports/service.py::build_stats_report() (étape 5) construira
#   la section "Gestion" à partir des mêmes données agrégées
# - interfaces/cli/actions.py (8.3/8.4) appellera ce renderer directement
#   pour l'affichage CLI
#---------------------------------------------------------------------->
