# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Fail2ban report data models (menu 6.4).

Pure DTOs — no I/O, no business logic. Complement the minimal fail2ban
summary already present in the audit report (menu 6.3) with full
per-jail detail.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class SystemStatus:
    """Fail2ban system-level status: installed, running, enabled at boot."""
    installed: bool = False
    service_running: bool = False
    enabled_at_boot: Optional[bool] = None  # None = impossible à déterminer


@dataclass
class RecentBan:
    """A single ban entry from fail2ban's own history (bips table)."""
    ip: str
    timeofban: datetime
    bantime: int
    bancount: int


@dataclass
class JailDetail:
    """Full detail for a single jail."""
    name: str
    currently_failed: int = 0
    total_failed: int = 0
    currently_banned: int = 0
    total_banned: int = 0
    maxretry: Optional[str] = None
    bantime: Optional[str] = None
    findtime: Optional[str] = None
    banned_ips: list[str] = field(default_factory=list)
    banned_ips_overflow: int = 0  # nombre d'IPs au-delà du plafond d'affichage
    recent_bans: list[RecentBan] = field(default_factory=list)
    history_available: bool = False


@dataclass
class DuplicateIp:
    """An IP present in more than one jail simultaneously."""
    ip: str
    jails: list[str]

    @property
    def jail_count(self) -> int:
        return len(self.jails)


@dataclass
class F2bReportData:
    """Complete fail2ban report (menu 6.4)."""
    generated_at: datetime
    system: SystemStatus
    total_jails: int
    jails: list[JailDetail]
    duplicate_ips: list[DuplicateIp]  # trié par jail_count décroissant, plafonné à 20


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - DTOs purs pour le rapport détaillé fail2ban (menu 6.4). Complète
#   le résumé minimal déjà présent dans le rapport d'audit (menu 6.3)
#   avec le détail complet par jail.
#
# Pourquoi dans application/queries/f2b_report/ (charte) :
# - DTOs de query, consommés par les modules de collecte et les
#   exporters (TXT/HTML).
#
# Points clés :
# - JailDetail.history_available : distingue "aucun ban récent" de
#   "base d'historique fail2ban indisponible" — évite d'afficher une
#   liste vide trompeuse si Fail2banHistoryReader échoue.
# - JailDetail.banned_ips_overflow : nombre d'IPs au-delà du plafond
#   d'affichage (décision de session : plafond fixe, ex. 20).
# - DuplicateIp : IP présente dans plusieurs jails à la fois (distinct
#   du plafond d'affichage — c'est une vraie donnée de recoupement).
#
# Comment il sera utilisé :
# - system_section.py, jails_section.py, duplicates_section.py
#   peuplent ces DTOs.
# - report_builder.py les assemble en F2bReportData.
#----------------------------------------------------------------------
