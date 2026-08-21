# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Service manager detector.

Detects which service manager is available on the current system
(systemd, openrc, runit, or none). Uses multiple detection strategies:
- Check /proc/1/comm for the init process name
- Check for the presence of known binaries (systemctl, rc-service, sv)
- Check for known directories (/run/systemd/system, /etc/init.d, /etc/runit)

This module performs real system I/O (file reads, binary checks) and
is therefore in infrastructure/. The result is a ServiceManagerType
enum value that can be used by the capability registry.
"""
import os
import shutil
from pathlib import Path
from typing import Optional
from omega_fire.core.enums import ServiceManagerType
from omega_fire.infrastructure.backends.service_manager.exceptions import (
    ServiceManagerDetectionError,
)


class ServiceManagerDetector:
    """Detects the service manager available on the current system.
    
    Uses multiple detection strategies to determine which service
    manager is present: systemd, openrc, runit, or none.
    """
    
    # Detection order: check most common first
    DETECTION_STRATEGIES = [
        ("systemd", ServiceManagerType.SYSTEMD),
        ("openrc", ServiceManagerType.OPENRC),
        ("runit", ServiceManagerType.RUNIT),
    ]
    
    def __init__(self):
        """Initialize the detector."""
        self._cache: Optional[ServiceManagerType] = None
    
    def detect(self) -> ServiceManagerType:
        """Detect the service manager on the current system.
        
        Uses multiple strategies:
        1. Check /proc/1/comm for the init process name
        2. Check for the presence of known binaries
        3. Check for known directories
        
        Returns:
            ServiceManagerType indicating which manager is available
        
        Raises:
            ServiceManagerDetectionError: If detection fails unexpectedly
        """
        if self._cache is not None:
            return self._cache
        
        try:
            # Strategy 1: Check /proc/1/comm
            result = self._detect_from_proc()
            if result is not None:
                self._cache = result
                return result
            
            # Strategy 2: Check for binaries
            result = self._detect_from_binaries()
            if result is not None:
                self._cache = result
                return result
            
            # Strategy 3: Check for directories
            result = self._detect_from_directories()
            if result is not None:
                self._cache = result
                return result
            
            # No service manager detected
            self._cache = ServiceManagerType.NONE
            return ServiceManagerType.NONE
        
        except Exception as e:
            raise ServiceManagerDetectionError(
                reason=str(e),
                context={"strategies_tried": ["proc", "binaries", "directories"]},
            ) from e
    
    def _detect_from_proc(self) -> Optional[ServiceManagerType]:
        """Detect service manager by reading /proc/1/comm.
        
        Returns:
            ServiceManagerType if detected, None otherwise
        """
        try:
            proc_comm = Path("/proc/1/comm")
            if proc_comm.exists():
                init_name = proc_comm.read_text().strip()
                
                if init_name == "systemd":
                    return ServiceManagerType.SYSTEMD
                elif init_name == "openrc-init" or init_name == "openrc":
                    return ServiceManagerType.OPENRC
                elif init_name == "runit" or init_name == "runsvdir":
                    return ServiceManagerType.RUNIT
        except (OSError, PermissionError):
            # Cannot read /proc/1/comm — try next strategy
            pass
        
        return None
    
    def _detect_from_binaries(self) -> Optional[ServiceManagerType]:
        """Detect service manager by checking for known binaries.
        
        Returns:
            ServiceManagerType if detected, None otherwise
        """
        # Check for systemctl (systemd)
        if shutil.which("systemctl") is not None:
            return ServiceManagerType.SYSTEMD
        
        # Check for rc-service (openrc)
        if shutil.which("rc-service") is not None:
            return ServiceManagerType.OPENRC
        
        # Check for sv (runit)
        if shutil.which("sv") is not None:
            return ServiceManagerType.RUNIT
        
        return None
    
    def _detect_from_directories(self) -> Optional[ServiceManagerType]:
        """Detect service manager by checking for known directories.
        
        Returns:
            ServiceManagerType if detected, None otherwise
        """
        # Check for systemd runtime directory
        if Path("/run/systemd/system").exists():
            return ServiceManagerType.SYSTEMD
        
        # Check for openrc init directory
        if Path("/etc/init.d").exists() and Path("/etc/rc.conf").exists():
            return ServiceManagerType.OPENRC
        
        # Check for runit service directory
        if Path("/etc/runit").exists() or Path("/etc/sv").exists():
            return ServiceManagerType.RUNIT
        
        return None
    
    def is_available(self, manager_type: ServiceManagerType) -> bool:
        """Check if a specific service manager is available.
        
        Args:
            manager_type: The service manager type to check
        
        Returns:
            True if the specified manager is available
        """
        detected = self.detect()
        return detected == manager_type
    
    def get_detected_manager(self) -> Optional[ServiceManagerType]:
        """Get the detected service manager without raising exceptions.
        
        Returns:
            ServiceManagerType if detected, None if detection failed
        """
        try:
            return self.detect()
        except ServiceManagerDetectionError:
            return None
    
    def clear_cache(self) -> None:
        """Clear the detection cache.
        
        This forces the next detect() call to re-run all strategies.
        """
        self._cache = None
    
    def get_detection_details(self) -> dict:
        """Get detailed information about the detection process.
        
        Returns:
            Dictionary with detection details
        """
        detected = self.detect()
        
        return {
            "detected": detected.value,
            "binary_systemctl": shutil.which("systemctl") is not None,
            "binary_rc_service": shutil.which("rc-service") is not None,
            "binary_sv": shutil.which("sv") is not None,
            "directory_systemd": Path("/run/systemd/system").exists(),
            "directory_openrc": Path("/etc/init.d").exists(),
            "directory_runit": Path("/etc/runit").exists(),
            "proc_1_comm": self._read_proc_comm(),
        }
    
    def _read_proc_comm(self) -> Optional[str]:
        """Read /proc/1/comm if accessible.
        
        Returns:
            Init process name if readable, None otherwise
        """
        try:
            proc_comm = Path("/proc/1/comm")
            if proc_comm.exists():
                return proc_comm.read_text().strip()
        except (OSError, PermissionError):
            pass
        return None


def detect_service_manager() -> ServiceManagerType:
    """Convenience function to detect the service manager.
    
    Returns:
        ServiceManagerType indicating which manager is available
    """
    detector = ServiceManagerDetector()
    return detector.detect()


def is_systemd_available() -> bool:
    """Check if systemd is available.
    
    Returns:
        True if systemd is detected
    """
    detector = ServiceManagerDetector()
    return detector.is_available(ServiceManagerType.SYSTEMD)


def is_openrc_available() -> bool:
    """Check if openrc is available.
    
    Returns:
        True if openrc is detected
    """
    detector = ServiceManagerDetector()
    return detector.is_available(ServiceManagerType.OPENRC)


def is_runit_available() -> bool:
    """Check if runit is available.
    
    Returns:
        True if runit is detected
    """
    detector = ServiceManagerDetector()
    return detector.is_available(ServiceManagerType.RUNIT)


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Détecte quel gestionnaire de services est disponible sur le système actuel
#   (systemd, openrc, runit, ou aucun). Utilise 3 stratégies de détection :
#   1. Lecture de /proc/1/comm pour identifier le processus init
#   2. Vérification de la présence des binaires (systemctl, rc-service, sv)
#   3. Vérification de la présence des répertoires caractéristiques
# Pourquoi dans infrastructure/ (charte) :
# - C'est une détection technique qui nécessite des I/O système réels
#   (lecture de fichiers, vérification de binaires via shutil.which)
# - Le résultat (ServiceManagerType) est utilisé par le registre de capacités
# - Aucun autre module ne doit recoder cette détection (clause omega-fire)
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier (pas de règles firewall/fail2ban)
# ❌ Pas de contrôle de service (juste la détection)
# ❌ Pas de dépendance vers domain/ ou interfaces/
# Points clés :
# - ServiceManagerDetector : classe principale avec cache pour éviter les détections répétées
# - 3 stratégies de détection dans l'ordre :
#   1. _detect_from_proc() : lit /proc/1/comm (le plus fiable)
#   2. _detect_from_binaries() : vérifie systemctl, rc-service, sv
#   3. _detect_from_directories() : vérifie /run/systemd, /etc/init.d, /etc/runit
# - Méthodes utilitaires : is_available(), get_detected_manager(), clear_cache()
# - get_detection_details() : retourne un dict avec tous les détails de détection
# - Fonctions de convenance : detect_service_manager(), is_systemd_available(), etc.
# - Cache interne : _cache évite de relancer les détections à chaque appel
# Comment il sera utilisé (aperçu) :
# - infrastructure/probe/service_probe.py l'utilisera pour détecter le gestionnaire
# - infrastructure/probe/scanner.py alimentera le registre avec le résultat
# - interfaces/cli/tree_builder.py grisera les menus 4.10-4.12 si aucun gestionnaire
#---------------------------------------------------------------------->
