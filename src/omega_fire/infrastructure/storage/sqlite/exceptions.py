# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""SQLite storage exceptions.

Technical exceptions specific to SQLite storage operations.
These express failures in database connection, query execution,
schema migration, or repository operations. They are caught by
the application layer and translated into stable error messages.
"""
from omega_fire.core.exceptions import CoreError


class StorageError(CoreError):
    """Base exception for storage operations."""
    def __init__(self, message: str, context: dict = None):
        super().__init__(message, context)


class DatabaseConnectionError(StorageError):
    """Raised when database connection fails."""
    def __init__(self, db_path: str, reason: str, context: dict = None):
        super().__init__(
            f"Failed to connect to database '{db_path}': {reason}",
            {**(context or {}), "db_path": db_path, "reason": reason},
        )
        self.db_path = db_path
        self.reason = reason


class DatabaseQueryError(StorageError):
    """Raised when a database query fails."""
    def __init__(self, query: str, reason: str, context: dict = None):
        super().__init__(
            f"Database query failed: {reason}",
            {**(context or {}), "query": query[:100], "reason": reason},
        )
        self.query = query
        self.reason = reason


class DatabaseSchemaError(StorageError):
    """Raised when schema creation or migration fails."""
    def __init__(self, reason: str, version: str = "", context: dict = None):
        super().__init__(
            f"Database schema error: {reason}",
            {**(context or {}), "reason": reason, "version": version},
        )
        self.reason = reason
        self.version = version


class MigrationError(StorageError):
    """Raised when a migration fails."""
    def __init__(self, migration_name: str, reason: str, context: dict = None):
        super().__init__(
            f"Migration '{migration_name}' failed: {reason}",
            {**(context or {}), "migration_name": migration_name, "reason": reason},
        )
        self.migration_name = migration_name
        self.reason = reason


class RepositoryError(StorageError):
    """Raised when a repository operation fails."""
    def __init__(self, repository: str, operation: str, reason: str, context: dict = None):
        super().__init__(
            f"Repository '{repository}' operation '{operation}' failed: {reason}",
            {**(context or {}), "repository": repository, "operation": operation, "reason": reason},
        )
        self.repository = repository
        self.operation = operation
        self.reason = reason


class EntityNotFoundError(StorageError):
    """Raised when an entity is not found in the database."""
    def __init__(self, entity_type: str, entity_id: str, context: dict = None):
        super().__init__(
            f"{entity_type} with id '{entity_id}' not found",
            {**(context or {}), "entity_type": entity_type, "entity_id": entity_id},
        )
        self.entity_type = entity_type
        self.entity_id = entity_id


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit les exceptions techniques spécifiques au stockage SQLite.
#   Ces exceptions expriment des pannes ou limitations techniques liées
#   à la connexion, aux requêtes, au schéma, aux migrations et aux repositories.
# Pourquoi dans infrastructure/ (charte) :
# - Ce sont des erreurs techniques, pas des règles métier
# - Elles encapsulent les pannes système (DB inaccessible, requête échouée)
# - Elles héritent de CoreError pour être capturées uniformément
# - L'application/ les traduira en erreurs stables via le pipeline
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier (pas de règles de blacklist, politiques)
# ❌ Pas d'appels système (juste des définitions d'exceptions)
# ❌ Pas de dépendance vers domain/, application/ ou interfaces/
# Points clés :
# - Hiérarchie : StorageError → CoreError → Exception
# - 6 exceptions ciblées :
#   - DatabaseConnectionError : échec de connexion (db_path, reason)
#   - DatabaseQueryError : échec de requête (query, reason)
#   - DatabaseSchemaError : erreur de schéma (reason, version)
#   - MigrationError : échec de migration (migration_name, reason)
#   - RepositoryError : échec d'opération repository (repository, operation, reason)
#   - EntityNotFoundError : entité introuvable (entity_type, entity_id)
# - Contexte riche : chaque exception stocke les données pertinentes
# Comment elles seront utilisées (aperçu) :
# - infrastructure/storage/sqlite/connection.py les lèvera lors de la connexion
# - infrastructure/storage/sqlite/repositories.py les lèvera lors des opérations
# - application/pipeline/ les capturera via les ports
#---------------------------------------------------------------------->
