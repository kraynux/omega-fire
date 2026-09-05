# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Fail2ban service controller.

Controls the fail2ban service lifecycle (start, stop, restart, enable, disable)
using the detected service manager (systemd, openrc, runit).

This module uses the ServiceManager adapter to perform service operations.
"""
import os

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

# Chemin standard du log propre a fail2ban (logtarget par defaut de
# fail2ban.conf sur toutes les distributions majeures) — distinct du
# logpath d'une jail (le fichier qu'une jail SURVEILLE, deja gere par
# infrastructure/backends/fail2ban/adapter.py::create_jail(), qui recree
# deja ce fichier s'il est absent avant d'ecrire la config de la jail).
# Ce fichier-ci est celui que le DAEMON fail2ban lui-meme ecrit — s'il a
# ete supprime (ex. rotation/purge de logs), fail2ban ne le recree jamais
# tout seul et refuse alors de (re)demarrer (bug reel rapporte : "stoppe
# le service fail2ban depuis l'interface, impossible a redemarrer").
FAIL2BAN_LOG_PATH = "/var/log/fail2ban.log"


class Fail2banServiceController:
    """Controls the fail2ban service using the detected service manager."""

    def __init__(self):
        """Initialize the service controller."""
        self._detector = ServiceManagerDetector()
        self._manager: ServiceManager = None

    def _ensure_log_file_exists(self) -> None:
        """Recree un fichier vide a FAIL2BAN_LOG_PATH s'il est absent,
        avant de (re)demarrer le service — meme motif defensif deja
        applique a un logpath de jail dans adapter.py::create_jail()
        (creation du dossier parent si besoin, puis fichier vide via
        open(...).close()). Jamais bloquant : une erreur ici (permissions
        insuffisantes, etc.) est ignoree silencieusement, le start/restart
        sous-jacent echouera de toute facon avec un message clair si le
        fichier manque toujours."""
        try:
            log_dir = os.path.dirname(FAIL2BAN_LOG_PATH)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
            if not os.path.exists(FAIL2BAN_LOG_PATH):
                open(FAIL2BAN_LOG_PATH, "a", encoding="utf-8").close()
        except OSError:
            pass

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
        self._ensure_log_file_exists()
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
        self._ensure_log_file_exists()
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
# - start()/restart() appellent _ensure_log_file_exists() en premier
#   (bug réel corrigé le 2026-09-04, rapporté par l'utilisateur : "stoppe
#   fail2ban depuis l'interface, impossible à redémarrer — pas de fichier
#   log suite à suppression, fail2ban ne le recrée pas automatiquement").
#   Même motif défensif que adapter.py::create_jail() pour le logpath
#   d'une jail, appliqué ici au log PROPRE de fail2ban (FAIL2BAN_LOG_PATH,
#   /var/log/fail2ban.log) — jamais bloquant si la création échoue, le
#   start/restart sous-jacent produit alors son propre message d'erreur.
# - Composition : utilise ServiceManagerDetector et les adapters de service_manager/
# Comment il sera utilisé (aperçu) :
# - ports/fail2ban.py définira le contrat que ce controller implémente
# - app/bootstrap.py instanciera ce controller et l'injectera via les ports
# - application/commands/ utilisera le port (pas ce controller directement)
# - Les tests mockeront ServiceManager pour simuler différents états
#---------------------------------------------------------------------->
