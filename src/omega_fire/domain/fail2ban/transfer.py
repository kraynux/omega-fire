# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Fail2ban transfer logic.

Pure domain logic for transferring banned IPs from fail2ban jails
to the global blacklist (nftables/iptables). This module defines
WHAT to transfer, not HOW to execute the transfer.
"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional
from omega_fire.domain.ip_blacklist.models import BanEntry, BanSource, BanStatus
from omega_fire.domain.fail2ban.models import Jail


class TransferStrategy(Enum):
    """Strategy for transferring IPs from jail to blacklist."""
    ALL_ACTIVE = "all_active"  # Transfer all currently banned IPs
    NEW_ONLY = "new_only"      # Transfer only IPs not already in blacklist
    WITH_THRESHOLD = "with_threshold"  # Transfer only if ban count >= threshold


@dataclass
class TransferPlan:
    """Plan of transfer operations from jail to blacklist.
    
    This is a pure data structure describing what needs to be transferred,
    without any knowledge of how to execute it.
    """
    source_jail: str
    target_backend: str
    entries_to_transfer: list[BanEntry]
    strategy: TransferStrategy
    created_at: datetime = datetime.now()
    
    def count(self) -> int:
        """Return the number of entries to transfer."""
        return len(self.entries_to_transfer)
    
    def is_empty(self) -> bool:
        """Check if there are no entries to transfer."""
        return len(self.entries_to_transfer) == 0


def plan_transfer(
    jail: Jail,
    banned_ips: list[str],
    existing_blacklist: list[BanEntry],
    target_backend: str,
    strategy: TransferStrategy = TransferStrategy.NEW_ONLY,
    threshold: int = 1,
) -> TransferPlan:
    """Plan a transfer of banned IPs from a jail to the blacklist.
    
    Args:
        jail: Source jail
        banned_ips: List of currently banned IPs in the jail
        existing_blacklist: Current blacklist entries
        target_backend: Target backend for transfer ('nftables' or 'iptables')
        strategy: Transfer strategy (default: NEW_ONLY)
        threshold: Minimum ban count for WITH_THRESHOLD strategy
    
    Returns:
        TransferPlan describing what needs to be transferred
    """
    # Build set of IPs already in blacklist
    existing_ips = {e.ip for e in existing_blacklist if e.is_active()}
    
    # Determine which IPs to transfer based on strategy
    ips_to_transfer = []
    
    if strategy == TransferStrategy.ALL_ACTIVE:
        # Transfer all currently banned IPs
        ips_to_transfer = banned_ips
    
    elif strategy == TransferStrategy.NEW_ONLY:
        # Transfer only IPs not already in blacklist
        ips_to_transfer = [ip for ip in banned_ips if ip not in existing_ips]
    
    elif strategy == TransferStrategy.WITH_THRESHOLD:
        # Transfer only if jail has >= threshold banned IPs
        if len(banned_ips) >= threshold:
            ips_to_transfer = [ip for ip in banned_ips if ip not in existing_ips]
    
    # Create BanEntry objects for transfer
    entries_to_transfer = [
        BanEntry(
            ip=ip,
            backend=target_backend,
            status=BanStatus.ACTIVE,
            jail_name=jail.name,
            comment=f"Transferred from jail '{jail.name}'",
            banned_at=datetime.now(),
            source=BanSource.FAIL2BAN_TRANSFER,
        )
        for ip in ips_to_transfer
    ]
    
    return TransferPlan(
        source_jail=jail.name,
        target_backend=target_backend,
        entries_to_transfer=entries_to_transfer,
        strategy=strategy,
    )


def validate_transfer_feasibility(
    jail: Jail,
    target_backend: str,
) -> tuple[bool, Optional[str]]:
    """Validate that a transfer from jail to backend is feasible.
    
    Business rules:
    - Jail must be active
    - Jail must use the same backend as target (or compatible)
    - Jail must have a valid configuration
    
    Args:
        jail: Source jail
        target_backend: Target backend
    
    Returns:
        Tuple of (is_feasible, reason_if_not)
    """
    # Check if jail is active
    if not jail.is_active():
        return False, f"Jail '{jail.name}' is not active"
    
    # Check backend compatibility
    if jail.config.backend != target_backend:
        # Allow transfer if jail backend matches target
        # (e.g., jail uses nftables, transfer to nftables blacklist)
        return False, (
            f"Backend mismatch: jail uses '{jail.config.backend}', "
            f"target is '{target_backend}'"
        )
    
    # Check jail configuration
    if not jail.config.is_valid():
        return False, f"Jail '{jail.name}' has invalid configuration"
    
    return True, None


def should_transfer(
    jail: Jail,
    banned_ips: list[str],
    strategy: TransferStrategy,
    threshold: int = 1,
) -> bool:
    """Determine if a transfer should be performed.
    
    Args:
        jail: Source jail
        banned_ips: List of currently banned IPs
        strategy: Transfer strategy
        threshold: Threshold for WITH_THRESHOLD strategy
    
    Returns:
        True if transfer should be performed, False otherwise
    """
    if not banned_ips:
        return False
    
    if strategy == TransferStrategy.ALL_ACTIVE:
        return True
    
    elif strategy == TransferStrategy.NEW_ONLY:
        return len(banned_ips) > 0
    
    elif strategy == TransferStrategy.WITH_THRESHOLD:
        return len(banned_ips) >= threshold
    
    return False

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit les règles métier de transfert des IPs depuis un jail fail2ban vers la blacklist globale (nftables/iptables). Ce module exprime la logique de décision : quelles IPs doivent être transférées, dans quelles conditions, et avec quelles contraintes.
# Pourquoi dans domain/ (charte) :
# - C'est une règle métier : quand et comment transférer une IP d'un jail vers la blacklist
# - Aucune dépendance externe (opère sur les modèles du domaine)
# - Fonctions pures : pas d'effet de bord, testable en mémoire
# - Utilisé par application/commands/sync_backends.py pour orchestrer le transfert
# Ce qu'il ne contient PAS :
# ❌ Pas d'import depuis infrastructure/ (pas d'appel système)
# ❌ Pas d'import depuis interfaces/ (pas de rendu)
# ❌ Pas d'import depuis application/ (pas de cas d'usage)
# ❌ Pas de logique d'exécution (juste la planification)
# Points clés :
# - TransferPlan : structure de données pure qui décrit quoi transférer, pas comment l'exécuter
# - plan_transfer() : fonction pure qui calcule le plan de transfert en comparant jail et blacklist
# - 3 stratégies de transfert :
#   - ALL_ACTIVE : transfère toutes les IPs bannies du jail
#   - NEW_ONLY : transfère seulement les IPs absentes de la blacklist
#   - WITH_THRESHOLD : transfère seulement si le jail a >= threshold IPs bannies
# - validate_transfer_feasibility() : vérifie qu'un transfert est possible (jail actif, backend compatible)
# - should_transfer() : décide si un transfert doit être effectué selon la stratégie
# - Aucune dépendance externe : opère uniquement sur les modèles du domaine
# Comment il sera utilisé (aperçu) :
# - application/commands/sync_backends.py appellera plan_transfer() pour calculer le plan
# - Le pipeline exécutera le plan via les ports (pas directement ici)
# - interfaces/cli/actions.py proposera les stratégies de transfert à l'utilisateur
#---------------------------------------------------------------------->
