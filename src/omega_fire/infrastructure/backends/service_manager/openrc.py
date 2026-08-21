# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""OpenRC service manager implementation.

Implements the ServiceManager interface for OpenRC-based systems (Alpine, Gentoo).
Uses rc-service and rc-update commands to control services.

This module performs real system I/O (subprocess calls) and is therefore
in infrastructure/. It implements the ServiceManager contract defined
in adapter.py.
"""
import subprocess
from typing import Optional
from omega_fire.core.enums import ServiceManagerType
from omega_fire.infrastructure.backends.service_manager.adapter import (
    ServiceManager,
    ServiceStatus,
)
from omega_fire.infrastructure.backends.service_manager.exceptions import (
    ServiceNotFoundError,
    ServiceControlError,
    ServiceStatusError,
)


class OpenRCServiceManager(ServiceManager):
    """OpenRC implementation of the ServiceManager interface.
    
    Uses rc-service and rc-update commands to control services on
    OpenRC-based systems (Alpine Linux, Gentoo).
    """
    
    def __init__(self):
        """Initialize the OpenRC service manager."""
        self._rc_service_bin = "rc-service"
        self._rc_update_bin = "rc-update"
    
    def get_type(self) -> ServiceManagerType:
        """Get the type of service manager.
        
        Returns:
            ServiceManagerType.OPENRC
        """
        return ServiceManagerType.OPENRC
    
    def start(self, service_name: str) -> bool:
        """Start a service using rc-service start.
        
        Args:
            service_name: Name of the service to start
        
        Returns:
            True if the service was started successfully
        
        Raises:
            ServiceNotFoundError: If the service does not exist
            ServiceControlError: If the start operation fails
        """
        try:
            result = subprocess.run(
                [self._rc_service_bin, service_name, "start"],
                capture_output=True,
                text=True,
                check=False,
            )
            
            if result.returncode == 0:
                return True
            elif "not found" in result.stderr.lower():
                raise ServiceNotFoundError(
                    service_name=service_name,
                    manager_type="openrc",
                )
            else:
                raise ServiceControlError(
                    service_name=service_name,
                    operation="start",
                    reason=result.stderr.strip() or f"Exit code {result.returncode}",
                    manager_type="openrc",
                )
        
        except FileNotFoundError:
            raise ServiceControlError(
                service_name=service_name,
                operation="start",
                reason="rc-service binary not found",
                manager_type="openrc",
            )
    
    def stop(self, service_name: str) -> bool:
        """Stop a service using rc-service stop.
        
        Args:
            service_name: Name of the service to stop
        
        Returns:
            True if the service was stopped successfully
        
        Raises:
            ServiceNotFoundError: If the service does not exist
            ServiceControlError: If the stop operation fails
        """
        try:
            result = subprocess.run(
                [self._rc_service_bin, service_name, "stop"],
                capture_output=True,
                text=True,
                check=False,
            )
            
            if result.returncode == 0:
                return True
            elif "not found" in result.stderr.lower():
                raise ServiceNotFoundError(
                    service_name=service_name,
                    manager_type="openrc",
                )
            else:
                raise ServiceControlError(
                    service_name=service_name,
                    operation="stop",
                    reason=result.stderr.strip() or f"Exit code {result.returncode}",
                    manager_type="openrc",
                )
        
        except FileNotFoundError:
            raise ServiceControlError(
                service_name=service_name,
                operation="stop",
                reason="rc-service binary not found",
                manager_type="openrc",
            )
    
    def restart(self, service_name: str) -> bool:
        """Restart a service using rc-service restart.
        
        Args:
            service_name: Name of the service to restart
        
        Returns:
            True if the service was restarted successfully
        
        Raises:
            ServiceNotFoundError: If the service does not exist
            ServiceControlError: If the restart operation fails
        """
        try:
            result = subprocess.run(
                [self._rc_service_bin, service_name, "restart"],
                capture_output=True,
                text=True,
                check=False,
            )
            
            if result.returncode == 0:
                return True
            elif "not found" in result.stderr.lower():
                raise ServiceNotFoundError(
                    service_name=service_name,
                    manager_type="openrc",
                )
            else:
                raise ServiceControlError(
                    service_name=service_name,
                    operation="restart",
                    reason=result.stderr.strip() or f"Exit code {result.returncode}",
                    manager_type="openrc",
                )
        
        except FileNotFoundError:
            raise ServiceControlError(
                service_name=service_name,
                operation="restart",
                reason="rc-service binary not found",
                manager_type="openrc",
            )
    
    def enable(self, service_name: str) -> bool:
        """Enable a service using rc-update add.
        
        Args:
            service_name: Name of the service to enable
        
        Returns:
            True if the service was enabled successfully
        
        Raises:
            ServiceNotFoundError: If the service does not exist
            ServiceControlError: If the enable operation fails
        """
        try:
            result = subprocess.run(
                [self._rc_update_bin, "add", service_name],
                capture_output=True,
                text=True,
                check=False,
            )
            
            if result.returncode == 0:
                return True
            elif "not found" in result.stderr.lower():
                raise ServiceNotFoundError(
                    service_name=service_name,
                    manager_type="openrc",
                )
            else:
                raise ServiceControlError(
                    service_name=service_name,
                    operation="enable",
                    reason=result.stderr.strip() or f"Exit code {result.returncode}",
                    manager_type="openrc",
                )
        
        except FileNotFoundError:
            raise ServiceControlError(
                service_name=service_name,
                operation="enable",
                reason="rc-update binary not found",
                manager_type="openrc",
            )
    
    def disable(self, service_name: str) -> bool:
        """Disable a service using rc-update del.
        
        Args:
            service_name: Name of the service to disable
        
        Returns:
            True if the service was disabled successfully
        
        Raises:
            ServiceNotFoundError: If the service does not exist
            ServiceControlError: If the disable operation fails
        """
        try:
            result = subprocess.run(
                [self._rc_update_bin, "del", service_name],
                capture_output=True,
                text=True,
                check=False,
            )
            
            if result.returncode == 0:
                return True
            elif "not found" in result.stderr.lower():
                raise ServiceNotFoundError(
                    service_name=service_name,
                    manager_type="openrc",
                )
            else:
                raise ServiceControlError(
                    service_name=service_name,
                    operation="disable",
                    reason=result.stderr.strip() or f"Exit code {result.returncode}",
                    manager_type="openrc",
                )
        
        except FileNotFoundError:
            raise ServiceControlError(
                service_name=service_name,
                operation="disable",
                reason="rc-update binary not found",
                manager_type="openrc",
            )
    
    def status(self, service_name: str) -> ServiceStatus:
        """Get the status of a service using rc-service status.
        
        Args:
            service_name: Name of the service to query
        
        Returns:
            ServiceStatus object with current status
        
        Raises:
            ServiceNotFoundError: If the service does not exist
            ServiceStatusError: If the status query fails
        """
        try:
            result = subprocess.run(
                [self._rc_service_bin, service_name, "status"],
                capture_output=True,
                text=True,
                check=False,
            )
            
            if "not found" in result.stderr.lower():
                raise ServiceNotFoundError(
                    service_name=service_name,
                    manager_type="openrc",
                )
            
            # Parse the output to extract status information
            active = result.returncode == 0
            enabled = self.is_enabled(service_name)
            state = "started" if active else "stopped"
            sub_state = "running" if active else "stopped"
            
            return ServiceStatus(
                service_name=service_name,
                active=active,
                enabled=enabled,
                state=state,
                sub_state=sub_state,
                description="",
            )
        
        except FileNotFoundError:
            raise ServiceStatusError(
                service_name=service_name,
                reason="rc-service binary not found",
                manager_type="openrc",
            )
    
    def is_active(self, service_name: str) -> bool:
        """Check if a service is active using rc-service status.
        
        Args:
            service_name: Name of the service to check
        
        Returns:
            True if the service is active
        """
        try:
            result = subprocess.run(
                [self._rc_service_bin, service_name, "status"],
                capture_output=True,
                text=True,
                check=False,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.SubprocessError):
            return False
    
    def is_enabled(self, service_name: str) -> bool:
        """Check if a service is enabled using rc-update show.
        
        Args:
            service_name: Name of the service to check
        
        Returns:
            True if the service is enabled
        """
        try:
            result = subprocess.run(
                [self._rc_update_bin, "show"],
                capture_output=True,
                text=True,
                check=False,
            )
            
            if result.returncode == 0:
                # Check if the service is in the output
                return service_name in result.stdout
            return False
        except (FileNotFoundError, subprocess.SubprocessError):
            return False
    
    def is_available(self) -> bool:
        """Check if OpenRC is available on the system.
        
        Returns:
            True if rc-service is available
        """
        try:
            result = subprocess.run(
                [self._rc_service_bin, "--version"],
                capture_output=True,
                text=True,
                check=False,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.SubprocessError):
            return False


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Implémente l'interface ServiceManager pour les systèmes OpenRC (Alpine, Gentoo)
# - Utilise les commandes rc-service et rc-update pour contrôler les services
# - Parse la sortie pour extraire les informations de statut
# Pourquoi dans infrastructure/ (charte) :
# - C'est une implémentation concrète qui fait des appels système réels
#   (subprocess.run avec rc-service, rc-update)
# - Implémente le contrat ServiceManager défini dans adapter.py
# - L'application/ ne dépend que de l'interface, pas de cette implémentation
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier (pas de règles firewall/fail2ban)
# ❌ Pas de dépendance vers domain/ ou interfaces/
# ❌ Pas d'appels directs depuis l'UI ou les cas d'usage
# Points clés :
# - OpenRCServiceManager : implémentation concrète de ServiceManager
# - Méthodes de contrôle : start(), stop(), restart()
#   - Utilisent subprocess.run avec rc-service
#   - Lèvent ServiceNotFoundError ou ServiceControlError
# - Méthodes enable()/disable() : utilisent rc-update add/del
# - Méthodes de requête : status(), is_active(), is_enabled()
#   - status() parse la sortie de rc-service status
#   - is_active() vérifie le code de retour de rc-service status
#   - is_enabled() utilise rc-update show et cherche le service dans la sortie
# - is_available() : vérifie que rc-service est présent et fonctionnel
# - Gestion des erreurs : toutes les méthodes capturent FileNotFoundError
#   et le convertissent en ServiceControlError
# - Différences avec systemd :
#   - rc-service au lieu de systemctl
#   - rc-update add/del au lieu de systemctl enable/disable
#   - Pas de parsing complexe de la sortie (plus simple que systemd)
# Comment il sera utilisé (aperçu) :
# - infrastructure/backends/service_manager/detector.py détectera openrc
# - infrastructure/probe/service_probe.py instanciera OpenRCServiceManager
# - application/commands/ utilisera l'interface ServiceManager (pas cette classe)
# - Les tests mockeront cette classe pour simuler différents états de service
#---------------------------------------------------------------------->
