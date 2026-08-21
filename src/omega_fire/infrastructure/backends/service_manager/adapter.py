# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Service manager adapter interface.

Defines the abstract interface for service managers. All concrete
implementations (systemd, openrc, runit) must implement this interface
to provide a uniform API for service control operations.

This is a port/contract that infrastructure/ implements. The application
layer depends on this abstraction, not on concrete implementations.
"""
from abc import ABC, abstractmethod
from typing import Optional
from omega_fire.core.enums import ServiceManagerType


class ServiceStatus:
    """Represents the status of a service.
    
    Contains information about whether a service is active, enabled,
    and its current state.
    """
    
    def __init__(
        self,
        service_name: str,
        active: bool,
        enabled: bool,
        state: str = "unknown",
        sub_state: str = "",
        description: str = "",
    ):
        """Initialize the service status.
        
        Args:
            service_name: Name of the service
            active: Whether the service is currently running
            enabled: Whether the service is enabled at boot
            state: Current state (e.g., "active", "inactive", "failed")
            sub_state: Sub-state (e.g., "running", "dead", "exited")
            description: Human-readable description
        """
        self.service_name = service_name
        self.active = active
        self.enabled = enabled
        self.state = state
        self.sub_state = sub_state
        self.description = description
    
    def is_running(self) -> bool:
        """Check if the service is running.
        
        Returns:
            True if the service is active and in running state
        """
        return self.active and self.sub_state == "running"
    
    def is_failed(self) -> bool:
        """Check if the service has failed.
        
        Returns:
            True if the service is in failed state
        """
        return self.state == "failed"
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation.
        
        Returns:
            Dictionary with status information
        """
        return {
            "service_name": self.service_name,
            "active": self.active,
            "enabled": self.enabled,
            "state": self.state,
            "sub_state": self.sub_state,
            "description": self.description,
        }
    
    def __str__(self) -> str:
        """Return string representation.
        
        Returns:
            String like "sshd: active (running), enabled"
        """
        status = "active" if self.active else "inactive"
        enabled = "enabled" if self.enabled else "disabled"
        return f"{self.service_name}: {status} ({self.sub_state}), {enabled}"


class ServiceManager(ABC):
    """Abstract interface for service managers.
    
    All concrete implementations (systemd, openrc, runit) must implement
    this interface to provide a uniform API for service control operations.
    """
    
    @abstractmethod
    def get_type(self) -> ServiceManagerType:
        """Get the type of service manager.
        
        Returns:
            ServiceManagerType enum value
        """
        pass
    
    @abstractmethod
    def start(self, service_name: str) -> bool:
        """Start a service.
        
        Args:
            service_name: Name of the service to start
        
        Returns:
            True if the service was started successfully
        
        Raises:
            ServiceNotFoundError: If the service does not exist
            ServiceControlError: If the start operation fails
        """
        pass
    
    @abstractmethod
    def stop(self, service_name: str) -> bool:
        """Stop a service.
        
        Args:
            service_name: Name of the service to stop
        
        Returns:
            True if the service was stopped successfully
        
        Raises:
            ServiceNotFoundError: If the service does not exist
            ServiceControlError: If the stop operation fails
        """
        pass
    
    @abstractmethod
    def restart(self, service_name: str) -> bool:
        """Restart a service.
        
        Args:
            service_name: Name of the service to restart
        
        Returns:
            True if the service was restarted successfully
        
        Raises:
            ServiceNotFoundError: If the service does not exist
            ServiceControlError: If the restart operation fails
        """
        pass
    
    @abstractmethod
    def enable(self, service_name: str) -> bool:
        """Enable a service to start at boot.
        
        Args:
            service_name: Name of the service to enable
        
        Returns:
            True if the service was enabled successfully
        
        Raises:
            ServiceNotFoundError: If the service does not exist
            ServiceControlError: If the enable operation fails
        """
        pass
    
    @abstractmethod
    def disable(self, service_name: str) -> bool:
        """Disable a service from starting at boot.
        
        Args:
            service_name: Name of the service to disable
        
        Returns:
            True if the service was disabled successfully
        
        Raises:
            ServiceNotFoundError: If the service does not exist
            ServiceControlError: If the disable operation fails
        """
        pass
    
    @abstractmethod
    def status(self, service_name: str) -> ServiceStatus:
        """Get the status of a service.
        
        Args:
            service_name: Name of the service to query
        
        Returns:
            ServiceStatus object with current status
        
        Raises:
            ServiceNotFoundError: If the service does not exist
            ServiceStatusError: If the status query fails
        """
        pass
    
    @abstractmethod
    def is_active(self, service_name: str) -> bool:
        """Check if a service is currently active.
        
        Args:
            service_name: Name of the service to check
        
        Returns:
            True if the service is active
        """
        pass
    
    @abstractmethod
    def is_enabled(self, service_name: str) -> bool:
        """Check if a service is enabled at boot.
        
        Args:
            service_name: Name of the service to check
        
        Returns:
            True if the service is enabled
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this service manager is available on the system.
        
        Returns:
            True if the service manager is available and functional
        """
        pass


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit l'interface abstraite ServiceManager et la classe ServiceStatus
# - ServiceManager est un contrat (port) que toutes les implémentations concrètes
#   (systemd, openrc, runit) doivent respecter
# - ServiceStatus représente l'état d'un service (actif, activé, état, sous-état)
# Pourquoi dans infrastructure/ (charte) :
# - C'est un contrat technique pour l'infrastructure, pas une règle métier
# - L'application/ dépend de cette abstraction, pas des implémentations concrètes
# - Les implémentations concrètes (systemd.py, openrc.py, runit.py) sont aussi
#   dans infrastructure/ car elles font des appels système
# Ce qu'il ne contient PAS :
# ❌ Pas d'implémentation concrète (juste l'interface abstraite)
# ❌ Pas d'appels système (les implémentations les feront)
# ❌ Pas de logique métier (pas de règles firewall/fail2ban)
# Points clés :
# - ServiceStatus : dataclass avec service_name, active, enabled, state, sub_state
#   - Méthodes : is_running(), is_failed(), to_dict()
# - ServiceManager : classe abstraite (ABC) avec méthodes abstraites :
#   - get_type() : retourne le type de gestionnaire
#   - start(), stop(), restart() : contrôle du service
#   - enable(), disable() : activation/désactivation au boot
#   - status() : retourne ServiceStatus
#   - is_active(), is_enabled() : vérifications rapides
#   - is_available() : vérifie si le gestionnaire est disponible
# - Toutes les méthodes lèvent des exceptions spécifiques :
#   - ServiceNotFoundError : service inexistant
#   - ServiceControlError : échec de l'opération
#   - ServiceStatusError : échec de la requête de statut
# Comment il sera utilisé (aperçu) :
# - infrastructure/backends/service_manager/systemd.py implémentera cette interface
# - infrastructure/backends/service_manager/openrc.py implémentera cette interface
# - infrastructure/backends/service_manager/runit.py implémentera cette interface
# - infrastructure/probe/service_probe.py utilisera l'implémentation détectée
# - application/ ne dépendra que de cette interface, pas des implémentations
#---------------------------------------------------------------------->
