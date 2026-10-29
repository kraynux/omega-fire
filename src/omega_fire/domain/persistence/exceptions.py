# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Persistence domain exceptions.

Pure domain exceptions for the persistence subdomain.
These express business rule violations (invalid snapshot, failed backup,
failed restore), not technical failures of file I/O. They are caught
by application/ and translated into Results or user-facing messages.
"""
from omega_fire.shared.i18n import _


class PersistenceError(Exception):
    """Base exception for persistence domain."""
    pass


class InvalidSnapshotError(PersistenceError):
    """Raised when a snapshot is invalid or incomplete.
    
    Business rule: a snapshot must have valid metadata and non-empty content.
    """
    def __init__(self, snapshot_id: str, reason: str):
        self.snapshot_id = snapshot_id
        self.reason = reason
        super().__init__(_("Snapshot « {snapshot_id} » invalide : {reason}").format(snapshot_id=snapshot_id, reason=reason))


class BackupError(PersistenceError):
    """Raised when a backup operation fails.
    
    Examples: no data to backup, invalid scope, conflicting backup.
    """
    def __init__(self, operation: str, reason: str):
        self.operation = operation
        self.reason = reason
        super().__init__(_("Erreur de sauvegarde ({operation}) : {reason}").format(operation=operation, reason=reason))


class RestoreError(PersistenceError):
    """Raised when a restore operation fails.
    
    Examples: snapshot not found, corrupted snapshot, incompatible version.
    """
    def __init__(self, snapshot_id: str, reason: str):
        self.snapshot_id = snapshot_id
        self.reason = reason
        super().__init__(_("Erreur de restauration de « {snapshot_id} » : {reason}").format(snapshot_id=snapshot_id, reason=reason))


class SnapshotNotFoundError(PersistenceError):
    """Raised when attempting to use a snapshot that does not exist.
    
    Business rule: a snapshot must exist before it can be restored or inspected.
    """
    def __init__(self, snapshot_id: str):
        self.snapshot_id = snapshot_id
        super().__init__(_("Snapshot introuvable : {snapshot_id}").format(snapshot_id=snapshot_id))


class CorruptedSnapshotError(PersistenceError):
    """Raised when a snapshot file is corrupted or unreadable.
    
    Business rule: a corrupted snapshot cannot be restored safely.
    """
    def __init__(self, snapshot_id: str, reason: str):
        self.snapshot_id = snapshot_id
        self.reason = reason
        super().__init__(_("Corrupted snapshot '{snapshot_id}': {reason}").format(snapshot_id=snapshot_id, reason=reason))


class IncompatibleVersionError(PersistenceError):
    """Raised when a snapshot version is incompatible with current app.
    
    Business rule: a snapshot from a newer version cannot be restored safely.
    """
    def __init__(self, snapshot_version: str, app_version: str):
        self.snapshot_version = snapshot_version
        self.app_version = app_version
        super().__init__(
            _("Incompatible versions: snapshot={snapshot_version}, app={app_version}").format(snapshot_version=snapshot_version, app_version=app_version)
        )


class EmptyBackupError(PersistenceError):
    """Raised when attempting to create a backup with no data.
    
    Business rule: a backup must contain at least one component.
    """
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(_("Sauvegarde vide : {reason}").format(reason=reason))


class InvalidRestoreScopeError(PersistenceError):
    """Raised when restore scope does not match snapshot content.
    
    Examples: trying to restore fail2ban from a blacklist-only snapshot.
    """
    def __init__(self, requested_scope: str, available_scope: str):
        self.requested_scope = requested_scope
        self.available_scope = available_scope
        super().__init__(
            _("Portée de restauration invalide : demandée={requested_scope}, disponible={available_scope}").format(requested_scope=requested_scope, available_scope=available_scope)
        )

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Exceptions métier spécifiques au sous-domaine persistence. Elles expriment des violations de règles métier (snapshot invalide, backup impossible, restauration impossible), pas des pannes techniques du système de fichiers.
#---------------------------------------------------------------------->
