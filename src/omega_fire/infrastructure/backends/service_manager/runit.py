# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Runit service manager implementation.

Implements the ServiceManager interface for runit-based systems.
Uses sv commands to control services.

This module performs real system I/O (subprocess calls) and is therefore
in infrastructure/. It implements the ServiceManager contract defined
in adapter.py.
"""
import subprocess
from pathlib import Path
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


class RunitServiceManager(ServiceManager):
    """Runit implementation of the ServiceManager interface.
    
    Uses sv commands to control services on runit-based systems.
    Runit is commonly used on Void Linux and some minimal distributions.
    """
    
    def __init__(self, service_dir: str = "/etc/sv"):
        """Initialize the runit service manager.
        
        Args:
            service_dir: Directory where runit services are defined (default: /etc/sv)
        """
        self._sv_bin = "sv"
        self._service_dir = service_dir
        self._run_dir = "/var/service"  # Where services are symlinked to be active
    
    def get_type(self) -> ServiceManagerType:
        """Get the type of service manager.
        
        Returns:
            ServiceManagerType.RUNIT
        """
        return ServiceManagerType.RUNIT
    
    def start(self, service_name: str) -> bool:
        """Start a service using sv up.
        
        Args:
            service_name: Name of the service to start
        
        Returns:
            True if the service was started successfully
        
        Raises:
            ServiceNotFoundError: If the service does not exist
            ServiceControlError: If the start operation fails
        """
        service_path = self._get_service_path(service_name)
        
        try:
            result = subprocess.run(
                [self._sv_bin, "up", service_path],
                capture_output=True,
                text=True,
                check=False,
            )
            
            if result.returncode == 0:
                return True
            elif "fail" in result.stderr.lower() or "not found" in result.stderr.lower():
                raise ServiceNotFoundError(
                    service_name=service_name,
                    manager_type="runit",
                )
            else:
                raise ServiceControlError(
                    service_name=service_name,
                    operation="start",
                    reason=result.stderr.strip() or f"Exit code {result.returncode}",
                    manager_type="runit",
                )
        
        except FileNotFoundError:
            raise ServiceControlError(
                service_name=service_name,
                operation="start",
                reason="sv binary not found",
                manager_type="runit",
            )
    
    def stop(self, service_name: str) -> bool:
        """Stop a service using sv down.
        
        Args:
            service_name: Name of the service to stop
        
        Returns:
            True if the service was stopped successfully
        
        Raises:
            ServiceNotFoundError: If the service does not exist
            ServiceControlError: If the stop operation fails
        """
        service_path = self._get_service_path(service_name)
        
        try:
            result = subprocess.run(
                [self._sv_bin, "down", service_path],
                capture_output=True,
                text=True,
                check=False,
            )
            
            if result.returncode == 0:
                return True
            elif "fail" in result.stderr.lower() or "not found" in result.stderr.lower():
                raise ServiceNotFoundError(
                    service_name=service_name,
                    manager_type="runit",
                )
            else:
                raise ServiceControlError(
                    service_name=service_name,
                    operation="stop",
                    reason=result.stderr.strip() or f"Exit code {result.returncode}",
                    manager_type="runit",
                )
        
        except FileNotFoundError:
            raise ServiceControlError(
                service_name=service_name,
                operation="stop",
                reason="sv binary not found",
                manager_type="runit",
            )
    
    def restart(self, service_name: str) -> bool:
        """Restart a service using sv restart.
        
        Args:
            service_name: Name of the service to restart
        
        Returns:
            True if the service was restarted successfully
        
        Raises:
            ServiceNotFoundError: If the service does not exist
            ServiceControlError: If the restart operation fails
        """
        service_path = self._get_service_path(service_name)
        
        try:
            result = subprocess.run(
                [self._sv_bin, "restart", service_path],
                capture_output=True,
                text=True,
                check=False,
            )
            
            if result.returncode == 0:
                return True
            elif "fail" in result.stderr.lower() or "not found" in result.stderr.lower():
                raise ServiceNotFoundError(
                    service_name=service_name,
                    manager_type="runit",
                )
            else:
                raise ServiceControlError(
                    service_name=service_name,
                    operation="restart",
                    reason=result.stderr.strip() or f"Exit code {result.returncode}",
                    manager_type="runit",
                )
        
        except FileNotFoundError:
            raise ServiceControlError(
                service_name=service_name,
                operation="restart",
                reason="sv binary not found",
                manager_type="runit",
            )
    
    def enable(self, service_name: str) -> bool:
        """Enable a service by creating a symlink in /var/service.
        
        In runit, enabling a service means creating a symlink from
        /var/service/<service> to /etc/sv/<service>.
        
        Args:
            service_name: Name of the service to enable
        
        Returns:
            True if the service was enabled successfully
        
        Raises:
            ServiceNotFoundError: If the service does not exist
            ServiceControlError: If the enable operation fails
        """
        service_path = self._get_service_path(service_name)
        run_path = Path(self._run_dir) / service_name
        
        try:
            # Check if service exists
            if not Path(service_path).exists():
                raise ServiceNotFoundError(
                    service_name=service_name,
                    manager_type="runit",
                )
            
            # Create symlink if it doesn't exist
            if not run_path.exists():
                run_path.symlink_to(service_path)
            
            return True
        
        except PermissionError as e:
            raise ServiceControlError(
                service_name=service_name,
                operation="enable",
                reason=f"Permission denied: {e}",
                manager_type="runit",
            )
        except OSError as e:
            raise ServiceControlError(
                service_name=service_name,
                operation="enable",
                reason=f"Failed to create symlink: {e}",
                manager_type="runit",
            )
    
    def disable(self, service_name: str) -> bool:
        """Disable a service by removing the symlink from /var/service.
        
        In runit, disabling a service means removing the symlink from
        /var/service/<service>.
        
        Args:
            service_name: Name of the service to disable
        
        Returns:
            True if the service was disabled successfully
        
        Raises:
            ServiceNotFoundError: If the service does not exist
            ServiceControlError: If the disable operation fails
        """
        run_path = Path(self._run_dir) / service_name
        
        try:
            # Remove symlink if it exists
            if run_path.exists() or run_path.is_symlink():
                run_path.unlink()
            
            return True
        
        except PermissionError as e:
            raise ServiceControlError(
                service_name=service_name,
                operation="disable",
                reason=f"Permission denied: {e}",
                manager_type="runit",
            )
        except OSError as e:
            raise ServiceControlError(
                service_name=service_name,
                operation="disable",
                reason=f"Failed to remove symlink: {e}",
                manager_type="runit",
            )
    
    def status(self, service_name: str) -> ServiceStatus:
        """Get the status of a service using sv status.
        
        Args:
            service_name: Name of the service to query
        
        Returns:
            ServiceStatus object with current status
        
        Raises:
            ServiceNotFoundError: If the service does not exist
            ServiceStatusError: If the status query fails
        """
        service_path = self._get_service_path(service_name)
        
        try:
            result = subprocess.run(
                [self._sv_bin, "status", service_path],
                capture_output=True,
                text=True,
                check=False,
            )
            
            if "fail" in result.stderr.lower() or "not found" in result.stderr.lower():
                raise ServiceNotFoundError(
                    service_name=service_name,
                    manager_type="runit",
                )
            
            # Parse the output to extract status information
            active, state, sub_state = self._parse_status_output(result.stdout)
            enabled = self.is_enabled(service_name)
            
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
                reason="sv binary not found",
                manager_type="runit",
            )
    
    def is_active(self, service_name: str) -> bool:
        """Check if a service is active using sv status.
        
        Args:
            service_name: Name of the service to check
        
        Returns:
            True if the service is active
        """
        service_path = self._get_service_path(service_name)
        
        try:
            result = subprocess.run(
                [self._sv_bin, "status", service_path],
                capture_output=True,
                text=True,
                check=False,
            )
            
            # sv status returns 0 and outputs "run:" if the service is running
            return result.returncode == 0 and "run:" in result.stdout
        
        except (FileNotFoundError, subprocess.SubprocessError):
            return False
    
    def is_enabled(self, service_name: str) -> bool:
        """Check if a service is enabled by checking for symlink in /var/service.
        
        Args:
            service_name: Name of the service to check
        
        Returns:
            True if the service is enabled (symlink exists)
        """
        run_path = Path(self._run_dir) / service_name
        return run_path.exists() or run_path.is_symlink()
    
    def is_available(self) -> bool:
        """Check if runit is available on the system.
        
        Returns:
            True if sv is available
        """
        try:
            result = subprocess.run(
                [self._sv_bin],
                capture_output=True,
                text=True,
                check=False,
            )
            # sv without arguments returns 1 but shows usage
            return result.returncode in (0, 1)
        except (FileNotFoundError, subprocess.SubprocessError):
            return False
    
    def _get_service_path(self, service_name: str) -> str:
        """Get the full path to a service directory.
        
        Args:
            service_name: Name of the service
        
        Returns:
            Full path to the service directory
        """
        return str(Path(self._service_dir) / service_name)
    
    def _parse_status_output(self, output: str) -> tuple[bool, str, str]:
        """Parse the status output from sv status.
        
        Args:
            output: Output from sv status
        
        Returns:
            Tuple of (active, state, sub_state)
        """
        # sv status output format: "run: service_name: (pid 1234) 12345s; run: log: (pid 5678) 12345s"
        # or "down: service_name: 1s, normally up; run: log: (pid 5678) 12345s"
        
        if "run:" in output:
            return True, "run", "running"
        elif "down:" in output:
            return False, "down", "stopped"
        elif "finish:" in output:
            return False, "finish", "finished"
        
        return False, "unknown", "unknown"


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Implémente l'interface ServiceManager pour les systèmes runit (Void Linux)
# - Utilise la commande sv pour contrôler les services
# - Gère l'activation/désactivation via des symlinks dans /var/service
# - Parse la sortie de sv pour extraire les informations de statut
# Pourquoi dans infrastructure/ (charte) :
# - C'est une implémentation concrète qui fait des appels système réels
#   (subprocess.run avec sv, manipulation de symlinks)
# - Implémente le contrat ServiceManager défini dans adapter.py
# - L'application/ ne dépend que de l'interface, pas de cette implémentation
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier (pas de règles firewall/fail2ban)
# ❌ Pas de dépendance vers domain/ ou interfaces/
# ❌ Pas d'appels directs depuis l'UI ou les cas d'usage
# Points clés :
# - RunitServiceManager : implémentation concrète de ServiceManager
# - Paramètre service_dir : répertoire des services (défaut: /etc/sv)
# - Paramètre run_dir : répertoire des services actifs (défaut: /var/service)
# - Méthodes de contrôle : start(), stop(), restart()
#   - Utilisent subprocess.run avec sv up/down/restart
#   - Lèvent ServiceNotFoundError ou ServiceControlError
# - Méthodes enable()/disable() : créent/suppriment des symlinks
#   - enable() : symlink de /var/service/<service> vers /etc/sv/<service>
#   - disable() : supprime le symlink
# - Méthodes de requête : status(), is_active(), is_enabled()
#   - status() parse la sortie de sv status
#   - is_active() vérifie si "run:" est dans la sortie
#   - is_enabled() vérifie si le symlink existe dans /var/service
# - _parse_status_output() : extrait (active, state, sub_state) de la sortie
# - is_available() : vérifie que sv est présent
# - Différences avec systemd/openrc :
#   - sv au lieu de systemctl/rc-service
#   - Activation via symlinks au lieu de commandes dédiées
#   - Parsing plus simple de la sortie
# Comment il sera utilisé (aperçu) :
# - infrastructure/backends/service_manager/detector.py détectera runit
# - infrastructure/probe/service_probe.py instanciera RunitServiceManager
# - application/commands/ utilisera l'interface ServiceManager (pas cette classe)
# - Les tests mockeront cette classe pour simuler différents états de service
#---------------------------------------------------------------------->
