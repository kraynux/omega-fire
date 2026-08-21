# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Activity collection: rules, bans, sync, journal summary (sections 3, 4, 5, 7).

Pure collection functions: read from AuditLogger (JSON-lines audit
file), return DTOs. No file writing, no export logic.

IMPORTANT LIMITATION (documented, not a bug): the current audit log
only records the menu title as free text (e.g. "3.1 Créer une règle"),
not a structured command identifier. This module matches on known menu
title prefixes rather than a proper field — fragile if menu titles are
renamed, and unable to break down by backend or exact IP count (see
session notes / models.py docstrings for BanActivity and SyncInfo).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from omega_fire.application.queries.audit_report.models import (
    SyncInfo,
    JournalSummary,
)

# Préfixes de titres de menu connus, tels qu'utilisés par
# interfaces/cli/actions.py::_execute_action_flow(ctx, title, logic).
# Fragile par nature (dépend du texte des titres) — à remplacer si un
# jour le logging devient structuré (command_name distinct du titre UI).
_RULE_CREATE_PREFIX = "3.1"
_RULE_DELETE_PREFIX = "3.2"
_BAN_PREFIXES = ("2.1", "2.2")
_UNBAN_PREFIXES = ("2.3", "2.4")
_SYNC_PREFIX = "2.6"


def _matches_prefix(action: str, prefix: str) -> bool:
    """Check if an audit entry's action title starts with a known menu prefix."""
    return action.strip().startswith(prefix)




def collect_sync_info(audit_logger: Any) -> SyncInfo:
    """Find the most recent successful sync event (section 5).

    Searches the entire audit log (not limited to "since") — this
    section reports the last sync regardless of the report's period.

    Args:
        audit_logger: AuditLogger instance.

    Returns:
        SyncInfo with the last sync timestamp, or found=False if none.
    """
    entries = audit_logger.get_all_since(None)

    sync_entries = [
        e for e in entries
        if e.success and _matches_prefix(e.action, _SYNC_PREFIX)
    ]

    if not sync_entries:
        return SyncInfo(found=False)

    last_entry = max(sync_entries, key=lambda e: e.timestamp)
    return SyncInfo(
        last_sync_at=last_entry.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        found=True,
    )


def collect_journal_summary(audit_logger: Any, since: Optional[datetime]) -> JournalSummary:
    """Collect the top 10 most frequent journal events since a given date (section 7).

    Args:
        audit_logger: AuditLogger instance.
        since: only count entries at or after this date. None = all time.

    Returns:
        JournalSummary with top events, error count, and "other" count.
    """
    entries = audit_logger.get_all_since(since)

    counts: dict[str, int] = {}
    error_count = 0

    for e in entries:
        counts[e.action] = counts.get(e.action, 0) + 1
        if not e.success:
            error_count += 1

    sorted_events = sorted(counts.items(), key=lambda item: item[1], reverse=True)
    top_events = sorted_events[:10]
    other_count = sum(count for _, count in sorted_events[10:])

    return JournalSummary(
        top_events=top_events,
        error_count=error_count,
        other_count=other_count,
    )


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Collecte les données pour les sections 3 (règles), 4 (bans/débans),
#   5 (dernière sync), 7 (top événements journal) du rapport d'audit
#   (menu 6.3).
#
# Pourquoi dans application/queries/audit_report/ (charte) :
# - Lecture seule, aucune modification d'état.
# - Consomme AuditLogger déjà résolu par l'appelant (jamais d'import
#   direct depuis infrastructure/ au-delà du type reçu en paramètre).
#
# LIMITATION IMPORTANTE (documentée dans le docstring de module) :
# - Le matching se fait sur le TEXTE du titre de menu (ex: "3.1"), pas
#   sur un identifiant structuré. Fragile si les titres sont renommés
#   dans actions.py. Pas de détail par backend ni de compte exact
#   d'IPs (l'information n'existe pas dans le journal actuel).
#
# Points clés :
# - collect_rules_activity() : compte 3.1 (créées) / 3.2 (supprimées).
# - collect_ban_activity() : compte 2.1+2.2 (bans) / 2.3+2.4 (débans).
# - collect_sync_info() : dernière exécution réussie de 2.6, sur TOUT
#   le journal (pas limité à "since" — toujours le dernier connu).
# - collect_journal_summary() : top 10 actions les plus fréquentes +
#   compteur d'erreurs (success=False) + compteur "autres" (au-delà
#   du top 10).
#
# Comment il sera utilisé :
# - report_builder.py (application/queries/audit_report/report_builder.py)
#   appelle ces 4 fonctions pour peupler AuditReportData.
#----------------------------------------------------------------------
