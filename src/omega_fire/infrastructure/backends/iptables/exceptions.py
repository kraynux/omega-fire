# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Iptables backend exceptions.

Technical exceptions specific to the iptables backend.
These express failures in iptables command execution, parsing,
or configuration. They are caught by the application layer
and translated into stable error messages.
"""
from omega_fire.core.exceptions import CoreError


class IptablesError(CoreError):
    """Base exception for iptables operations."""
    def __init__(self, message: str, context: dict = None):
        super().__init__(message, context)


class IptCommandError(IptablesError):
    """Raised when an iptables command fails."""
    def __init__(self, command: str, returncode: int, stderr: str, context: dict = None):
        super().__init__(
            f"iptables command failed (exit {returncode}): {command}",
            {**(context or {}), "command": command, "returncode": returncode, "stderr": stderr},
        )
        self.command = command
        self.returncode = returncode
        self.stderr = stderr


class IptParseError(IptablesError):
    """Raised when iptables output cannot be parsed."""
    def __init__(self, reason: str, raw_output: str = "", context: dict = None):
        super().__init__(
            f"Failed to parse iptables output: {reason}",
            {**(context or {}), "reason": reason},
        )
        self.reason = reason
        self.raw_output = raw_output


class IptChainNotFoundError(IptablesError):
    """Raised when a referenced iptables chain does not exist."""
    def __init__(self, chain_name: str, table: str = "filter", context: dict = None):
        super().__init__(
            f"iptables chain '{chain_name}' not found in table '{table}'",
            {**(context or {}), "chain_name": chain_name, "table": table},
        )
        self.chain_name = chain_name
        self.table = table


class IptRuleNotFoundError(IptablesError):
    """Raised when a referenced iptables rule does not exist."""
    def __init__(self, rule_num: int, chain_name: str = "", context: dict = None):
        super().__init__(
            f"iptables rule #{rule_num} not found in chain '{chain_name}'",
            {**(context or {}), "rule_num": rule_num, "chain_name": chain_name},
        )
        self.rule_num = rule_num
        self.chain_name = chain_name


class IptPermissionError(IptablesError):
    """Raised when iptables operations require elevated privileges."""
    def __init__(self, operation: str, context: dict = None):
        super().__init__(
            f"Permission denied for iptables operation: {operation}. Run as root.",
            {**(context or {}), "operation": operation},
        )
        self.operation = operation


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit les exceptions techniques spécifiques au backend iptables.
#   Miroir de nftables/exceptions.py mais pour iptables.
# Pourquoi dans infrastructure/ (charte) :
# - Ce sont des erreurs techniques, pas des règles métier
# - Elles encapsulent les pannes système (commande échouée, chaîne introuvable)
# - Elles héritent de CoreError pour être capturées uniformément
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier, pas d'appels système, pas de dépendances externes
# Points clés :
# - Hiérarchie : IptablesError → CoreError → Exception
# - 5 exceptions : IptCommandError, IptParseError, IptChainNotFoundError,
#   IptRuleNotFoundError, IptPermissionError
# - Différence avec nftables : iptables utilise des numéros de règle (rule_num)
#   au lieu de handles, et des tables/chaînes au lieu de familles
# Comment elles seront utilisées (aperçu) :
# - infrastructure/backends/iptables/adapter.py les lèvera lors des opérations
# - application/pipeline/ les capturera via les ports
#---------------------------------------------------------------------->
