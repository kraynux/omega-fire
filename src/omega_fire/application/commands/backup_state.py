# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Backup state command.

Orchestrates the creation of a full-state snapshot (menu 7.1):
reads the current live state from all available backends (nftables,
iptables, fail2ban), converts it to domain types, and delegates the
actual snapshot creation to the persistence port.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from omega_fire.domain.ip_blacklist.models import BanEntry, BanStatus, BanSource
from omega_fire.domain.fail2ban.models import Jail, JailConfig, JailStatus, JailManagedBy
from omega_fire.infrastructure.exceptions import StorageError


@dataclass
class BackupStateRequest:
    """Input for the backup state use case."""
    description: str = ""
    origin: str = "manual"


@dataclass
class BackupStateResult:
    """Output of the backup state use case."""
    success: bool
    message: str
    snapshot_id: Optional[str] = None
    blacklist_count: int = 0
    rules_count: int = 0
    jails_count: int = 0


def _collect_banned_ips(adapters: dict[str, Any]) -> list[BanEntry]:
    """Read banned IPs from all available backends, converted to BanEntry."""
    entries: list[BanEntry] = []

    for backend, adapter in adapters.items():
        if adapter is None:
            continue
        try:
            if hasattr(adapter, "list_bans"):
                raw = adapter.list_bans()
            elif hasattr(adapter, "list_banned_ips"):
                raw = adapter.list_banned_ips()
            else:
                continue
        except Exception:
            continue

        for item in raw:
            if isinstance(item, dict):
                ip = item.get("ip")
                comment = item.get("comment", "")
            else:
                ip = getattr(item, "ip", None)
                comment = getattr(item, "comment", "")
            if not ip:
                continue
            entries.append(BanEntry(
                ip=str(ip).split("/")[0].strip(),
                backend=backend,
                status=BanStatus.ACTIVE,
                comment=comment,
                source=BanSource.MANUAL,
            ))

    return entries


def _collect_jails(fail2ban_adapter: Any) -> list[Jail]:
    """Read jail state from fail2ban, converted to domain Jail objects."""
    if fail2ban_adapter is None:
        return []

    try:
        jail_names = fail2ban_adapter.list_jails()
    except Exception:
        return []

    jails: list[Jail] = []
    for name in jail_names:
        try:
            status = fail2ban_adapter.get_jail_status(name)
        except Exception:
            status = {}

        config = JailConfig(
            jail_name=name,
            log_path="",
            maxretry=5,
            bantime=3600,
            findtime=600,
        )
        jails.append(Jail(
            name=name,
            config=config,
            status=JailStatus.ACTIVE,
            managed_by=JailManagedBy.EXTERNAL,
            currently_banned=status.get("currently_banned", 0),
            total_banned=status.get("total_banned", 0),
        ))

    return jails


class BackupStateCommand:
    """Use case: capture the current full system state as a snapshot."""

    def __init__(self, persistence_port: Any, adapters: dict[str, Any]):
        """Initialize the command.

        Args:
            persistence_port: implementation of PersistencePort
                (via app/dependency_container.py::get_persistence_port()).
            adapters: mapping of backend name -> resolved adapter
                (nftables, iptables, ip6tables, fail2ban).
        """
        self._port = persistence_port
        self._adapters = adapters

    def execute(self, request: BackupStateRequest) -> BackupStateResult:
        banned_ips = _collect_banned_ips({
            k: v for k, v in self._adapters.items()
            if k in ("nftables", "iptables", "ip6tables", "fail2ban")
        })

        rules = []
        for backend in ("nftables", "iptables", "ip6tables"):
            adapter = self._adapters.get(backend)
            if adapter is None:
                continue
            try:
                rules.extend(adapter.list_rules())
            except Exception:
                continue

        jails = _collect_jails(self._adapters.get("fail2ban"))

        if not banned_ips and not rules and not jails:
            return BackupStateResult(
                success=False,
                message="Aucune donnée disponible à sauvegarder (aucun backend actif ?).",
            )

        try:
            snapshot = self._port.create_snapshot(
                banned_ips=banned_ips,
                rules=rules,
                jails=jails,
                description=request.description,
                origin=request.origin,
            )
        except StorageError as e:
            return BackupStateResult(success=False, message=f"Échec de la sauvegarde : {e}")
        except Exception as e:
            return BackupStateResult(success=False, message=f"Erreur inattendue : {e}")

        return BackupStateResult(
            success=True,
            message=f"Snapshot créé avec succès : {snapshot.id}",
            snapshot_id=snapshot.id,
            blacklist_count=snapshot.blacklist_count,
            rules_count=snapshot.rules_count,
            jails_count=snapshot.jails_count,
        )


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Orchestre la capture de l'état système complet (menu 7.1) : lit
#   l'état live de tous les backends disponibles, convertit vers les
#   types du domaine, délègue la création réelle du snapshot au port
#   persistence.
#
# Pourquoi dans application/commands/ (charte) :
# - Orchestration : lecture multi-adapters + conversion + délégation.
# - Pattern simple (comme les autres commands de cette session) : pas
#   de pipeline ExecutionPlan.
#
# Points clés :
# - Source de données : adapters live uniquement (nftables/iptables/
#   fail2ban), jamais les repositories SQLite — cohérent avec la
#   décision de session (bans jamais peuplée en base par action_2_1).
# - _collect_jails() : JailConfig reconstruit avec des valeurs par
#   défaut (maxretry=5, bantime=3600, findtime=600) — get_jail_status()
#   ne fournit pas ces paramètres, seulement les compteurs. Les vraies
#   valeurs de config seraient à lire via get_jail_config() si un jour
#   nécessaire pour la restauration exacte.
#
# Flux d'exécution :
# interfaces/cli/actions.py : action_7_1_backup_state(ctx)
#   ↓ résout persistence_port + adapters via ctx.container
# application/commands/backup_state.py : BackupStateCommand.execute()
#   ↓ persistence_port.create_snapshot()
#----------------------------------------------------------------------
