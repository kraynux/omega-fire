# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Infrastructure layer exceptions.

Base hierarchy for technical failures across all infrastructure/
adapters (storage, backends, exporters, probes). These express
technical failures (I/O errors, command failures, unavailable
services), not business rule violations — those belong in domain/
or application/ exceptions.

Per-adapter exception modules (e.g. infrastructure/storage/sqlite/
exceptions.py) may define their own specific exceptions, but should
inherit from the relevant class here rather than from CoreError
directly, to keep a single infrastructure-wide hierarchy.
"""
from omega_fire.core.exceptions import CoreError


class InfrastructureError(CoreError):
    """Base exception for all infrastructure/ technical failures."""
    pass


class CommandExecutionError(InfrastructureError):
    """Raised when an external command fails (non-zero exit, etc.).

    Should carry enough context (command, stdout, stderr, exit code)
    for application/ to translate it into a user-facing message.
    """
    pass


class ServiceUnavailableError(InfrastructureError):
    """Raised when a required system service is unavailable."""
    pass


class StorageError(InfrastructureError):
    """Raised when a storage operation fails (file I/O, archive, DB)."""
    pass


class ParseError(InfrastructureError):
    """Raised when parsing external command output fails."""
    pass


class AdapterConfigurationError(InfrastructureError):
    """Raised when an adapter is misconfigured (missing path, bad settings)."""
    pass


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Hiérarchie d'exceptions technique commune à toute la couche
#   infrastructure/, conforme à la charte (section 5).
#
# Pourquoi dans infrastructure/ (charte) :
# - Ce sont des erreurs techniques (I/O, commandes, services), pas des
#   violations de règles métier (celles-ci vivent dans domain/exceptions.py
#   ou application/exceptions.py).
#
# Ce qu'il ne contient PAS :
# ❌ Pas d'exceptions métier (InvalidSnapshotError, etc. → domain/)
# ❌ Pas d'exceptions spécifiques à un backend précis (celles-ci restent
#   dans leur propre module, ex: infrastructure/storage/sqlite/exceptions.py,
#   mais devraient hériter d'une classe d'ici plutôt que de CoreError direct)
#
# Points clés :
# - InfrastructureError : base commune de toute la couche.
# - StorageError : utilisé par persistence_adapter.py pour les échecs
#   de backup/restauration/listage/suppression d'archives.
# - Note : infrastructure/storage/sqlite/exceptions.py définit déjà un
#   StorageError qui hérite directement de CoreError (pas de celui-ci).
#   Coexistence possible tant que les imports restent explicites et
#   qualifiés, mais à unifier un jour pour éviter la confusion.
#
# Comment il sera utilisé (aperçu) :
# - infrastructure/storage/files/persistence_adapter.py importera
#   StorageError d'ici (pas celui de sqlite/exceptions.py).
#----------------------------------------------------------------------
