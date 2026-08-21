# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Infrastructure probe subsystem.

Provides system detection capabilities for Omega-Fire.
This package contains probes for commands, services, and kernel modules,
along with the scanner that orchestrates them and populates the capability registry.
"""
from omega_fire.infrastructure.probe.command_probe import (
    CommandProbe,
    probe_command,
    is_command_available,
)
from omega_fire.infrastructure.probe.service_probe import (
    ServiceProbe,
    probe_service,
    is_service_active,
)
from omega_fire.infrastructure.probe.kernel_probe import (
    KernelProbe,
    probe_kernel,
    is_nftables_supported,
    is_iptables_supported,
)
from omega_fire.infrastructure.probe.scanner import (
    SystemScanner,
    scan_system,
)
from omega_fire.infrastructure.probe.capability_mapper import (
    CapabilityMapper,
    map_command_to_capability,
    map_service_to_capability,
)
from omega_fire.infrastructure.probe.exceptions import (
    ProbeError,
    ProbeExecutionError,
    ProbeTimeoutError,
    CapabilityMappingError,
    ScannerError,
)
from omega_fire.infrastructure.probe.results import (
    ProbeResult,
    CommandProbeResult,
    ServiceProbeResult,
    KernelProbeResult,
    ScanResult,
)

__all__ = [
    # Command probe
    "CommandProbe",
    "probe_command",
    "is_command_available",
    # Service probe
    "ServiceProbe",
    "probe_service",
    "is_service_active",
    # Kernel probe
    "KernelProbe",
    "probe_kernel",
    "is_nftables_supported",
    "is_iptables_supported",
    # Scanner
    "SystemScanner",
    "scan_system",
    # Capability mapper
    "CapabilityMapper",
    "map_command_to_capability",
    "map_service_to_capability",
    # Exceptions
    "ProbeError",
    "ProbeExecutionError",
    "ProbeTimeoutError",
    "CapabilityMappingError",
    "ScannerError",
    # Results
    "ProbeResult",
    "CommandProbeResult",
    "ServiceProbeResult",
    "KernelProbeResult",
    "ScanResult",
]

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Exports publics du sous-système probe
# - Facilite les imports depuis d'autres modules
# - Permet d'importer directement : from omega_fire.infrastructure.probe import scan_system
#
# Pourquoi dans infrastructure/ (charte) :
# - C'est le point d'entrée technique pour la détection système
# - Expose les classes et fonctions publiques des probes
# - Pas de logique métier, juste des ré-exports
#
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier
# ❌ Pas d'implémentation (juste des imports)
# ❌ Pas de dépendance vers domain/ ou interfaces/
#
# Points clés :
# - Importe toutes les classes et fonctions publiques des modules probe
# - Définit __all__ pour contrôler les exports
# - Permet des imports simplifiés depuis l'extérieur
#
# Comment il sera utilisé (aperçu) :
# - app/bootstrap.py importera scan_system pour initialiser le registre
# - Les tests importeront les probes individuellement
# - interfaces/cli/actions.py importera scan_system pour le re-scan manuel
#---------------------------------------------------------------------->
