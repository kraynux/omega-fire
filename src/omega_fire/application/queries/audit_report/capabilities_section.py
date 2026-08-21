# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Capabilities and fail2ban summary collection (sections 2 & 13).

Pure collection functions: read from the capability registry and the
fail2ban adapter, return DTOs. No file I/O, no export logic.
"""
from __future__ import annotations

from typing import Any, Optional

from omega_fire.core.enums import CapabilityStatus
from omega_fire.application.queries.audit_report.models import (
    CapabilitiesSection,
    Fail2banSummary,
)


def collect_capabilities_section(registry: Any) -> CapabilitiesSection:
    """Collect the current status of all known capabilities (section 2).

    Args:
        registry: CapabilityRegistry instance.

    Returns:
        CapabilitiesSection with the full list and counts by status.
    """
    if registry is None:
        return CapabilitiesSection()

    capabilities = registry.list_all()

    entries = [
        {
            "id": cap.id,
            "status": cap.status.name,
            "reason": getattr(cap, "reason", ""),
            "category": getattr(cap, "category", ""),
        }
        for cap in capabilities
    ]

    return CapabilitiesSection(
        capabilities=entries,
        total_available=registry.count_by_status(CapabilityStatus.AVAILABLE),
        total_missing=registry.count_by_status(CapabilityStatus.MISSING),
        total_degraded=registry.count_by_status(CapabilityStatus.DEGRADED),
        total_disqualified=registry.count_by_status(CapabilityStatus.DISQUALIFIED),
    )


def collect_fail2ban_summary(fail2ban_adapter: Optional[Any]) -> Fail2banSummary:
    """Collect a minimal fail2ban overview (section 13).

    Detailed statistics belong to menu 6.4 — this section only gives a
    quick headcount, not a per-jail breakdown.

    Args:
        fail2ban_adapter: Fail2banAdapter instance, or None if fail2ban
            is unavailable.

    Returns:
        Fail2banSummary with total jail count and total currently
        banned IPs across all jails.
    """
    if fail2ban_adapter is None:
        return Fail2banSummary()

    try:
        jail_names = fail2ban_adapter.list_jails()
    except Exception:
        return Fail2banSummary()

    total_banned = 0
    for jail_name in jail_names:
        try:
            status = fail2ban_adapter.get_jail_status(jail_name)
            total_banned += status.get("currently_banned", 0)
        except Exception:
            continue

    return Fail2banSummary(
        total_jails=len(jail_names),
        total_currently_banned=total_banned,
    )


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Collecte les données pour les sections 2 (capacités) et 13
#   (résumé fail2ban) du rapport d'audit (menu 6.3).
#
# Pourquoi dans application/queries/ (charte) :
# - Lecture seule, aucune modification d'état.
# - Consomme capability_registry et fail2ban_adapter déjà résolus par
#   l'appelant (jamais d'import direct depuis infrastructure/backends/).
#
# Ce qu'il ne contient PAS :
# ❌ Pas d'écriture de fichier (délégué aux exporters).
# ❌ Pas de détail par jail (c'est le rôle de menu 6.4).
#
# Points clés :
# - collect_capabilities_section() : liste complète + compteurs par
#   statut, réutilise capability_registry.count_by_status() existant.
# - collect_fail2ban_summary() : total_jails + total_currently_banned
#   uniquement — list_jails() ne distingue pas actif/inactif (toute
#   jail retournée est de facto chargée dans le daemon), donc pas de
#   notion active/inactive ici (voir discussion de session).
#
# Comment il sera utilisé :
# - report_builder.py appelle ces deux fonctions pour peupler
#   AuditReportData.capabilities et .fail2ban_summary.
#----------------------------------------------------------------------
