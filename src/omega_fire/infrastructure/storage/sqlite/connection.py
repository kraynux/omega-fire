# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""SQLite database connection manager.

Manages the SQLite database connection lifecycle: opening, closing,
transaction management, and connection pooling. The database file
is stored in var/db/omega.db (not in the source tree).

This module performs real file I/O and is therefore in infrastructure/.
"""
import sqlite3
from pathlib import Path
from typing import Optional, Generator
from contextlib import contextmanager
from omega_fire.infrastructure.storage.sqlite.exceptions import (
    DatabaseConnectionError,
)


class DatabaseConnection:
    """Manages SQLite database connections.
    
    Provides connection lifecycle management, transaction control,
    and context managers for safe database access.
    """
    
    def __init__(self, db_path: Path):
        """Initialize the database connection manager.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self._db_path = db_path
        self._connection: Optional[sqlite3.Connection] = None
    
    @property
    def db_path(self) -> Path:
        """Get the database file path."""
        return self._db_path
    
    def connect(self) -> None:
        """Open the database connection.
        
        Creates the parent directory if it doesn't exist.
        
        Raises:
            DatabaseConnectionError: If connection fails
        """
        try:
            # Ensure parent directory exists
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            
            self._connection = sqlite3.connect(
                str(self._db_path),
                timeout=10.0,
                check_same_thread=False,
            )
            self._connection.row_factory = sqlite3.Row
            self._connection.execute("PRAGMA foreign_keys = ON")
            self._connection.execute("PRAGMA journal_mode = WAL")
        
        except sqlite3.Error as e:
            raise DatabaseConnectionError(
                db_path=str(self._db_path),
                reason=str(e),
            ) from e
    
    # ⏬Initailisation de la BD⏬
    def initialize_tables(self) -> None:
        """Initialise le schéma de la base de données si les tables manquent."""
        if not self._connection:
            self.connect()

        schema_rules = """
        CREATE TABLE IF NOT EXISTS rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            backend TEXT,
            family TEXT,
            table_name TEXT,
            chain TEXT,
            action TEXT,
            protocol TEXT,
            port_start INTEGER,
            port_end INTEGER,
            source_cidr TEXT,
            dest_cidr TEXT,
            comment TEXT,
            priority INTEGER DEFAULT 0,
            enabled INTEGER DEFAULT 1,
            rule_id TEXT
        );
        """
        self.execute(schema_rules)
        self.get_connection().commit()

    def close(self) -> None:
        """Close the database connection."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None
    
    def is_connected(self) -> bool:
        """Check if the connection is open.
        
        Returns:
            True if connected
        """
        return self._connection is not None
    
    def get_connection(self) -> sqlite3.Connection:
        """Get the underlying SQLite connection.
        
        Returns:
            sqlite3.Connection instance
        
        Raises:
            DatabaseConnectionError: If not connected
        """
        if self._connection is None:
            raise DatabaseConnectionError(
                db_path=str(self._db_path),
                reason="Connection not established. Call connect() first.",
            )
        return self._connection
    
    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager for database transactions.
        
        Commits on success, rolls back on exception.
        
        Yields:
            sqlite3.Connection for executing queries
        
        Raises:
            DatabaseConnectionError: If not connected
        """
        conn = self.get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    
    @contextmanager
    def cursor(self) -> Generator[sqlite3.Cursor, None, None]:
        """Context manager for database cursors.
        
        Automatically closes the cursor on exit.
        
        Yields:
            sqlite3.Cursor for executing queries
        
        Raises:
            DatabaseConnectionError: If not connected
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
        finally:
            cursor.close()
    
    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a single query.
        
        Args:
            query: SQL query string
            params: Query parameters
        
        Returns:
            sqlite3.Cursor with results
        
        Raises:
            DatabaseConnectionError: If not connected
        """
        conn = self.get_connection()
        return conn.execute(query, params)
    
    def execute_many(self, query: str, params_list: list[tuple]) -> sqlite3.Cursor:
        """Execute a query multiple times with different parameters.
        
        Args:
            query: SQL query string
            params_list: List of parameter tuples
        
        Returns:
            sqlite3.Cursor with results
        
        Raises:
            DatabaseConnectionError: If not connected
        """
        conn = self.get_connection()
        return conn.executemany(query, params_list)
    
    def __enter__(self):
        """Enter context manager: open connection."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager: close connection."""
        self.close()
        return False


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Gère le cycle de vie des connexions SQLite (ouverture, fermeture, transactions)
# - Fournit des context managers pour un accès sécurisé à la base
# - Le fichier DB est stocké dans var/db/omega.db (pas dans le code source)
# Pourquoi dans infrastructure/ (charte) :
# - C'est une implémentation technique qui fait des I/O réels (fichier SQLite)
# - Le domaine ne doit pas connaître SQLite (règle de dépendance)
# - L'application/ utilise les repositories via ports/, pas cette classe directement
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier (pas de règles de blacklist, politiques)
# ❌ Pas de dépendance vers domain/, application/ ou interfaces/
# ❌ Pas de requêtes SQL concrètes (c'est le rôle des repositories)
# Points clés :
# - DatabaseConnection : classe principale avec gestion du cycle de vie
# - connect() : ouvre la connexion, crée le répertoire parent si nécessaire
#   - Active foreign_keys et journal_mode=WAL pour la performance
# - close() : ferme la connexion proprement
# - transaction() : context manager pour les transactions (commit/rollback)
# - cursor() : context manager pour les curseurs (fermeture automatique)
# - execute() / execute_many() : exécution de requêtes
# - Support du pattern context manager (__enter__/__exit__)
# - db_path : chemin vers le fichier DB (var/db/omega.db)
# Comment il sera utilisé (aperçu) :
# - infrastructure/storage/sqlite/repositories.py l'utilisera pour exécuter les requêtes
# - app/bootstrap.py instanciera cette classe et l'injectera dans les repositories
# - Les tests utiliseront un fichier DB temporaire dans /tmp
#---------------------------------------------------------------------->
