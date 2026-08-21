# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Core capability model.

Defines the Capability dataclass, which represents a single system capability
with its status, reason, and metadata. This is the fundamental unit of the
capability registry.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from omega_fire.core.enums import CapabilityStatus


@dataclass
class Capability:
    """A single system capability.
    
    Represents a capability with its current status, reason for that status,
    and metadata about when it was last checked. This is the fundamental unit
    stored in the capability registry.
    
    Attributes:
        id: Unique identifier for the capability (e.g., "nftables", "fail2ban")
        status: Current status (AVAILABLE, DEGRADED, MISSING, DISQUALIFIED)
        reason: Human-readable reason for the current status
        detail: Optional dictionary with additional technical details
        last_checked: Timestamp of the last status verification
        category: Optional category for grouping (e.g., "backend", "service")
        metadata: Optional dictionary for arbitrary additional data
    """
    id: str
    status: CapabilityStatus
    reason: str = ""
    detail: Optional[dict[str, Any]] = None
    last_checked: datetime = field(default_factory=datetime.now)
    category: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def is_available(self) -> bool:
        """Check if the capability is fully available.
        
        Returns:
            True if status is AVAILABLE
        """
        return self.status == CapabilityStatus.AVAILABLE
    
    def is_degraded(self) -> bool:
        """Check if the capability is in degraded state.
        
        Returns:
            True if status is DEGRADED
        """
        return self.status == CapabilityStatus.DEGRADED
    
    def is_missing(self) -> bool:
        """Check if the capability is missing.
        
        Returns:
            True if status is MISSING
        """
        return self.status == CapabilityStatus.MISSING
    
    def is_disqualified(self) -> bool:
        """Check if the capability is disqualified.
        
        Returns:
            True if status is DISQUALIFIED
        """
        return self.status == CapabilityStatus.DISQUALIFIED
    
    def is_usable(self, allow_degraded: bool = False) -> bool:
        """Check if the capability can be used.
        
        Args:
            allow_degraded: If True, consider DEGRADED as usable
        
        Returns:
            True if the capability is AVAILABLE, or DEGRADED with allow_degraded=True
        """
        if self.status == CapabilityStatus.AVAILABLE:
            return True
        if allow_degraded and self.status == CapabilityStatus.DEGRADED:
            return True
        return False
    
    def update_status(
        self,
        status: CapabilityStatus,
        reason: str = "",
        detail: Optional[dict[str, Any]] = None,
    ) -> None:
        """Update the capability status.
        
        Args:
            status: New status
            reason: New reason for the status
            detail: Optional new detail dictionary
        """
        self.status = status
        self.reason = reason
        if detail is not None:
            self.detail = detail
        self.last_checked = datetime.now()
    
    def mark_available(self, reason: str = "") -> None:
        """Mark the capability as available.
        
        Args:
            reason: Optional reason message
        """
        self.update_status(CapabilityStatus.AVAILABLE, reason)
    
    def mark_degraded(self, reason: str, detail: Optional[dict[str, Any]] = None) -> None:
        """Mark the capability as degraded.
        
        Args:
            reason: Reason for degradation
            detail: Optional technical details
        """
        self.update_status(CapabilityStatus.DEGRADED, reason, detail)
    
    def mark_missing(self, reason: str = "") -> None:
        """Mark the capability as missing.
        
        Args:
            reason: Optional reason message
        """
        self.update_status(CapabilityStatus.MISSING, reason)
    
    def mark_disqualified(self, reason: str, detail: Optional[dict[str, Any]] = None) -> None:
        """Mark the capability as disqualified.
        
        Args:
            reason: Reason for disqualification
            detail: Optional technical details
        """
        self.update_status(CapabilityStatus.DISQUALIFIED, reason, detail)
    
    def age_seconds(self, now: Optional[datetime] = None) -> float:
        """Calculate the age since last check in seconds.
        
        Args:
            now: Current time (default: datetime.now())
        
        Returns:
            Age in seconds
        """
        if now is None:
            now = datetime.now()
        delta = now - self.last_checked
        return delta.total_seconds()
    
    def is_stale(self, max_age_seconds: int = 300) -> bool:
        """Check if the capability status is stale (too old).
        
        Args:
            max_age_seconds: Maximum age in seconds (default: 5 minutes)
        
        Returns:
            True if the status is older than max_age_seconds
        """
        return self.age_seconds() > max_age_seconds
    
    def to_dict(self) -> dict[str, Any]:
        """Convert the capability to a dictionary.
        
        Returns:
            Dictionary representation of the capability
        """
        return {
            "id": self.id,
            "status": self.status.value,
            "reason": self.reason,
            "detail": self.detail,
            "last_checked": self.last_checked.isoformat(),
            "category": self.category,
            "metadata": self.metadata,
        }
    
    def __str__(self) -> str:
        """Return string representation.
        
        Returns:
            String like "nftables: AVAILABLE (reason)"
        """
        status_str = self.status.value.upper()
        if self.reason:
            return f"{self.id}: {status_str} ({self.reason})"
        return f"{self.id}: {status_str}"


