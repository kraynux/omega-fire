# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Service manager exceptions.

Technical exceptions specific to the service manager subsystem.
These express failures in detecting or controlling system services
(systemd, openrc, runit). They are caught by the application layer
and translated into capability status updates in the registry.
"""
from omega_fire.core.exceptions import CoreError


class ServiceManagerError(CoreError):
    """Base exception for service manager operations.
    
    All service manager-specific exceptions inherit from this class.
    """
    def __init__(self, message: str, manager_type: str = None, context: dict = None):
        super().__init__(message, context)
        self.manager_type = manager_type
        if manager_type:
            self.context["manager_type"] = manager_type


class NoServiceManagerDetectedError(ServiceManagerError):
    """Raised when no service manager is detected on the system.
    
    This is a non-fatal error: the application can still function,
    but service control operations (start/stop/enable) will be unavailable.
    """
    def __init__(self, context: dict = None):
        super().__init__(
            "No service manager detected on this system",
            manager_type=None,
            context=context,
        )


class ServiceManagerDetectionError(ServiceManagerError):
    """Raised when service manager detection fails.
    
    This is raised when the detection process encounters an unexpected
    error (permission denied, filesystem issue, etc.).
    """
    def __init__(self, reason: str, manager_type: str = None, context: dict = None):
        super().__init__(
            f"Service manager detection failed: {reason}",
            manager_type=manager_type,
            context=context,
        )
        self.reason = reason


class ServiceNotFoundError(ServiceManagerError):
    """Raised when a requested service is not found.
    
    This is raised when trying to control a service that does not exist
    in the service manager's registry.
    """
    def __init__(self, service_name: str, manager_type: str = None, context: dict = None):
        super().__init__(
            f"Service '{service_name}' not found",
            manager_type=manager_type,
            context={**(context or {}), "service_name": service_name},
        )
        self.service_name = service_name


class ServiceControlError(ServiceManagerError):
    """Raised when a service control operation fails.
    
    This is raised when start/stop/restart/enable/disable operations
    fail at the system level.
    """
    def __init__(
        self,
        service_name: str,
        operation: str,
        reason: str,
        manager_type: str = None,
        context: dict = None,
    ):
        super().__init__(
            f"Failed to {operation} service '{service_name}': {reason}",
            manager_type=manager_type,
            context={
                **(context or {}),
                "service_name": service_name,
                "operation": operation,
                "reason": reason,
            },
        )
        self.service_name = service_name
        self.operation = operation
        self.reason = reason


class ServiceStatusError(ServiceManagerError):
    """Raised when retrieving service status fails.
    
    This is raised when the status query cannot be completed
    (service manager not responding, permission denied, etc.).
    """
    def __init__(
        self,
        service_name: str,
        reason: str,
        manager_type: str = None,
        context: dict = None,
    ):
        super().__init__(
            f"Failed to get status of service '{service_name}': {reason}",
            manager_type=manager_type,
            context={
                **(context or {}),
                "service_name": service_name,
                "reason": reason,
            },
        )
        self.service_name = service_name
        self.reason = reason


class UnsupportedServiceManagerError(ServiceManagerError):
    """Raised when an unsupported service manager is encountered.
    
    This is raised when the detected service manager is not one of
    the supported types (systemd, openrc, runit).
    """
    def __init__(self, detected_type: str, context: dict = None):
        super().__init__(
            f"Unsupported service manager type: {detected_type}",
            manager_type=detected_type,
            context=context,
        )
        self.detected_type = detected_type


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit les exceptions techniques spécifiques au sous-domaine service_manager.
#   Ces exceptions expriment des pannes ou limitations techniques liées à la
#   détection et au contrôle des gestionnaires de services (systemd, openrc, runit).
# Pourquoi dans infrastructure/ (charte) :
# - Ce sont des erreurs techniques, pas des règles métier
# - Elles encapsulent les pannes système (commande échouée, service introuvable)
# - Elles héritent de CoreError (exception transverse) pour être capturées
#   uniformément par application/
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier (pas de règles firewall/fail2ban)
# ❌ Pas d'appels système (juste des définitions d'exceptions)
# ❌ Pas de dépendance vers domain/ ou interfaces/
# Points clés :
# - Hiérarchie claire : toutes les exceptions héritent de ServiceManagerError
# - 6 exceptions ciblées :
#   - NoServiceManagerDetectedError : aucun gestionnaire détecté (non-fatal)
#   - ServiceManagerDetectionError : échec de la détection
#   - ServiceNotFoundError : service demandé introuvable
#   - ServiceControlError : échec d'une opération (start/stop/restart)
#   - ServiceStatusError : échec de la requête de statut
#   - UnsupportedServiceManagerError : type de gestionnaire non supporté
# - Contexte riche : chaque exception stocke les données pertinentes
#   (manager_type, service_name, operation, reason)
# Comment elles seront utilisées (aperçu) :
# - infrastructure/backends/service_manager/detector.py les lèvera lors de la détection
# - infrastructure/backends/service_manager/systemd.py les lèvera lors du contrôle
# - application/pipeline/guards/ les capturera pour mettre à jour le registre
#---------------------------------------------------------------------->
