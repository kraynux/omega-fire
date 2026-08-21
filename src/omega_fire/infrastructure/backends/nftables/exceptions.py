# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Nftables backend exceptions.

Technical exceptions specific to the nftables backend.
These express failures in nftables command execution, parsing,
or configuration. They are caught by the application layer
and translated into stable error messages.
"""
from omega_fire.core.exceptions import CoreError


class NftablesError(CoreError):
    """Base exception for nftables operations."""
    def __init__(self, message: str, context: dict = None):
        super().__init__(message, context)


class NftCommandError(NftablesError):
    """Raised when an nft command fails."""
    def __init__(self, command: str, returncode: int, stderr: str, context: dict = None):
        super().__init__(
            f"nft command failed (exit {returncode}): {command}",
            {**(context or {}), "command": command, "returncode": returncode, "stderr": stderr},
        )
        self.command = command
        self.returncode = returncode
        self.stderr = stderr


class NftParseError(NftablesError):
    """Raised when nft output cannot be parsed."""
    def __init__(self, reason: str, raw_output: str = "", context: dict = None):
        super().__init__(
            f"Failed to parse nft output: {reason}",
            {**(context or {}), "reason": reason},
        )
        self.reason = reason
        self.raw_output = raw_output


class NftTableNotFoundError(NftablesError):
    """Raised when a referenced nft table does not exist."""
    def __init__(self, table_name: str, family: str = "inet", context: dict = None):
        super().__init__(
            f"nft table '{family} {table_name}' not found",
            {**(context or {}), "table_name": table_name, "family": family},
        )
        self.table_name = table_name
        self.family = family


class NftChainNotFoundError(NftablesError):
    """Raised when a referenced nft chain does not exist."""
    def __init__(self, chain_name: str, table_name: str = "", context: dict = None):
        super().__init__(
            f"nft chain '{chain_name}' not found in table '{table_name}'",
            {**(context or {}), "chain_name": chain_name, "table_name": table_name},
        )
        self.chain_name = chain_name
        self.table_name = table_name


class NftRuleNotFoundError(NftablesError):
    """Raised when a referenced nft rule handle does not exist."""
    def __init__(self, handle: int, chain_name: str = "", context: dict = None):
        super().__init__(
            f"nft rule handle {handle} not found in chain '{chain_name}'",
            {**(context or {}), "handle": handle, "chain_name": chain_name},
        )
        self.handle = handle
        self.chain_name = chain_name


class NftPermissionError(NftablesError):
    """Raised when nft operations require elevated privileges."""
    def __init__(self, operation: str, context: dict = None):
        super().__init__(
            f"Permission denied for nft operation: {operation}. Run as root.",
            {**(context or {}), "operation": operation},
        )
        self.operation = operation


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit les exceptions techniques spécifiques au backend nftables.
#   Ces exceptions expriment des pannes ou limitations techniques liées
#   aux commandes nft, au parsing de sortie et à la configuration.
# Pourquoi dans infrastructure/ (charte) :
# - Ce sont des erreurs techniques, pas des règles métier
# - Elles encapsulent les pannes système (commande échouée, table introuvable)
# - Elles héritent de CoreError pour être capturées uniformément
# - L'application/ les traduira en erreurs stables via le pipeline
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier (pas de règles de blacklist, politiques)
# ❌ Pas d'appels système (juste des définitions d'exceptions)
# ❌ Pas de dépendance vers domain/, application/ ou interfaces/
# Points clés :
# - Hiérarchie : NftablesError → CoreError → Exception
# - 6 exceptions ciblées :
#   - NftCommandError : commande nft échouée (command, returncode, stderr)
#   - NftParseError : parsing de sortie échoué (reason, raw_output)
#   - NftTableNotFoundError : table inexistante (table_name, family)
#   - NftChainNotFoundError : chaîne inexistante (chain_name, table_name)
#   - NftRuleNotFoundError : règle inexistante (handle, chain_name)
#   - NftPermissionError : privilèges insuffisants (operation)
# - Contexte riche : chaque exception stocke les données pertinentes
# Comment elles seront utilisées (aperçu) :
# - infrastructure/backends/nftables/adapter.py les lèvera lors des opérations
# - infrastructure/backends/nftables/parser.py les lèvera lors du parsing
# - application/pipeline/ les capturera via les ports pour produire des Result
#---------------------------------------------------------------------->