def create_capability(
    capability_id: str,
    status: CapabilityStatus = CapabilityStatus.AVAILABLE,
    reason: str = "",
    detail: Optional[dict[str, Any]] = None,
    category: Optional[str] = None,
) -> Capability:
    """Factory function to create a Capability.
    
    Args:
        capability_id: Unique identifier
        status: Initial status (default: AVAILABLE)
        reason: Initial reason
        detail: Optional detail dictionary
        category: Optional category
    
    Returns:
        Capability instance
    """
    return Capability(
        id=capability_id,
        status=status,
        reason=reason,
        detail=detail,
        category=category,
    )


def create_available_capability(
    capability_id: str,
    category: Optional[str] = None,
) -> Capability:
    """Factory function to create an available capability.
    
    Args:
        capability_id: Unique identifier
        category: Optional category
    
    Returns:
        Capability with AVAILABLE status
    """
    return create_capability(capability_id, CapabilityStatus.AVAILABLE, category=category)


def create_missing_capability(
    capability_id: str,
    reason: str = "",
    category: Optional[str] = None,
) -> Capability:
    """Factory function to create a missing capability.
    
    Args:
        capability_id: Unique identifier
        reason: Reason for being missing
        category: Optional category
    
    Returns:
        Capability with MISSING status
    """
    return create_capability(capability_id, CapabilityStatus.MISSING, reason, category=category)


def create_degraded_capability(
    capability_id: str,
    reason: str,
    detail: Optional[dict[str, Any]] = None,
    category: Optional[str] = None,
) -> Capability:
    """Factory function to create a degraded capability.
    
    Args:
        capability_id: Unique identifier
        reason: Reason for degradation
        detail: Optional technical details
        category: Optional category
    
    Returns:
        Capability with DEGRADED status
    """
    return create_capability(
        capability_id,
        CapabilityStatus.DEGRADED,
        reason,
        detail,
        category,
    )


def create_disqualified_capability(
    capability_id: str,
    reason: str,
    detail: Optional[dict[str, Any]] = None,
    category: Optional[str] = None,
) -> Capability:
    """Factory function to create a disqualified capability.
    
    Args:
        capability_id: Unique identifier
        reason: Reason for disqualification
        detail: Optional technical details
        category: Optional category
    
    Returns:
        Capability with DISQUALIFIED status
    """
    return create_capability(
        capability_id,
        CapabilityStatus.DISQUALIFIED,
        reason,
        detail,
        category,
    )

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit la dataclass Capability qui représente une capacité métier unique dans le système. Chaque capacité a un identifiant, un statut (AVAILABLE, DEGRADED, MISSING, DISQUALIFIED), une raison, des détails optionnels, et une date de dernière vérification. C'est l'unité de base du registre de capacités.
# Pourquoi dans core/ (charte) :
# - C'est un modèle transverse utilisé par tout le système
# - Aucune dépendance externe (pas de domain/, application/, infrastructure/)
# - Testable en mémoire pure
# - Utilisé par core/capability_registry.py
# Ce qu'il ne contient PAS (règles projet) :
# ❌ Pas d'import depuis domain/, application/, infrastructure/, interfaces/
# ❌ Pas de logique métier spécifique
# ❌ Pas de subprocess, sqlite3, rich — aucun I/O
# Points clés :
# - Capability : dataclass principale avec id, status, reason, detail, last_checked, category, metadata
# - Méthodes de vérification : is_available(), is_degraded(), is_missing(), is_disqualified(), is_usable()
# - Méthodes de mise à jour : update_status(), mark_available(), mark_degraded(), mark_missing(), mark_disqualified()
# - Méthodes temporelles : age_seconds(), is_stale()
# - Sérialisation : to_dict() pour conversion en dictionnaire
# - Factory functions : create_capability(), create_available_capability(), create_missing_capability(), etc.
# - Aucune dépendance externe : utilise uniquement dataclasses, datetime, typing, core/enums.py
# - Aucun I/O : ne lit ni n'écrit aucun fichier
# Comment il sera utilisé (aperçu) :
# - core/capability_registry.py stockera des instances de Capability
# - infrastructure/probe/capability_mapper.py créera des Capability à partir des résultats de probes
# - application/pipeline/guards/capability_guard.py vérifiera le statut via is_usable()
# - interfaces/cli/tree_builder.py utilisera is_available() pour griser les menus
#---------------------------------------------------------------------->
