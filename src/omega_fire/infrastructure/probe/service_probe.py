# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Service probe.

Tests the presence and status of system services using the detected
service manager (systemd, openrc, runit). Uses the ServiceManager
adapter to query service status.

This module performs real system I/O (service manager queries) and is
therefore in infrastructure/.
"""
from typing import Optional
from omega_fire.core.enums import ServiceManagerType
from omega_fire.infrastructure.backends.service_manager.detector import ServiceManagerDetector
from omega_fire.infrastructure.backends.service_manager.adapter import ServiceManager
from omega_fire.infrastructure.backends.service_manager.systemd import SystemdServiceManager
from omega_fire.infrastructure.backends.service_manager.openrc import OpenRCServiceManager
from omega_fire.infrastructure.backends.service_manager.runit import RunitServiceManager
from omega_fire.infrastructure.backends.service_manager.exceptions import (
    NoServiceManagerDetectedError,
    ServiceNotFoundError,
    ServiceStatusError,
)
from omega_fire.infrastructure.probe.exceptions import ProbeExecutionError


class ServiceProbe:
    """Probes the presence and status of system services.
    
    Uses the detected service manager to query service status.
    Automatically selects the appropriate adapter based on the
    detected service manager type.
    """
    
    def __init__(self):
        """Initialize the service probe."""
        self._detector = ServiceManagerDetector()
        self._manager: Optional[ServiceManager] = None
    
    def _get_manager(self) -> ServiceManager:
        """Get the appropriate service manager adapter.
        
        Returns:
            ServiceManager instance for the detected manager type
        
        Raises:
            NoServiceManagerDetectedError: If no service manager is detected
        """
        if self._manager is not None:
            return self._manager
        
        detected_type = self._detector.detect()
        
        if detected_type == ServiceManagerType.SYSTEMD:
            self._manager = SystemdServiceManager()
        elif detected_type == ServiceManagerType.OPENRC:
            self._manager = OpenRCServiceManager()
        elif detected_type == ServiceManagerType.RUNIT:
            self._manager = RunitServiceManager()
        else:
            raise NoServiceManagerDetectedError()
        
        return self._manager
    
    def check_service_status(self, service_name: str) -> dict:
        """Check the status of a service.
        
        Args:
            service_name: Name of the service to check
        
        Returns:
            Dictionary with service status:
            - available: bool (service manager available)
            - exists: bool (service exists)
            - active: bool (service is running)
            - enabled: bool (service is enabled at boot)
            - state: str (service state)
            - message: str (description)
        """
        try:
            manager = self._get_manager()
            
            # Check if service exists
            try:
                status = manager.status(service_name)
                
                return {
                    "available": True,
                    "exists": True,
                    "active": status.active,
                    "enabled": status.enabled,
                    "state": status.state,
                    "message": f"Service '{service_name}' is {status.state}",
                }
            
            except ServiceNotFoundError:
                return {
                    "available": True,
                    "exists": False,
                    "active": False,
                    "enabled": False,
                    "state": "not_found",
                    "message": f"Service '{service_name}' not found",
                }
        
        except NoServiceManagerDetectedError:
            return {
                "available": False,
                "exists": False,
                "active": False,
                "enabled": False,
                "state": "no_manager",
                "message": "No service manager detected",
            }
        
        except Exception as e:
            return {
                "available": False,
                "exists": False,
                "active": False,
                "enabled": False,
                "state": "error",
                "message": f"Service probe error: {e}",
            }
    
    def is_service_active(self, service_name: str) -> bool:
        """Check if a service is currently active.
        
        Args:
            service_name: Name of the service to check
        
        Returns:
            True if the service is active
        """
        try:
            manager = self._get_manager()
            return manager.is_active(service_name)
        except (NoServiceManagerDetectedError, ServiceNotFoundError):
            return False
    
    def is_service_enabled(self, service_name: str) -> bool:
        """Check if a service is enabled at boot.
        
        Args:
            service_name: Name of the service to check
        
        Returns:
            True if the service is enabled
        """
        try:
            manager = self._get_manager()
            return manager.is_enabled(service_name)
        except (NoServiceManagerDetectedError, ServiceNotFoundError):
            return False
    
    def probe_service(self, service_name: str) -> dict:
        """Probe a service and return detailed results.
        
        This is an alias for check_service_status() for consistency
        with other probe methods.
        
        Args:
            service_name: Name of the service to probe
        
        Returns:
            Dictionary with probe results
        """
        return self.check_service_status(service_name)
    
    def get_detected_manager_type(self) -> Optional[ServiceManagerType]:
        """Get the detected service manager type.
        
        Returns:
            ServiceManagerType if detected, None otherwise
        """
        return self._detector.get_detected_manager()


def probe_service(service_name: str) -> dict:
    """Convenience function to probe a service.
    
    Args:
        service_name: Name of the service to probe
    
    Returns:
        Dictionary with probe results
    """
    probe = ServiceProbe()
    return probe.probe_service(service_name)


def is_service_active(service_name: str) -> bool:
    """Check if a service is currently active.
    
    Args:
        service_name: Name of the service to check
    
    Returns:
        True if the service is active
    """
    probe = ServiceProbe()
    return probe.is_service_active(service_name)


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Teste la présence et le statut des services système
# - Utilise le ServiceManager détecté (systemd/openrc/runit) pour interroger les services
# - Sélectionne automatiquement l'adapter approprié selon le gestionnaire détecté
# - Retourne des résultats détaillés (disponible, existe, actif, activé, état, message)
# Pourquoi dans infrastructure/ (charte) :
# - C'est une détection technique qui nécessite des I/O système réels
#   (requêtes au gestionnaire de services via subprocess)
# - Le résultat est utilisé par capability_mapper pour créer des Capability
# - Aucun autre module ne doit recoder cette détection (clause omega-fire)
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier (pas de règles firewall/fail2ban)
# ❌ Pas de mapping vers Capability (c'est le rôle de capability_mapper)
# ❌ Pas de dépendance vers domain/ ou interfaces/
# Points clés :
# - ServiceProbe : classe principale qui utilise ServiceManagerDetector
# - _get_manager() : sélectionne l'adapter approprié (systemd/openrc/runit)
#   - Lève NoServiceManagerDetectedError si aucun gestionnaire détecté
# - check_service_status() : méthode principale qui retourne un dict détaillé
#   - available : bool (gestionnaire disponible)
#   - exists : bool (service existe)
#   - active : bool (service en cours d'exécution)
#   - enabled : bool (service activé au boot)
#   - state : str (état du service)
#   - message : str (description du résultat)
# - is_service_active() : vérification rapide de l'état actif
# - is_service_enabled() : vérification rapide de l'activation au boot
# - get_detected_manager_type() : retourne le type de gestionnaire détecté
# - Gestion des erreurs : capture ServiceNotFoundError, NoServiceManagerDetectedError
#   et retourne des résultats structurés plutôt que de lever des exceptions
# - Fonctions de convenance : probe_service(), is_service_active()
# Comment il sera utilisé (aperçu) :
# - infrastructure/probe/scanner.py l'utilisera pour tester fail2ban, nftables, etc.
# - infrastructure/probe/capability_mapper.py transformera les résultats en Capability
# - Les tests mockeront ServiceManager pour simuler différents états de service
#---------------------------------------------------------------------->
