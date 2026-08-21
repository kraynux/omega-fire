# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Sync backends command.

Orchestrates a multi-backend reconciliation of banned IPs (menu 2.6):
builds a merged master list from all available backends, then pushes
to each target backend the IPs it is currently missing.

Note on domain reuse: domain/ip_blacklist/sync.py (plan_sync) models a
point-to-point sync between two named backends, matching 4 specific
supported pairs. This command performs a different operation — an
N-way reconciliation against a virtual merged master list, which is
not a real backend and doesn't fit plan_sync()'s pairwise contract.
Rather than force an ill-fitting reuse, this command keeps its own
simple delta logic (set difference), expressed in terms of BanEntry
for consistency with the domain vocabulary.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class BackendSyncOutcome:
    """Result of syncing a single target backend."""
    backend: str
    added_count: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class SyncBackendsResult:
    """Output of the sync backends use case."""
    outcomes: list[BackendSyncOutcome] = field(default_factory=list)

    @property
    def total_added(self) -> int:
        return sum(o.added_count for o in self.outcomes)

    @property
    def has_errors(self) -> bool:
        return any(o.errors for o in self.outcomes)


class SyncBackendsCommand:
    """Use case: reconcile banned IPs across multiple backends.

    Builds a merged master list of all banned IPs seen across every
    available backend, then ensures each target backend has every IP
    from that master list, adding only what's missing (never removes
    or overwrites existing bans).
    """

    def __init__(self, adapters: dict[str, Any]):
        """Initialize the command.

        Args:
            adapters: mapping of backend name -> already-resolved
                adapter (e.g. {"nftables": ..., "iptables": ..., "fail2ban": ...}).
                Only backends present here are considered.
        """
        self._adapters = adapters

    def execute(self, target_backends: list[str]) -> SyncBackendsResult:
        # --- 1. Cartographie de l'état actuel de chaque backend ---
        backend_states: dict[str, dict[str, str]] = {}
        master_ips: dict[str, str] = {}

        for b_name, adapter in self._adapters.items():
            backend_states[b_name] = {}
            if not adapter:
                continue

            try:
                bans = []
                if hasattr(adapter, "list_bans"):
                    bans = adapter.list_bans()
                elif hasattr(adapter, "list_banned_ips"):
                    bans = adapter.list_banned_ips()

                for item in bans:
                    if isinstance(item, dict):
                        ip = item.get("ip")
                        comment = item.get("comment", "") or item.get("source", "")
                    elif hasattr(item, "ip"):
                        ip = item.ip
                        comment = getattr(item, "comment", "")
                    else:
                        ip = str(item)
                        comment = ""

                    if not ip:
                        continue

                    clean_ip = str(ip).split("/")[0].strip()
                    comment = str(comment).strip() if comment else ""

                    backend_states[b_name][clean_ip] = comment

                    if clean_ip in master_ips:
                        existing = master_ips[clean_ip]
                        if comment and comment not in existing:
                            master_ips[clean_ip] = f"{existing} | {b_name}: {comment}"
                    else:
                        master_ips[clean_ip] = f"{b_name}: {comment}" if comment else ""

            except Exception:
                continue

        result = SyncBackendsResult()

        if not master_ips:
            return result

        # --- 2. Calcul du delta et injection uniquement sur les IP manquantes ---
        for b_name in target_backends:
            adapter = self._adapters.get(b_name)
            outcome = BackendSyncOutcome(backend=b_name)

            if not adapter:
                result.outcomes.append(outcome)
                continue

            current_banned = set(backend_states.get(b_name, {}).keys())
            missing_ips = set(master_ips.keys()) - current_banned

            for ip in missing_ips:
                comment = master_ips[ip]
                final_comment = comment if comment else "Action de synchronisation"
                try:
                    if hasattr(adapter, "ban_ip"):
                        adapter.ban_ip(ip=ip, comment=final_comment)
                        outcome.added_count += 1
                    elif hasattr(adapter, "ban"):
                        adapter.ban(ip=ip, comment=final_comment)
                        outcome.added_count += 1
                except Exception as e:
                    outcome.errors.append(f"{ip} : {e}")

            result.outcomes.append(outcome)

        return result


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Réconciliation multi-backends des IPs bannies (menu 2.6) : fusionne
#   l'état de tous les backends en une liste maîtresse, puis ajoute à
#   chaque backend cible ce qui lui manque. Ne supprime ni n'écrase
#   jamais un ban existant.
#
# Pourquoi dans application/commands/ (charte) :
# - Orchestration : lecture multi-adapters + calcul delta + écriture.
# - Pattern simple (comme create_rule.py, rotate_logs.py) : pas de
#   pipeline ExecutionPlan.
# - Les adapters sont injectés (dict), jamais importés directement
#   depuis infrastructure/backends/.
#
# Compromis assumé (voir docstring de module) :
# - N'utilise PAS domain/ip_blacklist/sync.py::plan_sync(), qui modélise
#   une synchronisation point-à-point entre deux backends nommés, pas
#   une réconciliation N-way contre une liste maîtresse virtuelle.
#
# Flux d'exécution :
# interfaces/cli/actions.py : action_2_6_sync_backends(ctx)
#   ↓ résout les adapters via ctx.container.get_firewall_port(name)
#   ↓ construit le dict adapters, choisit target_backends (saisie utilisateur)
# application/commands/sync_backends.py : SyncBackendsCommand.execute()
#----------------------------------------------------------------------
