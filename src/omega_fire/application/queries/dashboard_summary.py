# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Dashboard summary query.

Provides read-only access to the monitoring dashboard data.
Used by Section 8.1 of the menu.
"""
from __future__ import annotations

from omega_fire.core.capability_registry import CapabilityRegistry
from omega_fire.core.enums import CapabilityStatus
from omega_fire.application.dto.views import DashboardView


def get_dashboard_summary(registry: CapabilityRegistry) -> str:
    """8.1: Get monitoring dashboard summary.

    Args:
        registry: The capability registry

    Returns:
        Formatted string with dashboard summary
    """
    view = build_dashboard_view(registry)

    lines = [
        "═══ TABLEAU DE BORD ═══",
        "",
        f"  Connexions actives   : {view.active_connections}",
        f"  IPs bannies (total)  : {view.banned_ips_total}",
        f"  Règles actives       : {view.rules_total}",
        f"  Jails actifs         : {view.jails_active}",
        f"  Uptime               : {view.uptime_seconds:.0f}s",
        f"  Dernier scan         : {view.last_scan or 'N/A'}",
        "",
    ]

    if view.degraded_capabilities:
        lines.append("  ⚠️ Capacités dégradées :")
        for cap in view.degraded_capabilities:
            lines.append(f"     • {cap}")
    else:
        lines.append("   Toutes les capacités sont opérationnelles")

    lines.append("")
    lines.append("⚠️ Données réelles à connecter via infrastructure adapters")

    return "\n".join(lines)


def build_dashboard_view(registry: CapabilityRegistry) -> DashboardView:
    """Build a DashboardView from the current registry state.

    Args:
        registry: The capability registry

    Returns:
        DashboardView with current data
    """
    degraded = [
        cap.id for cap in registry.list_all()
        if cap.status == CapabilityStatus.DEGRADED
    ]

    # In real implementation, counts would come from infrastructure adapters
    return DashboardView(
        active_connections=0,
        banned_ips_total=0,
        rules_total=0,
        jails_active=0,
        uptime_seconds=0.0,
        last_scan="",
        degraded_capabilities=degraded,
    )

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Query read-only pour le dashboard monitoring (Section 8.1)
# - Agrège les données de plusieurs sous-systèmes
# - Retourne une vue consolidée pour l'affichage
#
# Pourquoi dans application/queries/ (charte) :
# - Lecture seule, pas de modification
# - Dépend de core/capability_registry.py
# - Dépend de application/dto/views.py pour DashboardView
# - Ne dépend pas de infrastructure/ (pas d'appel système)
#
# Ce qu'il ne contient PAS :
# ❌ Pas d'import depuis infrastructure/
# ❌ Pas d'import depuis interfaces/
# ❌ Pas de subprocess, rich
#
# Points clés :
# - get_dashboard_summary() : retourne string formatée pour l'UI
# - build_dashboard_view() : construit le DashboardView structuré
# - Liste les capacités dégradées depuis le registry
# - Les compteurs réels viendront des infrastructure adapters
#---------------------------------------------------------------------->
