# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Fail2ban backend exceptions.

Technical exceptions specific to the fail2ban backend.
These express failures in fail2ban-client command execution, parsing,
or jail management. They are caught by the application layer
and translated into stable error messages.
"""
from omega_fire.core.exceptions import CoreError


class Fail2banError(CoreError):
    """Base exception for fail2ban operations."""
    def __init__(self, message: str, context: dict = None):
        super().__init__(message, context)


class Fail2banCommandError(Fail2banError):
    """Raised when a fail2ban-client command fails."""
    def __init__(self, command: str, returncode: int, stderr: str, context: dict = None):
        super().__init__(
            f"fail2ban-client command failed (exit {returncode}): {command}",
            {**(context or {}), "command": command, "returncode": returncode, "stderr": stderr},
        )
        self.command = command
        self.returncode = returncode
        self.stderr = stderr


class Fail2banParseError(Fail2banError):
    """Raised when fail2ban-client output cannot be parsed."""
    def __init__(self, reason: str, raw_output: str = "", context: dict = None):
        super().__init__(
            f"Failed to parse fail2ban-client output: {reason}",
            {**(context or {}), "reason": reason},
        )
        self.reason = reason
        self.raw_output = raw_output


class JailNotFoundError(Fail2banError):
    """Raised when a referenced jail does not exist."""
    def __init__(self, jail_name: str, context: dict = None):
        super().__init__(
            f"Fail2ban jail '{jail_name}' not found",
            {**(context or {}), "jail_name": jail_name},
        )
        self.jail_name = jail_name


class JailAlreadyExistsError(Fail2banError):
    """Raised when attempting to create a jail that already exists."""
    def __init__(self, jail_name: str, context: dict = None):
        super().__init__(
            f"Fail2ban jail '{jail_name}' already exists",
            {**(context or {}), "jail_name": jail_name},
        )
        self.jail_name = jail_name


class Fail2banServiceError(Fail2banError):
    """Raised when fail2ban service control fails."""
    def __init__(self, operation: str, reason: str, context: dict = None):
        super().__init__(
            f"Fail2ban service {operation} failed: {reason}",
            {**(context or {}), "operation": operation, "reason": reason},
        )
        self.operation = operation
        self.reason = reason


class Fail2banPermissionError(Fail2banError):
    """Raised when fail2ban operations require elevated privileges."""
    def __init__(self, operation: str, context: dict = None):
        super().__init__(
            f"Permission denied for fail2ban operation: {operation}. Run as root.",
            {**(context or {}), "operation": operation},
        )
        self.operation = operation


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit les exceptions techniques spécifiques au backend fail2ban.
#   Ces exceptions expriment des pannes ou limitations techniques liées
#   aux commandes fail2ban-client, au parsing de sortie et à la gestion des jails.
# Pourquoi dans infrastructure/ (charte) :
# - Ce sont des erreurs techniques, pas des règles métier
# - Elles encapsulent les pannes système (commande échouée, jail introuvable)
# - Elles héritent de CoreError pour être capturées uniformément
# - L'application/ les traduira en erreurs stables via le pipeline
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier (pas de règles de transfert, politiques de jail)
# ❌ Pas d'appels système (juste des définitions d'exceptions)
# ❌ Pas de dépendance vers domain/, application/ ou interfaces/
# Points clés :
# - Hiérarchie : Fail2banError → CoreError → Exception
# - 6 exceptions ciblées :
#   - Fail2banCommandError : commande fail2ban-client échouée
#   - Fail2banParseError : parsing de sortie échoué
#   - JailNotFoundError : jail inexistant
#   - JailAlreadyExistsError : jail déjà existant
#   - Fail2banServiceError : échec de contrôle du service
#   - Fail2banPermissionError : privilèges insuffisants
# - Contexte riche : chaque exception stocke les données pertinentes
# Comment elles seront utilisées (aperçu) :
# - infrastructure/backends/fail2ban/adapter.py les lèvera lors des opérations
# - infrastructure/backends/fail2ban/service_controller.py les lèvera pour le service
# - application/pipeline/ les capturera via les ports
#---------------------------------------------------------------------->
