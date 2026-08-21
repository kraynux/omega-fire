# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Probe results.
Structured result types for probe operations.
Provides typed result objects that encapsulate probe outcomes
with status, details, and error information.
"""
from dataclasses import dataclass, field
from typing import Any, Optional
from omega_fire.core.enums import CapabilityStatus


@dataclass
class ProbeResult:
    """Base result type for all probe operations.
    
    Attributes:
        success: Whether the probe completed successfully
        capability_id: ID of the capability being probed
        status: Capability status (AVAILABLE, DEGRADED, MISSING, DISQUALIFIED)
        reason: Human-readable explanation of the status
        details: Additional technical details
        error: Error message if probe failed
    """
    success: bool
    capability_id: str
    status: CapabilityStatus
    reason: str
    details: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    
    @classmethod
    def available(cls, capability_id: str, reason: str, details: dict = None) -> "ProbeResult":
        """Create a successful AVAILABLE result."""
        return cls(
            success=True,
            capability_id=capability_id,
            status=CapabilityStatus.AVAILABLE,
            reason=reason,
            details=details or {},
        )
    
    @classmethod
    def degraded(cls, capability_id: str, reason: str, details: dict = None) -> "ProbeResult":
        """Create a DEGRADED result."""
        return cls(
            success=True,
            capability_id=capability_id,
            status=CapabilityStatus.DEGRADED,
            reason=reason,
            details=details or {},
        )
    
    @classmethod
    def missing(cls, capability_id: str, reason: str, details: dict = None) -> "ProbeResult":
        """Create a MISSING result."""
        return cls(
            success=True,
            capability_id=capability_id,
            status=CapabilityStatus.MISSING,
            reason=reason,
            details=details or {},
        )
    
    @classmethod
    def disqualified(cls, capability_id: str, reason: str, details: dict = None) -> "ProbeResult":
        """Create a DISQUALIFIED result."""
        return cls(
            success=True,
            capability_id=capability_id,
            status=CapabilityStatus.DISQUALIFIED,
            reason=reason,
            details=details or {},
        )
    
    @classmethod
    def error(cls, capability_id: str, error_msg: str) -> "ProbeResult":
        """Create an error result."""
        return cls(
            success=False,
            capability_id=capability_id,
            status=CapabilityStatus.MISSING,
            reason=f"Probe failed: {error_msg}",
            error=error_msg,
        )


@dataclass
class CommandProbeResult:
    """Result type for command probe operations.
    
    Attributes:
        present: Whether the binary is present in PATH
        functional: Whether the binary is functional
        path: Full path to the binary (if present)
        message: Human-readable description
    """
    present: bool
    functional: bool
    path: Optional[str]
    message: str
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "present": self.present,
            "functional": self.functional,
            "path": self.path,
            "message": self.message,
        }


@dataclass
class ServiceProbeResult:
    """Result type for service probe operations.
    
    Attributes:
        available: Whether the service manager is available
        exists: Whether the service exists
        active: Whether the service is currently active
        enabled: Whether the service is enabled at boot
        state: Service state string
        message: Human-readable description
    """
    available: bool
    exists: bool
    active: bool
    enabled: bool
    state: str
    message: str
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "available": self.available,
            "exists": self.exists,
            "active": self.active,
            "enabled": self.enabled,
            "state": self.state,
            "message": self.message,
        }


@dataclass
class KernelProbeResult:
    """Result type for kernel probe operations.
    
    Attributes:
        available: Whether kernel support is available
        modules: List of detected kernel modules
        message: Human-readable description
    """
    available: bool
    modules: list[str]
    message: str
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "available": self.available,
            "modules": self.modules,
            "message": self.message,
        }


@dataclass
class ScanResult:
    """Result type for complete system scan.
    
    Attributes:
        capabilities_registered: Total number of capabilities registered
        capabilities_available: Number of AVAILABLE capabilities
        capabilities_degraded: Number of DEGRADED capabilities
        capabilities_missing: Number of MISSING capabilities
        capabilities_disqualified: Number of DISQUALIFIED capabilities
        errors: List of error messages encountered during scan
    """
    capabilities_registered: int
    capabilities_available: int
    capabilities_degraded: int
    capabilities_missing: int
    capabilities_disqualified: int
    errors: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "capabilities_registered": self.capabilities_registered,
            "capabilities_available": self.capabilities_available,
            "capabilities_degraded": self.capabilities_degraded,
            "capabilities_missing": self.capabilities_missing,
            "capabilities_disqualified": self.capabilities_disqualified,
            "errors": self.errors,
        }
    
    @property
    def has_errors(self) -> bool:
        """Check if scan encountered any errors."""
        return len(self.errors) > 0
    
    @property
    def all_available(self) -> bool:
        """Check if all capabilities are AVAILABLE."""
        return (
            self.capabilities_available > 0
            and self.capabilities_degraded == 0
            and self.capabilities_missing == 0
            and self.capabilities_disqualified == 0
        )


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit les types de résultats structurés pour les opérations de probe
# - Fournit des objets typés qui encapsulent les résultats avec statut, détails et erreurs
# - Utilisé par les probes pour retourner des résultats cohérents
#
# Pourquoi dans infrastructure/ (charte) :
# - Ce sont des structures de données techniques pour les probes
# - Elles encapsulent les résultats bruts avant mapping vers Capability
# - Pas de logique métier, juste des conteneurs de données
#
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier (pas de règles firewall/fail2ban)
# ❌ Pas d'appels système (juste des définitions de dataclasses)
# ❌ Pas de dépendance vers domain/ ou interfaces/
#
# Points clés :
# - ProbeResult : résultat générique avec factory methods (available, degraded, missing, etc.)
# - CommandProbeResult : résultat spécifique pour command_probe
# - ServiceProbeResult : résultat spécifique pour service_probe
# - KernelProbeResult : résultat spécifique pour kernel_probe
# - ScanResult : résultat complet du scanner avec compteurs par statut
# - Toutes les classes ont une méthode to_dict() pour sérialisation
# - ScanResult a des propriétés utilitaires (has_errors, all_available)
#
# Comment il sera utilisé (aperçu) :
# - infrastructure/probe/*.py retourneront ces structures
# - infrastructure/probe/capability_mapper.py les convertira en Capability
# - Les tests vérifieront que les résultats sont corrects
#---------------------------------------------------------------------->
