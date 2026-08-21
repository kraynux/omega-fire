# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ip6tables backend exceptions.

Technical exceptions specific to the ip6tables backend.
These express failures in ip6tables command execution, parsing,
or configuration. They are caught by the application layer
and translated into stable error messages.
"""
from omega_fire.core.exceptions import CoreError


class Ip6tablesError(CoreError):
    """Base exception for ip6tables operations."""
    def __init__(self, message: str, context: dict = None):
        super().__init__(message, context)


class Ip6tCommandError(Ip6tablesError):
    """Raised when an ip6tables command fails."""
    def __init__(self, command: str, returncode: int, stderr: str, context: dict = None):
        super().__init__(
            f"ip6tables command failed (exit {returncode}): {command}",
            {**(context or {}), "command": command, "returncode": returncode, "stderr": stderr},
        )
        self.command = command
        self.returncode = returncode
        self.stderr = stderr


class Ip6tParseError(Ip6tablesError):
    """Raised when ip6tables output cannot be parsed."""
    def __init__(self, reason: str, raw_output: str = "", context: dict = None):
        super().__init__(
            f"Failed to parse ip6tables output: {reason}",
            {**(context or {}), "reason": reason},
        )
        self.reason = reason
        self.raw_output = raw_output


class Ip6tChainNotFoundError(Ip6tablesError):
    """Raised when a referenced ip6tables chain does not exist."""
    def __init__(self, chain_name: str, table: str = "filter", context: dict = None):
        super().__init__(
            f"ip6tables chain '{chain_name}' not found in table '{table}'",
            {**(context or {}), "chain_name": chain_name, "table": table},
        )
        self.chain_name = chain_name
        self.table = table


class Ip6tRuleNotFoundError(Ip6tablesError):
    """Raised when a referenced ip6tables rule does not exist."""
    def __init__(self, rule_num: int, chain_name: str = "", context: dict = None):
        super().__init__(
            f"ip6tables rule #{rule_num} not found in chain '{chain_name}'",
            {**(context or {}), "rule_num": rule_num, "chain_name": chain_name},
        )
        self.rule_num = rule_num
        self.chain_name = chain_name


class Ip6tPermissionError(Ip6tablesError):
    """Raised when ip6tables operations require elevated privileges."""
    def __init__(self, operation: str, context: dict = None):
        super().__init__(
            f"Permission denied for ip6tables operation: {operation}. Run as root.",
            {**(context or {}), "operation": operation},
        )
        self.operation = operation


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit les exceptions techniques spécifiques au backend ip6tables.
#   Miroir de iptables/exceptions.py mais pour ip6tables (plan IPv6 iptables,
#   référentiel §53, Phase A).
# Pourquoi dans infrastructure/ (charte) :
# - Ce sont des erreurs techniques, pas des règles métier
# - Elles encapsulent les pannes système (commande échouée, chaîne introuvable)
# - Elles héritent de CoreError pour être capturées uniformément
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier, pas d'appels système, pas de dépendances externes
# Points clés :
# - Hiérarchie : Ip6tablesError → CoreError → Exception
# - 5 exceptions : Ip6tCommandError, Ip6tParseError, Ip6tChainNotFoundError,
#   Ip6tRuleNotFoundError, Ip6tPermissionError
# - Classes distinctes de leurs homologues iptables (Ipt*) — ne pas fusionner :
#   backend séparé au sens de l'architecture (voir plan, décision "4e backend
#   indépendant").
# Comment elles seront utilisées (aperçu) :
# - infrastructure/backends/ip6tables/adapter.py les lèvera lors des opérations
# - application/pipeline/ les capturera via les ports
#---------------------------------------------------------------------->
