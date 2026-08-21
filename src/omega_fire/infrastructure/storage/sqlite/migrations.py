# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""SQLite database migrations.

Manages database schema evolution through versioned migrations.
Each migration is a SQL script that transforms the schema from
one version to the next.

This module performs real file I/O and is therefore in infrastructure/.
"""
import sqlite3
from pathlib import Path
from typing import Optional
from omega_fire.infrastructure.storage.sqlite.connection import DatabaseConnection
from omega_fire.infrastructure.storage.sqlite.exceptions import MigrationError


# Fragments d'erreur SQLite indiquant qu'une instruction DDL a déjà été
# appliquée précédemment (colonne ou table déjà existante). Dans ce cas,
# la migration est considérée comme sans effet plutôt qu'en échec, afin
# de rester idempotente : elle peut être rejouée sans jamais nécessiter
# d'intervention manuelle, y compris si un état incohérent (colonnes
# déjà ajoutées mais version non enregistrée) a existé avant ce correctif.
_ALREADY_APPLIED_MARKERS = (
    "duplicate column name",
    "already exists",
)


class Migration:
    """Represents a single database migration."""
    
    def __init__(self, version: str, name: str, sql: str):
        """Initialize a migration.
        
        Args:
            version: Migration version (e.g., "001")
            name: Migration name (e.g., "initial_schema")
            sql: SQL script to execute
        """
        self.version = version
        self.name = name
        self.sql = sql
    
    @property
    def full_name(self) -> str:
        """Get the full migration name (version_name)."""
        return f"{self.version}_{self.name}"


class MigrationManager:
    """Manages database migrations."""
    
    def __init__(self, db: DatabaseConnection, migrations_dir: Path):
        """Initialize the migration manager.
        
        Args:
            db: Database connection
            migrations_dir: Directory containing migration SQL files
        """
        self._db = db
        self._migrations_dir = migrations_dir
    
    def get_current_version(self) -> str:
        """Get the current database version.
        
        Returns:
            Version string (e.g., "001") or "000" if no migrations applied
        """
        try:
            cursor = self._db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
            )
            if cursor.fetchone() is None:
                return "000"
            
            cursor = self._db.execute(
                "SELECT version FROM schema_version ORDER BY applied_at DESC LIMIT 1"
            )
            row = cursor.fetchone()
            return row["version"] if row else "000"
        except Exception:
            return "000"
    
    def get_available_migrations(self) -> list[Migration]:
        """Get all available migrations from the migrations directory.
        
        Returns:
            List of Migration objects sorted by version
        """
        migrations = []
        
        if not self._migrations_dir.exists():
            return migrations
        
        for file_path in sorted(self._migrations_dir.glob("v*.sql")):
            # Parse filename: v001_initial.sql
            name = file_path.stem  # v001_initial
            parts = name.split("_", 1)
            if len(parts) == 2:
                version = parts[0][1:]  # Remove 'v' prefix
                migration_name = parts[1]
                sql = file_path.read_text()
                migrations.append(Migration(version, migration_name, sql))
        
        return migrations
    
    def get_pending_migrations(self) -> list[Migration]:
        """Get migrations that haven't been applied yet.
        
        Returns:
            List of pending Migration objects
        """
        current_version = self.get_current_version()
        available = self.get_available_migrations()
        
        return [m for m in available if m.version > current_version]
    
    def _is_already_applied_error(self, error: Exception) -> bool:
        """Check whether an error indicates a DDL statement already took effect.
        
        Args:
            error: Exception raised while executing a migration statement
        
        Returns:
            True if the error text matches a known "already applied" marker
        """
        message = str(error).lower()
        return any(marker in message for marker in _ALREADY_APPLIED_MARKERS)
    
    def apply_migration(self, migration: Migration) -> None:
        """Apply a single migration.
        
        Executes each SQL statement individually rather than as a single
        script. Statements that fail because their effect is already
        present (column/table already exists) are treated as no-ops
        instead of errors, making the migration safe to (re)apply even
        if a previous run partially succeeded without being recorded.
        Any other failure still raises MigrationError as before.
        
        Args:
            migration: Migration to apply
        
        Raises:
            MigrationError: If a statement fails for a reason other than
                "already applied"
        """
        try:
            with self._db.transaction() as conn:
                statements = [
                    stmt.strip()
                    for stmt in migration.sql.split(";")
                    if stmt.strip()
                ]

                for statement in statements:
                    try:
                        conn.execute(statement)
                    except sqlite3.Error as stmt_error:
                        if self._is_already_applied_error(stmt_error):
                            # Effet déjà présent en base : on continue sans
                            # échouer, la migration reste idempotente.
                            continue
                        raise

                # Record migration in schema_version table
                conn.execute(
                    """
                    INSERT INTO schema_version (version, name, applied_at)
                    VALUES (?, ?, datetime('now'))
                    """,
                    (migration.version, migration.name),
                )
        except Exception as e:
            raise MigrationError(
                migration_name=migration.full_name,
                reason=str(e),
            ) from e
    
    def apply_all_pending(self) -> list[str]:
        """Apply all pending migrations.
        
        Returns:
            List of applied migration names
        
        Raises:
            MigrationError: If any migration fails
        """
        pending = self.get_pending_migrations()
        applied = []
        
        for migration in pending:
            self.apply_migration(migration)
            applied.append(migration.full_name)
        
        return applied
    
    def ensure_schema_version_table(self) -> None:
        """Ensure the schema_version table exists.
        
        This table tracks which migrations have been applied.
        """
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version TEXT NOT NULL,
                name TEXT NOT NULL,
                applied_at TEXT NOT NULL
            )
        """)
        self._db.get_connection().commit()


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Gère l'évolution du schéma de base via des migrations versionnées
# - Chaque migration est un script SQL qui transforme le schéma
# - Suit les migrations appliquées dans la table schema_version
# Pourquoi dans infrastructure/ (charte) :
# - C'est une implémentation technique qui fait des I/O réels (fichiers SQL, DDL)
# - Le domaine ne doit pas connaître SQLite (règle de dépendance)
# - L'application/ utilise les repositories via ports/, pas cette classe
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier (pas de règles de blacklist, politiques)
# ❌ Pas de dépendance vers domain/, application/ ou interfaces/
# ❌ Pas de requêtes SELECT/INSERT métier (c'est le rôle des repositories)
# Points clés :
# - Migration : dataclass représentant une migration (version, name, sql)
# - MigrationManager : classe principale
#   - get_current_version() : retourne la version actuelle ("000" si aucune migration)
#   - get_available_migrations() : liste les fichiers SQL dans migrations_dir
#   - get_pending_migrations() : filtre les migrations non encore appliquées
#   - apply_migration() : exécute une migration statement par statement,
#     idempotente (tolère "duplicate column"/"already exists" comme no-op),
#     puis l'enregistre
#   - apply_all_pending() : applique toutes les migrations en attente
#   - ensure_schema_version_table() : crée la table de suivi si nécessaire
# - Format des fichiers : v001_initial.sql, v002_add_metadata.sql, etc.
# - Transactions : chaque migration est atomique (commit/rollback)
# - Ordre : les migrations sont appliquées dans l'ordre alphabétique (version)
# - Idempotence : une migration déjà partiellement/totalement appliquée peut
#   être rejouée sans jamais nécessiter d'intervention manuelle de l'utilisateur
# Comment il sera utilisé (aperçu) :
# - app/bootstrap.py appellera apply_all_pending() au démarrage
# - Les fichiers SQL sont dans infrastructure/storage/sqlite/migrations/versions/
# - Les tests utiliseront un fichier DB temporaire
#---------------------------------------------------------------------->
