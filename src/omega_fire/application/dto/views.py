# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""View DTOs for the application layer.

These dataclasses represent read-only projections of domain data,
formatted for display by the interface layer. They are NOT domain
models — they are shaped for rendering.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(slots=True)
class CapabilityView:
    """Read-only view of a single capability for display."""
    capability_id: str
    status: str
    category: str = ""
    reason: str = ""
    version: str = ""
    symbol: str = ""

    def to_line(self) -> str:
        return f"{self.symbol} {self.capability_id.upper():<20} : {self.status}"


@dataclass(slots=True)
class CapabilityRegistryView:
    """Read-only view of the full capability registry for display."""
    capabilities: list[CapabilityView] = field(default_factory=list)
    total: int = 0
    available: int = 0
    degraded: int = 0
    missing: int = 0
    disqualified: int = 0

    def summary_line(self) -> str:
        return (
            f"Total: {self.total} | "
            f"Disponible: {self.available} | "
            f"Dégradé: {self.degraded} | "
            f"Manquant: {self.missing} | "
            f"Disqualifié: {self.disqualified}"
        )


@dataclass(slots=True)
class BannedIPView:
    """Read-only view of a single banned IP for display."""
    ip: str
    backend: str
    status: str
    source: str = ""
    comment: str = ""
    banned_at: str = ""
    expires_at: str = ""


@dataclass(slots=True)
class BannedIPListView:
    """Read-only view of all banned IPs for display."""
    entries: list[BannedIPView] = field(default_factory=list)
    total: int = 0
    backends_queried: list[str] = field(default_factory=list)
    filter_applied: str = ""


@dataclass(slots=True)
class RuleView:
    """Read-only view of a single firewall rule for display."""
    rule_id: str
    backend: str
    chain: str = ""
    protocol: str = ""
    port: str = ""
    source: str = ""
    destination: str = ""
    action: str = ""
    comment: str = ""
    packet_count: int = 0
    byte_count: int = 0


@dataclass(slots=True)
class RuleListView:
    """Read-only view of all firewall rules for display."""
    rules: list[RuleView] = field(default_factory=list)
    total: int = 0
    backend: str = ""


@dataclass(slots=True)
class JailView:
    """Read-only view of a single fail2ban jail for display."""
    jail_name: str
    status: str = "unknown"
    banned_count: int = 0
    total_bans: int = 0
    filter_name: str = ""
    log_path: str = ""


@dataclass(slots=True)
class JailListView:
    """Read-only view of all fail2ban jails for display."""
    jails: list[JailView] = field(default_factory=list)
    total: int = 0
    active: int = 0
    inactive: int = 0


@dataclass(slots=True)
class ConntrackView:
    """Read-only view of conntrack status for display."""
    total_entries: int = 0
    established: int = 0
    time_wait: int = 0
    syn_sent: int = 0
    syn_recv: int = 0
    max_entries: int = 0
    usage_percent: float = 0.0


@dataclass(slots=True)
class DashboardView:
    """Read-only view of the monitoring dashboard for display."""
    active_connections: int = 0
    banned_ips_total: int = 0
    rules_total: int = 0
    jails_active: int = 0
    uptime_seconds: float = 0.0
    last_scan: str = ""
    degraded_capabilities: list[str] = field(default_factory=list)


@dataclass(slots=True)
class LogTopIPView:
    """Read-only view of top IPs from log analysis."""
    ip: str
    count: int = 0
    last_seen: str = ""
    is_banned: bool = False


@dataclass(slots=True)
class LogTopIPListView:
    """Read-only view of top IPs list for display."""
    entries: list[LogTopIPView] = field(default_factory=list)
    period: str = ""
    log_source: str = ""
    total_lines_analyzed: int = 0

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - DTOs de vue (read-only) pour l'affichage par interfaces/
# - Projections formatées des données domaine, pas les modèles eux-mêmes
# - Chaque vue est immutable par convention (slots=True)
#
# Pourquoi dans application/dto/ (charte) :
# - Objets de transfert entre application/ et interfaces/
# - Formatés pour le rendu, pas pour la logique métier
# - Pas de comportement, uniquement des données
#
# Ce qu'il ne contient PAS :
# ❌ Pas d'import depuis infrastructure/
# ❌ Pas d'import depuis interfaces/
# ❌ Pas de Rich, subprocess, sqlite3
# ❌ Pas de logique métier (c'est dans domain/)
#
# Points clés :
# - CapabilityView / CapabilityRegistryView : affichage capacités (Section 1)
# - BannedIPView / BannedIPListView : affichage IPs bannies (Section 2)
# - RuleView / RuleListView : affichage règles (Section 3)
# - JailView / JailListView : affichage jails (Section 4)
# - ConntrackView : affichage conntrack (Section 8)
# - DashboardView : affichage dashboard (Section 8)
# - LogTopIPView / LogTopIPListView : affichage top IPs (Section 5)
# - to_line() / summary_line() : helpers de formatage texte
#---------------------------------------------------------------------->
