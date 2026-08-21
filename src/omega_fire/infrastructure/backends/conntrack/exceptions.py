# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Conntrack backend exceptions.

Technical exceptions specific to the conntrack backend.
These express failures in conntrack command execution or parsing.
They are caught by the application layer and translated into stable error messages.
"""
from omega_fire.core.exceptions import CoreError


class ConntrackError(CoreError):
    """Base exception for conntrack operations."""
    def __init__(self, message: str, context: dict = None):
        super().__init__(message, context)


class ConntrackCommandError(ConntrackError):
    """Raised when a conntrack command fails."""
    def __init__(self, command: str, returncode: int, stderr: str, context: dict = None):
        super().__init__(
            f"conntrack command failed (exit {returncode}): {command}",
            {**(context or {}), "command": command, "returncode": returncode, "stderr": stderr},
        )
        self.command = command
        self.returncode = returncode
        self.stderr = stderr


class ConntrackParseError(ConntrackError):
    """Raised when conntrack output cannot be parsed."""
    def __init__(self, reason: str, raw_output: str = "", context: dict = None):
        super().__init__(
            f"Failed to parse conntrack output: {reason}",
            {**(context or {}), "reason": reason},
        )
        self.reason = reason
        self.raw_output = raw_output


class ConntrackPermissionError(ConntrackError):
    """Raised when conntrack operations require elevated privileges."""
    def __init__(self, operation: str, context: dict = None):
        super().__init__(
            f"Permission denied for conntrack operation: {operation}. Run as root.",
            {**(context or {}), "operation": operation},
        )
        self.operation = operation


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit les exceptions techniques spécifiques au backend conntrack.
#   Ces exceptions expriment des pannes ou limitations techniques liées
#   aux commandes conntrack et au parsing de sortie.
# Pourquoi dans infrastructure/ (charte) :
# - Ce sont des erreurs techniques, pas des règles métier
# - Elles encapsulent les pannes système (commande échouée, parsing impossible)
# - Elles héritent de CoreError pour être capturées uniformément
# - L'application/ les traduira en erreurs stables via le pipeline
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier (pas de filtrage de connexions, pas de politiques)
# ❌ Pas d'appels système (juste des définitions d'exceptions)
# ❌ Pas de dépendance vers domain/, application/ ou interfaces/
# Points clés :
# - Hiérarchie : ConntrackError → CoreError → Exception
# - 3 exceptions ciblées :
#   - ConntrackCommandError : commande conntrack échouée (command, returncode, stderr)
#   - ConntrackParseError : parsing de sortie échoué (reason, raw_output)
#   - ConntrackPermissionError : privilèges insuffisants (operation)
# - Contexte riche : chaque exception stocke les données pertinentes
# Comment elles seront utilisées (aperçu) :
# - infrastructure/backends/conntrack/adapter.py les lèvera lors des opérations
# - application/pipeline/ les capturera via les ports
#---------------------------------------------------------------------->
