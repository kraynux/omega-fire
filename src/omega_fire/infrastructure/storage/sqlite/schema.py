# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""SQLite database schema management.

Defines the database schema (tables, indexes) and provides functions
to create or recreate the schema. The schema is versioned via migrations.

This module performs real file I/O and is therefore in infrastructure/.
"""
from omega_fire.infrastructure.storage.sqlite.connection import DatabaseConnection
from omega_fire.infrastructure.storage.sqlite.exceptions import DatabaseSchemaError


# Initial schema SQL
INITIAL_SCHEMA = """
-- Bans table: stores banned IPs
CREATE TABLE IF NOT EXISTS bans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ip TEXT NOT NULL,
    backend TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    source TEXT NOT NULL DEFAULT 'manual',
    comment TEXT,
    banned_at TEXT NOT NULL,
    expires_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Rules table: stores firewall rules
CREATE TABLE IF NOT EXISTS rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    backend TEXT NOT NULL,
    family TEXT NOT NULL,
    table_name TEXT NOT NULL,
    chain TEXT NOT NULL,
    action TEXT NOT NULL,
    protocol TEXT,
    port_start INTEGER,
    port_end INTEGER,
    source_cidr TEXT,
    dest_cidr TEXT,
    comment TEXT,
    priority INTEGER DEFAULT 0,
    enabled INTEGER DEFAULT 1,
    rule_id INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Audit logs table: stores audit events
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    command_name TEXT,
    step_name TEXT,
    success INTEGER NOT NULL,
    error_message TEXT,
    details TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Snapshots table: stores backup metadata
CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    scope TEXT NOT NULL,
    description TEXT,
    version TEXT,
    status TEXT NOT NULL,
    file_path TEXT,
    file_size_bytes INTEGER,
    checksum TEXT,
    created_at_ts TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_bans_ip ON bans(ip);
CREATE INDEX IF NOT EXISTS idx_bans_backend ON bans(backend);
CREATE INDEX IF NOT EXISTS idx_bans_status ON bans(status);
CREATE INDEX IF NOT EXISTS idx_bans_banned_at ON bans(banned_at);

CREATE INDEX IF NOT EXISTS idx_rules_backend ON rules(backend);
CREATE INDEX IF NOT EXISTS idx_rules_chain ON rules(chain);
CREATE INDEX IF NOT EXISTS idx_rules_action ON rules(action);

CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_command ON audit_logs(command_name);

CREATE INDEX IF NOT EXISTS idx_snapshots_snapshot_id ON snapshots(snapshot_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_status ON snapshots(status);
"""


def create_schema(db: DatabaseConnection) -> None:
    """Create the initial database schema.
    
    Args:
        db: Database connection
    
    Raises:
        DatabaseSchemaError: If schema creation fails
    """
    try:
        with db.transaction() as conn:
            conn.executescript(INITIAL_SCHEMA)
    except Exception as e:
        raise DatabaseSchemaError(
            reason=f"Failed to create schema: {e}",
        ) from e


def drop_schema(db: DatabaseConnection) -> None:
    """Drop all tables from the database.
    
    WARNING: This is destructive and cannot be undone.
    
    Args:
        db: Database connection
    
    Raises:
        DatabaseSchemaError: If schema drop fails
    """
    try:
        with db.transaction() as conn:
            conn.execute("DROP TABLE IF EXISTS bans")
            conn.execute("DROP TABLE IF EXISTS rules")
            conn.execute("DROP TABLE IF EXISTS audit_logs")
            conn.execute("DROP TABLE IF EXISTS snapshots")
    except Exception as e:
        raise DatabaseSchemaError(
            reason=f"Failed to drop schema: {e}",
        ) from e


def get_schema_version(db: DatabaseConnection) -> str:
    """Get the current schema version.
    
    Args:
        db: Database connection
    
    Returns:
        Schema version string (e.g., "1.0.0")
    """
    try:
        cursor = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
        )
        if cursor.fetchone() is None:
            return "0.0.0"
        
        cursor = db.execute("SELECT version FROM schema_version ORDER BY applied_at DESC LIMIT 1")
        row = cursor.fetchone()
        return row["version"] if row else "0.0.0"
    except Exception:
        return "0.0.0"


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit le schéma de la base SQLite (tables, index)
# - Fournit des fonctions pour créer ou supprimer le schéma
# - Le schéma est versionné via les migrations (migrations.py)
# Pourquoi dans infrastructure/ (charte) :
# - C'est une implémentation technique qui fait des I/O réels (DDL SQL)
# - Le domaine ne doit pas connaître SQLite (règle de dépendance)
# - L'application/ utilise les repositories via ports/, pas cette classe
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier (pas de règles de blacklist, politiques)
# ❌ Pas de dépendance vers domain/, application/ ou interfaces/
# ❌ Pas de requêtes SELECT/INSERT/UPDATE/DELETE (c'est le rôle des repositories)
# Points clés :
# - INITIAL_SCHEMA : SQL pour créer les tables (bans, rules, audit_logs, snapshots)
# - Indexes pour performance sur les colonnes fréquemment requêtées
# - create_schema() : crée toutes les tables et index
# - drop_schema() : supprime toutes les tables (destructif)
# - get_schema_version() : retourne la version actuelle du schéma
# - Utilise des transactions pour garantir l'atomicité
# - Compatible avec les migrations (migrations.py)
# Comment il sera utilisé (aperçu) :
# - app/bootstrap.py appellera create_schema() au premier démarrage
# - infrastructure/storage/sqlite/migrations.py gérera les évolutions du schéma
# - Les tests utiliseront un fichier DB temporaire
#---------------------------------------------------------------------->
