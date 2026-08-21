# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Fail2ban jails detail collection (menu 6.4).

Combines jail descriptive config (Fail2banAdapter.list_jails_info(),
one bulk call for every jail — see perf note below) with per-jail live
failure counts (get_jail_status(), the one field that has no bulk
source) and recent ban history (Fail2banHistoryReader, reading
fail2ban's own SQLite database).

Perf note (2026-08-16) : cette fonction appelait auparavant, PAR JAIL,
get_jail_status() + 3x get_jail_config() (maxretry/bantime/findtime) —
4 x fail2ban-client (~400ms chacun, cf. adapter.py) x N jails. Avec 5
jails, ~8s rien que pour cette section, cause du "l'action met 10
secondes à se terminer" remonté par l'utilisateur alors qu'aucune
saisie n'était en cause (le prompt fonctionnait déjà correctement).
list_jails_info() (Phase 1B/scaling fix, déjà utilisée par 4.1/4.4/
4.6/4.7/4.8/4.9) fournit maxretry/bantime/findtime/banned_ips pour
TOUS les jails en un seul appel groupé (SQLite + lecture disque, zéro
fail2ban-client par jail dans le cas nominal) — seul get_jail_status()
reste par-jail, faute d'alternative : "currently failed"/"total
failed" ne sont exposés nulle part ailleurs (état vivant du
FailManager de fail2ban, jamais persisté).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from omega_fire.application.queries.f2b_report.models import JailDetail, RecentBan

MAX_DISPLAYED_BANNED_IPS = 20
MAX_RECENT_BANS = 10


def collect_jails_detail(
    fail2ban_adapter: Any,
    jails_info: list[Any],
    history_reader: Any,
) -> list[JailDetail]:
    """Collect full detail for every currently loaded jail.

    Args:
        fail2ban_adapter: Fail2banAdapter instance — still needed here
            for get_jail_status() (currently_failed/total_failed have
            no bulk source), but list_jails_info() is no longer called
            internally: the caller (report_builder.py) fetches it once
            and shares it with collect_duplicate_ips() too, instead of
            each collector re-fetching its own copy.
        jails_info: Pre-fetched list of JailInfo (ports/fail2ban.py),
            typically fail2ban_adapter.list_jails_info().
        history_reader: Fail2banHistoryReader instance
            (infrastructure/backends/fail2ban/history_reader.py).

    Returns:
        List of JailDetail, one per entry in jails_info. Empty list if
        fail2ban_adapter is None.
    """
    if fail2ban_adapter is None:
        return []

    history_available = history_reader is not None and history_reader.is_available()

    details: list[JailDetail] = []

    for info in jails_info:
        try:
            status = fail2ban_adapter.get_jail_status(info.name)
        except Exception:
            status = {}

        all_banned_ips = [str(ip) for ip in info.banned_ips]
        displayed_ips = all_banned_ips[:MAX_DISPLAYED_BANNED_IPS]
        overflow = max(0, len(all_banned_ips) - len(displayed_ips))

        recent_bans: list[RecentBan] = []
        if history_available:
            try:
                raw_bans = history_reader.get_recent_bans(info.name, limit=MAX_RECENT_BANS)
                recent_bans = [
                    RecentBan(
                        ip=b["ip"],
                        timeofban=datetime.fromtimestamp(b["timeofban"]),
                        bantime=b["bantime"],
                        bancount=b["bancount"],
                    )
                    for b in raw_bans
                ]
            except Exception:
                recent_bans = []

        details.append(JailDetail(
            name=info.name,
            currently_failed=status.get("currently_failed", 0),
            total_failed=status.get("total_failed", 0),
            currently_banned=info.banned_count,
            total_banned=status.get("total_banned", 0),
            maxretry=str(info.max_retry),
            bantime=str(info.ban_time),
            findtime=str(info.find_time),
            banned_ips=displayed_ips,
            banned_ips_overflow=overflow,
            recent_bans=recent_bans,
            history_available=history_available,
        ))

    return details


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Collecte le détail complet de chaque jail active : statut live
#   (Fail2banAdapter), paramètres de config (get_jail_config), et
#   historique récent des bans (Fail2banHistoryReader) pour le
#   rapport détaillé fail2ban (menu 6.4).
#
# Pourquoi dans application/queries/f2b_report/ (charte) :
# - Lecture seule, orchestre deux sources déjà résolues par
#   l'appelant (adapter injecté, history_reader injecté).
#
# Points clés :
# - MAX_DISPLAYED_BANNED_IPS (20) / MAX_RECENT_BANS (10) : plafonds
#   décidés en session pour éviter une liste interminable sur un
#   jail à fort débit.
# - history_available propagé par jail : si Fail2banHistoryReader
#   n'a pas de base disponible, chaque JailDetail le signale
#   explicitement plutôt que de laisser croire à "aucun ban récent".
# - _get_config_param() : best-effort, jamais bloquant (une erreur
#   sur un paramètre n'empêche pas la collecte du reste).
#
# Comment il sera utilisé :
# - report_builder.py appelle collect_jails_detail() pour peupler
#   F2bReportData.jails.
#----------------------------------------------------------------------
