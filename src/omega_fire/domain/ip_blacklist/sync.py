# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""IP blacklist synchronization logic.

Pure domain logic for synchronizing banned IPs between backends.
This module defines WHAT to sync, not HOW to execute the sync.
"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional
from omega_fire.domain.ip_blacklist.models import BanEntry, BanSource, BanStatus


class SyncDirection(Enum):
    """Direction of synchronization between backends."""
    NFTABLES_TO_IPTABLES = "nftables_to_iptables"
    IPTABLES_TO_NFTABLES = "iptables_to_nftables"
    NFTABLES_TO_FAIL2BAN = "nftables_to_fail2ban"
    FAIL2BAN_TO_NFTABLES = "fail2ban_to_nftables"


class SyncStrategy(Enum):
    """Strategy for handling conflicts during sync."""
    SKIP_IF_EXISTS = "skip_if_exists"
    OVERWRITE = "overwrite"
    MERGE_COMMENTS = "merge_comments"


@dataclass
class SyncPlan:
    """Plan of synchronization operations.
    
    This is a pure data structure describing what needs to be synced,
    without any knowledge of how to execute it.
    """
    direction: SyncDirection
    source_backend: str
    target_backend: str
    entries_to_sync: list[BanEntry]
    strategy: SyncStrategy = SyncStrategy.SKIP_IF_EXISTS
    created_at: datetime = datetime.now()
    
    def count(self) -> int:
        """Return the number of entries to sync."""
        return len(self.entries_to_sync)
    
    def is_empty(self) -> bool:
        """Check if there are no entries to sync."""
        return len(self.entries_to_sync) == 0


def plan_sync(
    source_entries: list[BanEntry],
    target_entries: list[BanEntry],
    source_backend: str,
    target_backend: str,
    strategy: SyncStrategy = SyncStrategy.SKIP_IF_EXISTS
) -> SyncPlan:
    """Plan a synchronization from source to target backend.
    
    Args:
        source_entries: Active bans from the source backend
        target_entries: Active bans from the target backend
        source_backend: Source backend name
        target_backend: Target backend name
        strategy: How to handle conflicts
    
    Returns:
        SyncPlan describing what needs to be synced
    """
    # Determine sync direction
    direction = _determine_direction(source_backend, target_backend)
    
    # Filter active entries from source
    active_source = [e for e in source_entries if e.is_active()]
    
    # Build set of IPs already in target
    target_ips = {e.ip for e in target_entries if e.is_active()}
    
    # Determine which entries need to be synced
    entries_to_sync = []
    
    if strategy == SyncStrategy.SKIP_IF_EXISTS:
        # Only sync IPs not already in target
        entries_to_sync = [e for e in active_source if e.ip not in target_ips]
    
    elif strategy == SyncStrategy.OVERWRITE:
        # Sync all active source entries (target will handle duplicates)
        entries_to_sync = active_source
    
    elif strategy == SyncStrategy.MERGE_COMMENTS:
        # Sync all, but mark entries that need comment merging
        entries_to_sync = active_source
    
    # Create sync plan
    return SyncPlan(
        direction=direction,
        source_backend=source_backend,
        target_backend=target_backend,
        entries_to_sync=entries_to_sync,
        strategy=strategy
    )


def _determine_direction(source: str, target: str) -> SyncDirection:
    """Determine the sync direction from source and target backends."""
    if source == "nftables" and target == "iptables":
        return SyncDirection.NFTABLES_TO_IPTABLES
    elif source == "iptables" and target == "nftables":
        return SyncDirection.IPTABLES_TO_NFTABLES
    elif source == "nftables" and target == "fail2ban":
        return SyncDirection.NFTABLES_TO_FAIL2BAN
    elif source == "fail2ban" and target == "nftables":
        return SyncDirection.FAIL2BAN_TO_NFTABLES
    else:
        raise ValueError(f"Unsupported sync direction: {source} -> {target}")


def transform_for_target(
    entry: BanEntry,
    target_backend: str,
    strategy: SyncStrategy = SyncStrategy.SKIP_IF_EXISTS
) -> BanEntry:
    """Transform a ban entry for the target backend.
    
    This creates a new BanEntry adapted for the target backend,
    preserving the original metadata but changing the backend label.
    
    Args:
        entry: Source ban entry
        target_backend: Target backend name
        strategy: Sync strategy (affects comment handling)
    
    Returns:
        New BanEntry adapted for the target backend
    """
    # Build comment with sync metadata
    comment = entry.comment or ""
    if strategy == SyncStrategy.MERGE_COMMENTS:
        comment = f"{comment} [synced from {entry.backend}]".strip()
    
    # Create new entry for target backend
    return BanEntry(
        ip=entry.ip,
        backend=target_backend,
        status=BanStatus.ACTIVE,
        jail_name=None,  # Jail info doesn't transfer across backends
        comment=comment,
        banned_at=entry.banned_at,
        expires_at=entry.expires_at,
        source=BanSource.SYNC
    )


def validate_sync_direction(source: str, target: str) -> bool:
    """Validate that a sync direction is supported.
    
    Args:
        source: Source backend name
        target: Target backend name
    
    Returns:
        True if the sync direction is supported, False otherwise
    """
    supported_pairs = {
        ("nftables", "iptables"),
        ("iptables", "nftables"),
        ("nftables", "fail2ban"),
        ("fail2ban", "nftables"),
    }
    return (source, target) in supported_pairs    

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit les règles métier de synchronisation entre backends (nftables ↔ iptables ↔ fail2ban). Ce module exprime la logique de transfert : quelles IPs doivent être synchronisées, dans quel sens, et avec quelles contraintes.
# Pourquoi dans domain/ :
# - C'est une règle métier : comment synchroniser des IPs entre backends
# - Aucune dépendance externe (opère sur les modèles du domaine)
# - Fonctions pures : pas d'effet de bord, testable en mémoire
# - Utilisé par application/commands/sync_backends.py pour orchestrer la sync
# Ce qu'il ne contient PAS (règles projet)
# ❌ Pas d'import depuis infrastructure/ (pas d'appel système)
# ❌ Pas d'import depuis interfaces/ (pas de rendu)
# ❌ Pas de logique d'exécution (juste la planification)
# Points clés :
# - SyncPlan : structure de données pure qui décrit quoi synchroniser, pas comment l'exécuter
# - plan_sync() : fonction pure qui calcule le plan de sync en comparant source et cible
# - transform_for_target() : adapte un BanEntry pour le backend cible (change le label, préserve les métadonnées)
# - validate_sync_direction() : vérifie qu'une direction de sync est supportée
# - Stratégies de sync : SKIP_IF_EXISTS (ignore les doublons), OVERWRITE (écrase), MERGE_COMMENTS (fusionne les commentaires)
# - Aucune dépendance externe : opère uniquement sur les modèles du domaine
# Comment il sera utilisé (aperçu)
# application/commands/sync_backends.py appellera plan_sync() pour calculer le plan
# Le pipeline exécutera le plan via les ports (pas directement ici)
# interfaces/cli/actions.py proposera les directions de sync à l'utilisateur
#---------------------------------------------------------------------->
