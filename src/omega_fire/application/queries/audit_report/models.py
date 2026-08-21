# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Audit report data models.

Defines the DTOs used to assemble and transport the audit report data
(menu 6.3) between the collection modules and the exporters. Pure data
structures — no I/O, no business logic.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class CapabilitiesSection:
    """Section 2: current status of all known capabilities."""
    capabilities: list[dict[str, Any]] = field(default_factory=list)
    total_available: int = 0
    total_missing: int = 0
    total_degraded: int = 0
    total_disqualified: int = 0


@dataclass
class RulesInventory:
    """Section 3: current total rule count (snapshot, not a period)."""
    total_count: int = 0
    enabled_count: int = 0


@dataclass
class BanActivity:
    """Section 4: ban/unban action counts (no per-backend breakdown —
    the current audit log does not capture which backend was targeted,
    only that the action ran and succeeded/failed)."""
    banned_count: int = 0
    unbanned_count: int = 0


@dataclass
class SyncInfo:
    """Section 5: last synchronization event.

    ips_realigned is not available — the current audit log only
    records that the sync action ran, not the count it processed.
    """
    last_sync_at: Optional[str] = None
    found: bool = False


@dataclass
class IpInventoryByBackend:
    """Section 6: current active IP count for a single backend."""
    backend: str
    active_count: int = 0


@dataclass
class JournalSummary:
    """Section 7: top application journal events since the last audit."""
    top_events: list[tuple[str, int]] = field(default_factory=list)
    error_count: int = 0
    other_count: int = 0


@dataclass
class Anomaly:
    """Section 8: a single (possibly aggregated) detected anomaly."""
    category: str
    description: str
    severity: str = "warning"
    count: int = 1


@dataclass
class AppHealth:
    """Section 11: application health snapshot."""
    version: str = "N/A"
    last_backup_info: str = "N/A — non configuré"
    config_integrity: str = "N/A"


@dataclass
class DiskUsage:
    """Section 12: disk usage of var/ subdirectories."""
    backups_size_mb: float = 0.0
    backups_count: int = 0
    db_size_mb: float = 0.0
    logs_size_mb: float = 0.0
    free_space_gb: float = 0.0
    warning: Optional[str] = None


@dataclass
class Fail2banSummary:
    """Section 13: minimal fail2ban overview (detail is in menu 6.4)."""
    total_jails: int = 0
    total_currently_banned: int = 0  # somme de currently_banned sur toutes les jails


@dataclass
class DatabaseIntegrity:
    """Section 14: SQLite integrity check."""
    integrity_ok: bool = True
    integrity_details: str = "ok"
    db_size_mb: float = 0.0
    schema_version: str = "N/A"


@dataclass
class AuditReportData:
    """Complete audit report (menu 6.3): all sections assembled."""
    generated_at: datetime
    period_since: Optional[str]  # None si tout premier audit (aucune période)

    capabilities: CapabilitiesSection
    rules_inventory: RulesInventory
    ip_internal_duplicate_count: int  # même IP plusieurs fois dans UN backend
    ip_cross_backend_count: int       # même IP présente dans PLUSIEURS backends
    sync_info: SyncInfo
    ip_inventory: list[IpInventoryByBackend]
    journal_summary: JournalSummary
    anomalies: list[Anomaly]
    app_health: AppHealth
    disk_usage: DiskUsage
    fail2ban_summary: Fail2banSummary
    db_integrity: DatabaseIntegrity

    executive_summary: str = ""


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - DTOs purs pour le rapport d'audit complet (menu 6.3). Chaque
#   dataclass correspond à une section du rapport final. Aucune
#   logique, aucun I/O — juste la forme des données.
#
# Pourquoi dans application/queries/ (charte) :
# - Ce sont des DTOs de query (lecture), pas des commands.
# - Consommés par les modules de collecte (capabilities_section.py,
#   activity_section.py, etc.) et par les exporters (TXT/HTML).
#
# Comment il sera utilisé :
# - report_builder.py assemble un AuditReportData complet à partir des
#   modules de collecte.
# - application/commands/export_audit_report.py passe cet objet aux
#   exporters pour générer le fichier final.
#----------------------------------------------------------------------
