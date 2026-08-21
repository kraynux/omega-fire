# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Core capability registry.

Defines the CapabilityRegistry class, which is the central registry for
all system capabilities. It stores capabilities with their status, allows
querying, updating, and invalidating them. This is the single source of
truth for what is available on the system.
"""
from datetime import datetime
from typing import Optional
from omega_fire.core.capability import Capability
from omega_fire.core.enums import CapabilityStatus
from omega_fire.core.exceptions import (
    RegistryError,
    CapabilityNotFoundError,
    InvalidCapabilityError,
    RegistryStateError,
)


class CapabilityRegistry:
    """Central registry for system capabilities.
    
    This class maintains a dictionary of capabilities indexed by their ID.
    It provides methods to register, update, query, and invalidate capabilities.
    It is the single source of truth for what is available on the system.
    
    The registry is thread-safe for read operations but not for write operations.
    In a multi-threaded environment, external synchronization is required for updates.
    """
    
    def __init__(self):
        """Initialize an empty capability registry."""
        self._capabilities: dict[str, Capability] = {}
        self._initialized: bool = False
    
    def register(self, capability: Capability) -> None:
        """Register a new capability in the registry.
        
        Args:
            capability: The capability to register
        
        Raises:
            InvalidCapabilityError: If the capability is invalid
            RegistryError: If a capability with the same ID already exists
        """
        if not capability.id:
            raise InvalidCapabilityError(
                "Capability ID cannot be empty",
                capability_id=capability.id,
            )
        
        if capability.id in self._capabilities:
            raise RegistryError(
                f"Capability '{capability.id}' is already registered",
                capability_id=capability.id,
                operation="register",
            )
        
        self._capabilities[capability.id] = capability
        self._initialized = True
    
    def update(self, capability: Capability) -> None:
        """Update an existing capability in the registry.
        
        Args:
            capability: The capability with updated status
        
        Raises:
            CapabilityNotFoundError: If the capability is not registered
            InvalidCapabilityError: If the capability is invalid
        """
        if not capability.id:
            raise InvalidCapabilityError(
                "Capability ID cannot be empty",
                capability_id=capability.id,
            )
        
        if capability.id not in self._capabilities:
            raise CapabilityNotFoundError(capability.id)
        
        self._capabilities[capability.id] = capability
    
    def get(self, capability_id: str) -> Optional[Capability]:
        """Get a capability by ID.
        
        Args:
            capability_id: The ID of the capability to retrieve
        
        Returns:
            The capability if found, None otherwise
        """
        return self._capabilities.get(capability_id)
    
    def get_or_raise(self, capability_id: str) -> Capability:
        """Get a capability by ID, raising an exception if not found.
        
        Args:
            capability_id: The ID of the capability to retrieve
        
        Returns:
            The capability
        
        Raises:
            CapabilityNotFoundError: If the capability is not registered
        """
        capability = self.get(capability_id)
        if capability is None:
            raise CapabilityNotFoundError(capability_id)
        return capability
    
    def is_available(self, capability_id: str, allow_degraded: bool = False) -> bool:
        """Check if a capability is available.
        
        Args:
            capability_id: The ID of the capability to check
            allow_degraded: If True, consider DEGRADED as available
        
        Returns:
            True if the capability is available (or degraded with allow_degraded=True)
        """
        capability = self.get(capability_id)
        if capability is None:
            return False
        return capability.is_usable(allow_degraded)
    
    def is_registered(self, capability_id: str) -> bool:
        """Check if a capability is registered.
        
        Args:
            capability_id: The ID of the capability to check
        
        Returns:
            True if the capability is registered
        """
        return capability_id in self._capabilities
    
    def invalidate(self, capability_id: str, reason: str = "") -> None:
        """Invalidate a capability by marking it as MISSING.
        
        Args:
            capability_id: The ID of the capability to invalidate
            reason: Optional reason for invalidation
        
        Raises:
            CapabilityNotFoundError: If the capability is not registered
        """
        capability = self.get_or_raise(capability_id)
        capability.mark_missing(reason)
    
    def mark_degraded(self, capability_id: str, reason: str, detail: Optional[dict] = None) -> None:
        """Mark a capability as degraded.
        
        Args:
            capability_id: The ID of the capability to mark
            reason: Reason for degradation
            detail: Optional technical details
        
        Raises:
            CapabilityNotFoundError: If the capability is not registered
        """
        capability = self.get_or_raise(capability_id)
        capability.mark_degraded(reason, detail)
    
    def mark_disqualified(self, capability_id: str, reason: str, detail: Optional[dict] = None) -> None:
        """Mark a capability as disqualified.
        
        Args:
            capability_id: The ID of the capability to mark
            reason: Reason for disqualification
            detail: Optional technical details
        
        Raises:
            CapabilityNotFoundError: If the capability is not registered
        """
        capability = self.get_or_raise(capability_id)
        capability.mark_disqualified(reason, detail)
    
    def mark_available(self, capability_id: str, reason: str = "") -> None:
        """Mark a capability as available.
        
        Args:
            capability_id: The ID of the capability to mark
            reason: Optional reason message
        
        Raises:
            CapabilityNotFoundError: If the capability is not registered
        """
        capability = self.get_or_raise(capability_id)
        capability.mark_available(reason)
    
    def list_all(self) -> list[Capability]:
        """List all registered capabilities.
        
        Returns:
            List of all capabilities
        """
        return list(self._capabilities.values())
    
    def list_by_status(self, status: CapabilityStatus) -> list[Capability]:
        """List capabilities filtered by status.
        
        Args:
            status: The status to filter by
        
        Returns:
            List of capabilities with the specified status
        """
        return [c for c in self._capabilities.values() if c.status == status]
    
    def list_available(self, include_degraded: bool = False) -> list[Capability]:
        """List available capabilities.
        
        Args:
            include_degraded: If True, include DEGRADED capabilities
        
        Returns:
            List of available capabilities
        """
        return [
            c for c in self._capabilities.values()
            if c.is_usable(allow_degraded=include_degraded)
        ]
    
    def list_missing(self) -> list[Capability]:
        """List missing capabilities.
        
        Returns:
            List of missing capabilities
        """
        return self.list_by_status(CapabilityStatus.MISSING)
    
    def list_degraded(self) -> list[Capability]:
        """List degraded capabilities.
        
        Returns:
            List of degraded capabilities
        """
        return self.list_by_status(CapabilityStatus.DEGRADED)
    
    def list_disqualified(self) -> list[Capability]:
        """List disqualified capabilities.
        
        Returns:
            List of disqualified capabilities
        """
        return self.list_by_status(CapabilityStatus.DISQUALIFIED)
    
    def count(self) -> int:
        """Get the total number of registered capabilities.
        
        Returns:
            Number of capabilities
        """
        return len(self._capabilities)
    
    def count_by_status(self, status: CapabilityStatus) -> int:
        """Get the number of capabilities with a specific status.
        
        Args:
            status: The status to count
        
        Returns:
            Number of capabilities with the specified status
        """
        return len(self.list_by_status(status))
    
    def clear(self) -> None:
        """Clear all capabilities from the registry."""
        self._capabilities.clear()
        self._initialized = False
    
    def is_initialized(self) -> bool:
        """Check if the registry has been initialized.
        
        Returns:
            True if at least one capability has been registered
        """
        return self._initialized
    
    def get_summary(self) -> dict:
        """Get a summary of the registry state.
        
        Returns:
            Dictionary with counts by status
        """
        return {
            "total": self.count(),
            "available": self.count_by_status(CapabilityStatus.AVAILABLE),
            "degraded": self.count_by_status(CapabilityStatus.DEGRADED),
            "missing": self.count_by_status(CapabilityStatus.MISSING),
            "disqualified": self.count_by_status(CapabilityStatus.DISQUALIFIED),
            "initialized": self._initialized,
        }
    
    def to_dict(self) -> dict[str, dict]:
        """Convert the registry to a dictionary.
        
        Returns:
            Dictionary mapping capability ID to capability dict
        """
        return {
            cap_id: cap.to_dict()
            for cap_id, cap in self._capabilities.items()
        }
    
    def __str__(self) -> str:
        """Return string representation.
        
        Returns:
            String like "CapabilityRegistry(5 capabilities: 3 available, 1 degraded, 1 missing)"
        """
        summary = self.get_summary()
        return (
            f"CapabilityRegistry({summary['total']} capabilities: "
            f"{summary['available']} available, "
            f"{summary['degraded']} degraded, "
            f"{summary['missing']} missing, "
            f"{summary['disqualified']} disqualified)"
        )
    
    def __contains__(self, capability_id: str) -> bool:
        """Check if a capability is registered (for 'in' operator).
        
        Args:
            capability_id: The ID to check
        
        Returns:
            True if the capability is registered
        """
        return self.is_registered(capability_id)
    
    def __len__(self) -> int:
        """Get the number of registered capabilities (for len() operator).
        
        Returns:
            Number of capabilities
        """
        return self.count()

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit la classe CapabilityRegistry qui est le registre central des capacités du système. Il stocke toutes les capacités (nftables, iptables, fail2ban, etc.) avec leur statut, permet de les interroger, de les mettre à jour, et de les invalider. C'est le point d'entrée unique pour vérifier ce qui est disponible sur le système.
# Pourquoi dans core/ (charte) :
# - C'est un service transverse utilisé par tout le système
# - Dépend uniquement de core/capability.py, core/enums.py, core/exceptions.py
# - Testable en mémoire pure
# - Utilisé par application/pipeline/guards/ et infrastructure/probe/
# Ce qu'il ne contient PAS (règles projet) : 
# ❌ Pas d'import depuis domain/, application/, infrastructure/, interfaces/
# ❌ Pas de logique métier spécifique
# ❌  Pas de subprocess, sqlite3, rich — aucun I/O
# Points clés :
# - CapabilityRegistry : classe principale avec dictionnaire interne _capabilities
# - Méthodes d'enregistrement : register(), update()
# - Méthodes de requête : get(), get_or_raise(), is_available(), is_registered()
# - Méthodes de modification de statut : invalidate(), mark_degraded(), mark_disqualified(), mark_available()
# - Méthodes de liste : list_all(), list_by_status(), list_available(), list_missing(), list_degraded(), list_disqualified()
# - Méthodes de comptage : count(), count_by_status()
# - Méthodes utilitaires : clear(), is_initialized(), get_summary(), to_dict()
# - Opérateurs : __contains__ (pour in), __len__ (pour len())
# - Aucune dépendance externe : utilise uniquement core/capability.py, core/enums.py, core/exceptions.py
# - Aucun I/O : ne lit ni n'écrit aucun fichier
# Comment il sera utilisé (aperçu) :
# - infrastructure/probe/capability_mapper.py peuplera le registre avec les résultats de probes
# - application/pipeline/guards/capability_guard.py interrogera le registre via is_available()
# - application/pipeline/executor.py vérifiera les capacités avant chaque step
# - interfaces/cli/tree_builder.py construira l'arbre conditionnel basé sur le registre
#---------------------------------------------------------------------->
