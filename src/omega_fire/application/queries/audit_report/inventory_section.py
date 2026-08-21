# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Current inventory collection: rules count and IPs by backend,
including cross-backend duplicate detection (sections 3 & 6).

Pure collection functions: reads from RuleRepository and BanRepository,
returns DTOs. Reflects the CURRENT state, not a period.
"""
from __future__ import annotations

from typing import Any

from omega_fire.application.queries.audit_report.models import (
    RulesInventory,
    IpInventoryByBackend,
)


def collect_rules_inventory(rule_repository: Any) -> RulesInventory:
    """Collect the current total count of firewall rules (section 3).

    Args:
        rule_repository: RuleRepository instance.

    Returns:
        RulesInventory with the total rule count (enabled + disabled).
    """
    if rule_repository is None:
        return RulesInventory()

    try:
        rules = rule_repository.find_all()
    except Exception:
        return RulesInventory()

    enabled_count = sum(1 for r in rules if getattr(r, "enabled", False))
    return RulesInventory(
        total_count=len(rules),
        enabled_count=enabled_count,
    )


def collect_ip_inventory(adapters: dict[str, Any]) -> tuple[list[IpInventoryByBackend], int, int]:
    """Collect the current count of banned IPs per backend by reading
    the live adapters directly (section 6).

    Reads live state rather than the database — action_2_1_ban_ip and
    similar actions do not currently persist bans to the bans table
    (known limitation, tracked separately), so the database cannot be
    trusted as a source of truth for this section.

    Args:
        adapters: mapping of backend name -> resolved adapter
            (nftables, iptables, fail2ban).

    Returns:
        Tuple of:
        - list of IpInventoryByBackend (count per backend)
        - internal_duplicate_count: number of (ip, backend) pairs where
          the same IP appears more than once WITHIN a single backend's
          list (a technical anomaly, e.g. a duplicated rule).
        - cross_backend_count: number of distinct IPs found active in
          two or more DIFFERENT backends at once (expected after a
          sync, not necessarily an anomaly).
    """
    counts: dict[str, int] = {}
    ip_occurrences_per_backend: dict[tuple[str, str], int] = {}  # (backend, ip) -> count
    backends_by_ip: dict[str, set[str]] = {}

    for backend, adapter in adapters.items():
        if adapter is None:
            continue
        try:
            if hasattr(adapter, "list_bans"):
                bans = adapter.list_bans()
            elif hasattr(adapter, "list_banned_ips"):
                bans = adapter.list_banned_ips()
            else:
                continue
        except Exception:
            continue

        for item in bans:
            if isinstance(item, dict):
                ip = item.get("ip")
            else:
                ip = getattr(item, "ip", None)
            if not ip:
                continue
            clean_ip = str(ip).split("/")[0].strip()

            counts[backend] = counts.get(backend, 0) + 1

            key = (backend, clean_ip)
            ip_occurrences_per_backend[key] = ip_occurrences_per_backend.get(key, 0) + 1

            backends_by_ip.setdefault(clean_ip, set()).add(backend)

    internal_duplicate_count = sum(
        1 for occ in ip_occurrences_per_backend.values() if occ > 1
    )
    cross_backend_count = sum(
        1 for backends in backends_by_ip.values() if len(backends) > 1
    )

    inventory = [
        IpInventoryByBackend(backend=backend, active_count=count)
        for backend, count in sorted(counts.items())
    ]

    return inventory, internal_duplicate_count, cross_backend_count


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Collecte l'inventaire actuel : nombre total de règles (section 3)
#   et IPs bannies par backend + détection de doublons inter-backends
#   (section 6), pour le rapport d'audit (menu 6.3).
#
# Pourquoi dans application/queries/audit_report/ (charte) :
# - Lecture seule, réutilise RuleRepository/BanRepository existants.
#
# Points clés :
# - collect_rules_inventory() : remplace l'ancienne notion d'activité
#   (créées/supprimées depuis une période) par un compte total actuel
#   — décision de session : éviter toute donnée liée à une période
#   pour cette partie du rapport, uniquement des photos à date.
# - collect_ip_inventory() : retourne aussi duplicate_count, distinct
#   de la logique de 2.6 (qui vérifie l'état live des adapters pour
#   pouvoir agir dessus, alors qu'ici on lit la base pour un simple
#   constat — deux sources différentes, volontairement).
#
# Comment il sera utilisé :
# - report_builder.py appelle ces deux fonctions.
#----------------------------------------------------------------------
