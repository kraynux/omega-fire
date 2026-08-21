# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Capability guard for the application pipeline.

This guard verifies that required capabilities are available in the registry
before allowing an action to proceed. It raises CapabilityUnavailableError
if a capability is MISSING, DEGRADED, or DISQUALIFIED.
"""
from typing import Optional
from omega_fire.core.capability_registry import CapabilityRegistry
from omega_fire.core.enums import CapabilityStatus
from omega_fire.application.exceptions import CapabilityUnavailableError


def check_capability(
    capability_id: str,
    registry: CapabilityRegistry,
    allow_degraded: bool = False,
) -> None:
    """Check if a capability is available for execution.
    
    This function verifies that the specified capability exists in the registry
    and has an acceptable status. If the capability is missing or in an
    unacceptable state, it raises CapabilityUnavailableError.
    
    Args:
        capability_id: The capability identifier to check
        registry: The capability registry to query
        allow_degraded: If True, allow DEGRADED status (default: False)
    
    Raises:
        CapabilityUnavailableError: If the capability is not available
    """
    capability = registry.get(capability_id)
    
    if capability is None:
        raise CapabilityUnavailableError(
            capability_id=capability_id,
            status="UNKNOWN",
            reason=f"Capability '{capability_id}' not found in registry"
        )
    
    status = capability.status
    
    # Check if status is acceptable
    if status == CapabilityStatus.MISSING:
        raise CapabilityUnavailableError(
            capability_id=capability_id,
            status=status.value,
            reason=capability.reason or "Capability is not available on this system"
        )
    
    if status == CapabilityStatus.DISQUALIFIED:
        raise CapabilityUnavailableError(
            capability_id=capability_id,
            status=status.value,
            reason=capability.reason or "Capability has been disqualified"
        )
    
    if status == CapabilityStatus.DEGRADED and not allow_degraded:
        raise CapabilityUnavailableError(
            capability_id=capability_id,
            status=status.value,
            reason=capability.reason or "Capability is in degraded state"
        )
    
    # Status is AVAILABLE or DEGRADED (with allow_degraded=True)
    # Guard passes, no exception raised


def check_capabilities(
    capability_ids: list[str],
    registry: CapabilityRegistry,
    allow_degraded: bool = False,
) -> None:
    """Check multiple capabilities at once.
    
    This function verifies that all specified capabilities are available.
    It raises CapabilityUnavailableError for the first capability that fails.
    
    Args:
        capability_ids: List of capability identifiers to check
        registry: The capability registry to query
        allow_degraded: If True, allow DEGRADED status (default: False)
    
    Raises:
        CapabilityUnavailableError: If any capability is not available
    """
    for capability_id in capability_ids:
        check_capability(capability_id, registry, allow_degraded)


def is_capability_available(
    capability_id: str,
    registry: CapabilityRegistry,
    allow_degraded: bool = False,
) -> bool:
    """Check if a capability is available without raising an exception.
    
    This is a non-throwing version of check_capability, useful for
    conditional logic where you want to check availability without
    interrupting the flow.
    
    Args:
        capability_id: The capability identifier to check
        registry: The capability registry to query
        allow_degraded: If True, allow DEGRADED status (default: False)
    
    Returns:
        True if the capability is available, False otherwise
    """
    try:
        check_capability(capability_id, registry, allow_degraded)
        return True
    except CapabilityUnavailableError:
        return False


def get_capability_status(
    capability_id: str,
    registry: CapabilityRegistry,
) -> Optional[CapabilityStatus]:
    """Get the status of a capability without raising an exception.
    
    Args:
        capability_id: The capability identifier to query
        registry: The capability registry to query
    
    Returns:
        The capability status, or None if the capability is not found
    """
    capability = registry.get(capability_id)
    if capability is None:
        return None
    return capability.status


def filter_available_capabilities(
    capability_ids: list[str],
    registry: CapabilityRegistry,
    allow_degraded: bool = False,
) -> list[str]:
    """Filter a list of capabilities to keep only available ones.
    
    This function returns a subset of the input list containing only
    the capabilities that are currently available.
    
    Args:
        capability_ids: List of capability identifiers to filter
        registry: The capability registry to query
        allow_degraded: If True, include DEGRADED capabilities (default: False)
    
    Returns:
        List of available capability identifiers
    """
    available = []
    for capability_id in capability_ids:
        if is_capability_available(capability_id, registry, allow_degraded):
            available.append(capability_id)
    return available


def get_unavailable_capabilities(
    capability_ids: list[str],
    registry: CapabilityRegistry,
    allow_degraded: bool = False,
) -> list[tuple[str, str, str]]:
    """Get a list of unavailable capabilities with their status and reason.
    
    This function returns details about capabilities that are not available,
    useful for error reporting and diagnostics.
    
    Args:
        capability_ids: List of capability identifiers to check
        registry: The capability registry to query
        allow_degraded: If True, treat DEGRADED as available (default: False)
    
    Returns:
        List of tuples (capability_id, status, reason) for unavailable capabilities
    """
    unavailable = []
    for capability_id in capability_ids:
        capability = registry.get(capability_id)
        if capability is None:
            unavailable.append((capability_id, "UNKNOWN", "Not found in registry"))
            continue
        
        status = capability.status
        is_available = (
            status == CapabilityStatus.AVAILABLE
            or (status == CapabilityStatus.DEGRADED and allow_degraded)
        )
        
        if not is_available:
            unavailable.append((
                capability_id,
                status.value,
                capability.reason or "No reason provided"
            ))
    
    return unavailable
# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Garde de capacité du pipeline. Ce guard vérifie qu'une capacité requise est disponible (AVAILABLE) dans le registre avant d'autoriser l'exécution d'une action. Si la capacité est MISSING, DEGRADED ou DISQUALIFIED, il lève CapabilityUnavailableError.
# Pourquoi dans application/pipeline/guards/ (charte) :
# - C'est une vérification de workflow avant exécution
# - Dépend de core/capability_registry.py (contrat interne)
# - Ne dépend pas de infrastructure/ (pas de probe direct)
# - Lève CapabilityUnavailableError définie dans application/exceptions.py
# Ce qu'il ne contient PAS (règles projet) :
# ❌ Pas d'import depuis infrastructure/ (pas de probe, pas de backend)
# ❌ Pas d'import depuis interfaces/ (pas de rendu)
# ❌ Pas d'import depuis domain/ (pas de logique métier)
# ❌ Pas de subprocess, sqlite3, rich — aucun I/O
# Points clés :
# - check_capability() : vérifie une capacité unique, lève CapabilityUnavailableError si indisponible
# - check_capabilities() : vérifie plusieurs capacités, lève l'exception pour la première qui échoue
# - is_capability_available() : version non-throwing pour logique conditionnelle
# - get_capability_status() : retourne le statut sans lever d'exception
# - filter_available_capabilities() : filtre une liste pour garder uniquement les disponibles
# - get_unavailable_capabilities() : retourne les détails des capacités indisponibles
# - Paramètre allow_degraded : permet d'autoriser ou non le statut DEGRADED
# - Aucune dépendance externe : utilise uniquement core/capability_registry.py et core/enums.py
# - Aucun I/O : ne lit ni n'écrit aucun fichier, n'appelle aucun système
# Comment il sera utilisé (aperçu) :
# - application/pipeline/executor.py appellera check_capabilities() avant d'exécuter une commande
# - application/commands/ban_ip.py définira requires=["nftables"] ou requires=["iptables"]
# - interfaces/cli/menu_builder.py utilisera is_capability_available() pour griser les menus
# - interfaces/cli/tree_builder.py construira l'arbre conditionnel basé sur les capacités disponibles
#---------------------------------------------------------------------->
