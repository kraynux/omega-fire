# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Contrat pour les interactions système (services, commandes, permissions)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class ServiceStatus(str, Enum):
    """Statut d'un service système."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ServiceInfo:
    """Informations sur un service système.

    Attributs:
        name: nom du service.
        status: statut actuel (active, inactive, failed, unknown).
        enabled: True si le service est activé au démarrage.
        manager: gestionnaire de services (systemd, openrc, runit).
        pid: PID du processus (None si inactif).
        uptime: durée de fonctionnement en secondes (None si inactif).
    """
    name: str
    status: ServiceStatus
    enabled: bool
    manager: str
    pid: int | None = None
    uptime: int | None = None


@dataclass(frozen=True, slots=True)
class CommandResult:
    """Résultat d'une commande système.

    Attributs:
        return_code: code de retour (0 = succès).
        stdout: sortie standard.
        stderr: sortie d'erreur.
        command: commande exécutée.
    """
    return_code: int
    stdout: str
    stderr: str
    command: str


class SystemPort(Protocol):
    """Contrat pour les interactions système.

    Définit les opérations attendues pour gérer les services,
    exécuter des commandes et vérifier les permissions.
    """

    @abstractmethod
    def get_service_status(self, service_name: str) -> ServiceInfo:
        """Récupère le statut d'un service.

        Args:
            service_name: nom du service.

        Returns:
            ServiceInfo avec statut, enabled, manager, pid, uptime.

        Raises:
            ServiceNotFoundError: si le service n'existe pas.
        """
        ...

    @abstractmethod
    def start_service(self, service_name: str) -> None:
        """Démarre un service.

        Args:
            service_name: nom du service.

        Raises:
            ServiceControlError: si le démarrage échoue.
        """
        ...

    @abstractmethod
    def stop_service(self, service_name: str) -> None:
        """Arrête un service.

        Args:
            service_name: nom du service.

        Raises:
            ServiceControlError: si l'arrêt échoue.
        """
        ...

    @abstractmethod
    def restart_service(self, service_name: str) -> None:
        """Redémarre un service.

        Args:
            service_name: nom du service.

        Raises:
            ServiceControlError: si le redémarrage échoue.
        """
        ...

    @abstractmethod
    def enable_service(self, service_name: str) -> None:
        """Active un service au démarrage.

        Args:
            service_name: nom du service.

        Raises:
            ServiceControlError: si l'activation échoue.
        """
        ...

    @abstractmethod
    def disable_service(self, service_name: str) -> None:
        """Désactive un service au démarrage.

        Args:
            service_name: nom du service.

        Raises:
            ServiceControlError: si la désactivation échoue.
        """
        ...

    @abstractmethod
    def run_command(
        self,
        command: list[str],
        *,
        check: bool = False,
        timeout: float | None = None,
    ) -> CommandResult:
        """Exécute une commande système.

        Args:
            command: commande à exécuter (liste d'arguments).
            check: si True, lève une erreur si le code de retour != 0.
            timeout: timeout en secondes (None = pas de timeout).

        Returns:
            CommandResult avec return_code, stdout, stderr, command.

        Raises:
            CommandTimeoutError: si le timeout est dépassé.
            CommandError: si check=True et return_code != 0.
        """
        ...

    @abstractmethod
    def check_permission(self, permission: str) -> bool:
        """Vérifie si une permission est disponible.

        Args:
            permission: nom de la permission (ex: "root", "network_admin").

        Returns:
            True si la permission est disponible.
        """
        ...

    @abstractmethod
    def get_system_info(self) -> dict[str, str]:
        """Récupère les informations système.

        Returns:
            Dictionnaire avec os, kernel, hostname, uptime, etc.
        """
        ...

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit le contrat (Protocol) pour les interactions système.
# - Fournit ServiceInfo, CommandResult (dataclasses frozen), ServiceStatus (enum).
# - Spécifie les opérations : get_service_status(), start_service(), stop_service(),
#   restart_service(), enable_service(), disable_service(), run_command(),
#   check_permission(), get_system_info().
#
# Pourquoi dans ports/ (charte) :
# - C'est un contrat attendu par le cœur applicatif (application/pipeline/guards/)
# - Pas d'implémentation concrète (c'est le rôle de infrastructure/backends/service_manager/)
# - Aucune dépendance vers domain/, application/, infrastructure/, interfaces/
#
# Ce qu'il ne contient PAS :
# ❌ Pas d'implémentation concrète (appels systemctl, rc-service)
# ❌ Pas d'import depuis domain/
# ❌ Pas d'import depuis application/
# ❌ Pas d'import depuis infrastructure/
# ❌ Pas d'import depuis interfaces/
# ❌ Pas de logique de détection de service manager (c'est infrastructure/probe/)
#
# Points clés :
# - ServiceStatus : enum (active, inactive, failed, unknown)
# - ServiceInfo : dataclass frozen avec name, status, enabled, manager, pid, uptime
# - CommandResult : dataclass frozen avec return_code, stdout, stderr, command
# - SystemPort : Protocol définissant toutes les opérations système
# - Toutes les méthodes sont abstraites (via Protocol)
#
# Comment il sera utilisé (aperçu) :
# - application/pipeline/guards/permission_guard.py appellera system_port.check_permission()
# - infrastructure/backends/service_manager/ implémentera SystemPort
# - infrastructure/probe/ utilisera SystemPort pour détecter les services
# - interfaces/cli/actions.py appellera system_port.get_service_status() pour diagnostics
#---------------------------------------------------------------------->       
