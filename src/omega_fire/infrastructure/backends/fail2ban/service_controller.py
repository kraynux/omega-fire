# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Fail2ban service controller.

Controls the fail2ban service lifecycle (start, stop, restart, enable, disable)
using the detected service manager (systemd, openrc, runit).

This module uses the ServiceManager adapter to perform service operations.
"""
from omega_fire.infrastructure.backends.service_manager.detector import ServiceManagerDetector
from omega_fire.infrastructure.backends.service_manager.adapter import ServiceManager
from omega_fire.infrastructure.backends.service_manager.systemd import SystemdServiceManager
from omega_fire.infrastructure.backends.service_manager.openrc import OpenRCServiceManager
from omega_fire.infrastructure.backends.service_manager.runit import RunitServiceManager
from omega_fire.infrastructure.backends.service_manager.exceptions import (
    NoServiceManagerDetectedError,
    ServiceNotFoundError,
    ServiceControlError,
)
from omega_fire.infrastructure.backends.fail2ban.exceptions import (
    Fail2banServiceError,
)
from omega_fire.core.enums import ServiceManagerType


class Fail2banServiceController:
    """Controls the fail2ban service using the detected service manager."""

    def __init__(self):
        """Initialize the service controller."""
        self._detector = ServiceManagerDetector()
        self._manager: ServiceManager = None

    def _get_manager(self) -> ServiceManager:
        """Get the appropriate service manager adapter.

        Returns:
            ServiceManager instance

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

    def start(self) -> bool:
        """Start the fail2ban service.

        Returns:
            True if the service was started successfully

        Raises:
            Fail2banServiceError: If the operation fails
        """
        try:
            manager = self._get_manager()
            return manager.start("fail2ban")
        except (NoServiceManagerDetectedError, ServiceNotFoundError, ServiceControlError) as e:
            raise Fail2banServiceError(operation="start", reason=str(e)) from e

    def stop(self) -> bool:
        """Stop the fail2ban service.

        Returns:
            True if the service was stopped successfully

        Raises:
            Fail2banServiceError: If the operation fails
        """
        try:
            manager = self._get_manager()
            return manager.stop("fail2ban")
        except (NoServiceManagerDetectedError, ServiceNotFoundError, ServiceControlError) as e:
            raise Fail2banServiceError(operation="stop", reason=str(e)) from e

    def restart(self) -> bool:
        """Restart the fail2ban service.

        Returns:
            True if the service was restarted successfully

        Raises:
            Fail2banServiceError: If the operation fails
        """
        try:
            manager = self._get_manager()
            return manager.restart("fail2ban")
        except (NoServiceManagerDetectedError, ServiceNotFoundError, ServiceControlError) as e:
            raise Fail2banServiceError(operation="restart", reason=str(e)) from e

    def enable(self) -> bool:
        """Enable the fail2ban service to start at boot.

        Returns:
            True if the service was enabled successfully

        Raises:
            Fail2banServiceError: If the operation fails
        """
        try:
            manager = self._get_manager()
            return manager.enable("fail2ban")
        except (NoServiceManagerDetectedError, ServiceNotFoundError, ServiceControlError) as e:
            raise Fail2banServiceError(operation="enable", reason=str(e)) from e

    def disable(self) -> bool:
        """Disable the fail2ban service from starting at boot.

        Returns:
            True if the service was disabled successfully

        Raises:
            Fail2banServiceError: If the operation fails
        """
        try:
            manager = self._get_manager()
            return manager.disable("fail2ban")
        except (NoServiceManagerDetectedError, ServiceNotFoundError, ServiceControlError) as e:
            raise Fail2banServiceError(operation="disable", reason=str(e)) from e

    def is_active(self) -> bool:
        """Check if the fail2ban service is currently active.

        Returns:
            True if the service is active
        """
        try:
            manager = self._get_manager()
            return manager.is_active("fail2ban")
        except (NoServiceManagerDetectedError, ServiceNotFoundError):
            return False

    def is_enabled(self) -> bool:
        """Check if the fail2ban service is enabled at boot.

        Returns:
            True if the service is enabled
        """
        try:
            manager = self._get_manager()
            return manager.is_enabled("fail2ban")
        except (NoServiceManagerDetectedError, ServiceNotFoundError):
            return False


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Contrôle le cycle de vie du service fail2ban (start/stop/restart/enable/disable)
# - Utilise le ServiceManager détecté (systemd/openrc/runit) pour exécuter les opérations
# - Sélectionne automatiquement l'adapter approprié selon le gestionnaire détecté
# Pourquoi dans infrastructure/ (charte) :
# - C'est une implémentation technique qui dépend du service manager
# - Implémente les contrats que l'application/ utilisera via les ports
# - L'application/ ne doit JAMAIS importer ce module directement
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier (pas de validation, pas de politiques)
# ❌ Pas de dépendance vers application/ ou interfaces/
# ❌ Pas d'appels directs aux commandes systemctl/rc-service/sv
# Points clés :
# - Fail2banServiceController : classe principale
# - _get_manager() : sélectionne l'adapter approprié (systemd/openrc/runit)
#   - Lève NoServiceManagerDetectedError si aucun gestionnaire détecté
# - start() / stop() / restart() : contrôle du service
# - enable() / disable() : activation/désactivation au boot
# - is_active() / is_enabled() : vérifications rapides
# - Toutes les méthodes capturent les exceptions du ServiceManager
#   et les convertissent en Fail2banServiceError
# - Composition : utilise ServiceManagerDetector et les adapters de service_manager/
# Comment il sera utilisé (aperçu) :
# - ports/fail2ban.py définira le contrat que ce controller implémente
# - app/bootstrap.py instanciera ce controller et l'injectera via les ports
# - application/commands/ utilisera le port (pas ce controller directement)
# - Les tests mockeront ServiceManager pour simuler différents états
#---------------------------------------------------------------------->
