# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Systemd service manager implementation.

Implements the ServiceManager interface for systemd-based systems.
Uses systemctl commands to control services.

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


class SystemdServiceManager(ServiceManager):
    """Systemd implementation of the ServiceManager interface.
    
    Uses systemctl commands to control services on systemd-based systems.
    """
    
    def __init__(self):
        """Initialize the systemd service manager."""
        self._systemctl_bin = "systemctl"
    
    def get_type(self) -> ServiceManagerType:
        """Get the type of service manager.
        
        Returns:
            ServiceManagerType.SYSTEMD
        """
        return ServiceManagerType.SYSTEMD
    
    def start(self, service_name: str) -> bool:
        """Start a service using systemctl start.
        
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
                [self._systemctl_bin, "start", service_name],
                capture_output=True,
                text=True,
                check=False,
            )
            
            if result.returncode == 0:
                return True
            elif result.returncode == 5:
                # Unit not found
                raise ServiceNotFoundError(
                    service_name=service_name,
                    manager_type="systemd",
                )
            else:
                raise ServiceControlError(
                    service_name=service_name,
                    operation="start",
                    reason=result.stderr.strip() or f"Exit code {result.returncode}",
                    manager_type="systemd",
                )
        
        except FileNotFoundError:
            raise ServiceControlError(
                service_name=service_name,
                operation="start",
                reason="systemctl binary not found",
                manager_type="systemd",
            )
    
    def stop(self, service_name: str) -> bool:
        """Stop a service using systemctl stop.
        
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
                [self._systemctl_bin, "stop", service_name],
                capture_output=True,
                text=True,
                check=False,
            )
            
            if result.returncode == 0:
                return True
            elif result.returncode == 5:
                raise ServiceNotFoundError(
                    service_name=service_name,
                    manager_type="systemd",
                )
            else:
                raise ServiceControlError(
                    service_name=service_name,
                    operation="stop",
                    reason=result.stderr.strip() or f"Exit code {result.returncode}",
                    manager_type="systemd",
                )
        
        except FileNotFoundError:
            raise ServiceControlError(
                service_name=service_name,
                operation="stop",
                reason="systemctl binary not found",
                manager_type="systemd",
            )
    
    def restart(self, service_name: str) -> bool:
        """Restart a service using systemctl restart.
        
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
                [self._systemctl_bin, "restart", service_name],
                capture_output=True,
                text=True,
                check=False,
            )
            
            if result.returncode == 0:
                return True
            elif result.returncode == 5:
                raise ServiceNotFoundError(
                    service_name=service_name,
                    manager_type="systemd",
                )
            else:
                raise ServiceControlError(
                    service_name=service_name,
                    operation="restart",
                    reason=result.stderr.strip() or f"Exit code {result.returncode}",
                    manager_type="systemd",
                )
        
        except FileNotFoundError:
            raise ServiceControlError(
                service_name=service_name,
                operation="restart",
                reason="systemctl binary not found",
                manager_type="systemd",
            )
    
    def enable(self, service_name: str) -> bool:
        """Enable a service using systemctl enable.
        
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
                [self._systemctl_bin, "enable", service_name],
                capture_output=True,
                text=True,
                check=False,
            )
            
            if result.returncode == 0:
                return True
            elif result.returncode == 5:
                raise ServiceNotFoundError(
                    service_name=service_name,
                    manager_type="systemd",
                )
            else:
                raise ServiceControlError(
                    service_name=service_name,
                    operation="enable",
                    reason=result.stderr.strip() or f"Exit code {result.returncode}",
                    manager_type="systemd",
                )
        
        except FileNotFoundError:
            raise ServiceControlError(
                service_name=service_name,
                operation="enable",
                reason="systemctl binary not found",
                manager_type="systemd",
            )
    
    def disable(self, service_name: str) -> bool:
        """Disable a service using systemctl disable.
        
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
                [self._systemctl_bin, "disable", service_name],
                capture_output=True,
                text=True,
                check=False,
            )
            
            if result.returncode == 0:
                return True
            elif result.returncode == 5:
                raise ServiceNotFoundError(
                    service_name=service_name,
                    manager_type="systemd",
                )
            else:
                raise ServiceControlError(
                    service_name=service_name,
                    operation="disable",
                    reason=result.stderr.strip() or f"Exit code {result.returncode}",
                    manager_type="systemd",
                )
        
        except FileNotFoundError:
            raise ServiceControlError(
                service_name=service_name,
                operation="disable",
                reason="systemctl binary not found",
                manager_type="systemd",
            )
    
    def status(self, service_name: str) -> ServiceStatus:
        """Get the status of a service using systemctl status.
        
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
                [self._systemctl_bin, "status", service_name],
                capture_output=True,
                text=True,
                check=False,
            )
            
            # systemctl status returns 0 if active, 3 if inactive, 4 if unknown
            if result.returncode == 4:
                raise ServiceNotFoundError(
                    service_name=service_name,
                    manager_type="systemd",
                )
            
            # Parse the output to extract status information
            active = result.returncode in (0, 3)  # 0 = active, 3 = inactive
            enabled = self._parse_enabled(result.stdout)
            state = self._parse_state(result.stdout)
            sub_state = self._parse_sub_state(result.stdout)
            description = self._parse_description(result.stdout)
            
            return ServiceStatus(
                service_name=service_name,
                active=active,
                enabled=enabled,
                state=state,
                sub_state=sub_state,
                description=description,
            )
        
        except FileNotFoundError:
            raise ServiceStatusError(
                service_name=service_name,
                reason="systemctl binary not found",
                manager_type="systemd",
            )
    
    def is_active(self, service_name: str) -> bool:
        """Check if a service is active using systemctl is-active.
        
        Args:
            service_name: Name of the service to check
        
        Returns:
            True if the service is active
        """
        try:
            result = subprocess.run(
                [self._systemctl_bin, "is-active", service_name],
                capture_output=True,
                text=True,
                check=False,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.SubprocessError):
            return False
    
    def is_enabled(self, service_name: str) -> bool:
        """Check if a service is enabled using systemctl is-enabled.
        
        Args:
            service_name: Name of the service to check
        
        Returns:
            True if the service is enabled
        """
        try:
            result = subprocess.run(
                [self._systemctl_bin, "is-enabled", service_name],
                capture_output=True,
                text=True,
                check=False,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.SubprocessError):
            return False
    
    def is_available(self) -> bool:
        """Check if systemd is available on the system.
        
        Returns:
            True if systemctl is available
        """
        try:
            result = subprocess.run(
                [self._systemctl_bin, "--version"],
                capture_output=True,
                text=True,
                check=False,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.SubprocessError):
            return False
    
    def _parse_enabled(self, output: str) -> bool:
        """Parse the enabled status from systemctl status output.
        
        Args:
            output: Output from systemctl status
        
        Returns:
            True if the service is enabled
        """
        for line in output.split("\n"):
            if "enabled" in line.lower():
                return True
        return False
    
    def _parse_state(self, output: str) -> str:
        """Parse the state from systemctl status output.
        
        Args:
            output: Output from systemctl status
        
        Returns:
            State string (e.g., "active", "inactive", "failed")
        """
        for line in output.split("\n"):
            if "Active:" in line:
                parts = line.split(":")
                if len(parts) > 1:
                    state = parts[1].strip().split()[0]
                    return state
        return "unknown"
    
    def _parse_sub_state(self, output: str) -> str:
        """Parse the sub-state from systemctl status output.
        
        Args:
            output: Output from systemctl status
        
        Returns:
            Sub-state string (e.g., "running", "dead", "exited")
        """
        for line in output.split("\n"):
            if "Active:" in line:
                parts = line.split("(")
                if len(parts) > 1:
                    sub_state = parts[1].split(")")[0]
                    return sub_state
        return "unknown"
    
    def _parse_description(self, output: str) -> str:
        """Parse the description from systemctl status output.
        
        Args:
            output: Output from systemctl status
        
        Returns:
            Description string
        """
        for line in output.split("\n"):
            if line.strip().startswith("●") or line.strip().startswith("○"):
                parts = line.split("-")
                if len(parts) > 1:
                    return parts[1].strip()
        return ""


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Implémente l'interface ServiceManager pour les systèmes systemd
# - Utilise les commandes systemctl pour contrôler les services
# - Parse la sortie de systemctl pour extraire les informations de statut
# Pourquoi dans infrastructure/ (charte) :
# - C'est une implémentation concrète qui fait des appels système réels
#   (subprocess.run avec systemctl)
# - Implémente le contrat ServiceManager défini dans adapter.py
# - L'application/ ne dépend que de l'interface, pas de cette implémentation
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier (pas de règles firewall/fail2ban)
# ❌ Pas de dépendance vers domain/ ou interfaces/
# ❌ Pas d'appels directs depuis l'UI ou les cas d'usage
# Points clés :
# - SystemdServiceManager : implémentation concrète de ServiceManager
# - Méthodes de contrôle : start(), stop(), restart(), enable(), disable()
#   - Utilisent subprocess.run avec systemctl
#   - Lèvent ServiceNotFoundError (code 5) ou ServiceControlError
# - Méthodes de requête : status(), is_active(), is_enabled()
#   - status() parse la sortie de systemctl status
#   - is_active() utilise systemctl is-active
#   - is_enabled() utilise systemctl is-enabled
# - Méthodes de parsing : _parse_enabled(), _parse_state(), _parse_sub_state()
#   - Extraient les informations de la sortie texte de systemctl
# - is_available() : vérifie que systemctl est présent et fonctionnel
# - Gestion des erreurs : toutes les méthodes capturent FileNotFoundError
#   et le convertissent en ServiceControlError
# Comment il sera utilisé (aperçu) :
# - infrastructure/backends/service_manager/detector.py détectera systemd
# - infrastructure/probe/service_probe.py instanciera SystemdServiceManager
# - application/commands/ utilisera l'interface ServiceManager (pas cette classe)
# - Les tests mockeront cette classe pour simuler différents états de service
#---------------------------------------------------------------------->
