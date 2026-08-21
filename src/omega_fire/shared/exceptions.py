# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)


"""Exceptions génériques partagées par les utilitaires transverses."""

from __future__ import annotations


class SharedError(Exception):
    """Base de toutes les erreurs issues du paquet shared/.

    Les sous-classes doivent rester purement techniques :
    erreurs de parsing, erreurs shell, erreurs de formatage.
    """


class ShellCommandError(SharedError):
    """Erreur levée lorsqu'une commande shell échoue.

    Attributs:
        command: commande exécutée (liste ou chaîne).
        return_code: code de retour du processus.
        stdout: sortie standard capturée (peut être vide).
        stderr: sortie d'erreur capturée (peut être vide).
    """

    def __init__(
        self,
        message: str,
        *,
        command: str | list[str] | None = None,
        return_code: int | None = None,
        stdout: str = "",
        stderr: str = "",
    ) -> None:
        super().__init__(message)
        self.command = command
        self.return_code = return_code
        self.stdout = stdout
        self.stderr = stderr

    def __str__(self) -> str:
        base = super().__str__()
        if self.command is not None:
            cmd = " ".join(self.command) if isinstance(self.command, list) else self.command
            base = f"{base} [cmd={cmd!r} rc={self.return_code}]"
        return base


class ParsingError(SharedError):
    """Erreur générique de parsing (regex, format de ligne, structure attendue)."""


class FormattingError(SharedError):
    """Erreur de formatage (conversion, alignement, rendu neutre)."""


class ValidationError(SharedError):
    """Erreur de validation générique (port, date, format).

    Utilisée uniquement pour des contrôles utilitaires, pas pour
    des invariants métier (qui eux vivent dans domain/).
    """
# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit les exceptions génériques transverses partagées par les utilitaires
#   de shared/ (shell, parsing, formatage, validation).
# - Fournit une hiérarchie minimale : SharedError (base), ShellCommandError,
#   ParsingError, FormattingError, ValidationError.
#
# Pourquoi dans shared/ (charte) :
# - Ce sont des exceptions purement techniques, non métier
# - Elles sont utilisées par plusieurs utilitaires transverses (shell.py,
#   parsing.py, utils.py, formatting.py)
# - Aucun lien avec une règle firewall, fail2ban, logs, blacklist
# - Aucune dépendance vers domain/, application/, infrastructure/, interfaces/
#
# Ce qu'il ne contient PAS :
# ❌ Pas d'import depuis domain/
# ❌ Pas d'import depuis application/
# ❌ Pas d'import depuis infrastructure/
# ❌ Pas d'import depuis interfaces/
# ❌ Pas d'exception métier (IPInvalidError, JailError, etc. → domain/)
# ❌ Pas d'exception applicative (CapabilityUnavailableError → application/)
# ❌ Pas d'exception technique d'infrastructure (BackendError → infrastructure/)
# ❌ Pas de subprocess, sqlite3, rich, open() — aucun I/O
#
# Points clés :
# - SharedError : base commune à toutes les exceptions de shared/
# - ShellCommandError : transporte command, return_code, stdout, stderr
#   pour diagnostic riche (utile pour infrastructure/ qui encapsulera)
# - ParsingError : erreurs de regex, format de ligne, structure attendue
# - FormattingError : erreurs de conversion, alignement, rendu neutre
# - ValidationError : contrôles utilitaires (port, date, format)
# - Chaque exception est sérialisable (attributs publics simples)
#
# Comment il sera utilisé (aperçu) :
# - shared/shell.py lèvera ShellCommandError si subprocess échoue
# - shared/parsing.py lèvera ParsingError si regex ne matche pas
# - shared/utils.py lèvera ValidationError si port/date invalide
# - infrastructure/ capturera ces erreurs pour les encapsuler en erreurs
#   techniques métier (BackendError, StorageError) avant remontée
# - application/ ne verra jamais ces exceptions brutes (encapsulation)
#---------------------------------------------------------------------->          
