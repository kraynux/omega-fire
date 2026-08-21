# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Application paths configuration.

Defines all filesystem paths used by the application. All runtime paths
are under var/ (not in the source tree). This module centralizes path
management to avoid hardcoded paths scattered across the codebase.

This module performs no I/O — it only defines path constants and helpers.

Architecture compliance (charte-architecture-review-checklist.md):
- Lives in infrastructure/config/ (rule 4: only infrastructure/ handles filesystem)
- No dependency on domain/, application/, interfaces/ (rule 1: inward dependencies)
- No business logic, no I/O (rule 3: pure configuration)
- Consumed by app/bootstrap.py via injection, and by other layers via module constants
- Single source of truth for all runtime paths (checklist §8)
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


# ============================================================================
# Module-level constants (single source of truth)
# ============================================================================
# These constants are computed once at import time from __file__.
# They provide a simple API for modules that don't need the full AppPaths class.
#
# File location: src/omega_fire/infrastructure/config/paths.py
#   paths.py -> config -> infrastructure -> omega_fire -> src -> PROJECT_ROOT
#   (5 levels up)
# ============================================================================

#  APRÈS (5 niveaux — pointe vers la vraie racine omega-fire/)
_PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent.parent.parent

# --- Runtime directories (all under var/) ---
VAR_DIR: Path = _PROJECT_ROOT / "var"
DB_DIR: Path = VAR_DIR / "db"
CACHE_DIR: Path = VAR_DIR / "cache"
EXPORTS_DIR: Path = VAR_DIR / "exports"
BLOCKLIST_DIR: Path = VAR_DIR / "blocklist"          # singular, matches var/blocklist/
BACKUPS_DIR: Path = VAR_DIR / "backups"
RUNTIME_DIR: Path = VAR_DIR / "runtime"
LOGS_DIR: Path = VAR_DIR / "logs"

# --- Configuration directories --- 
CONFIG_DIR: Path = _PROJECT_ROOT / "config"

# --- Source directories ---
SRC_DIR: Path = _PROJECT_ROOT / "src" / "omega_fire"
TEMPLATES_DIR: Path = SRC_DIR / "domain" / "reports" / "templates"
MIGRATIONS_DIR: Path = SRC_DIR / "infrastructure" / "storage" / "sqlite" / "migrations" / "versions"

# --- Key files ---
DB_PATH: Path = DB_DIR / "omega.db"
APP_LOG_PATH: Path = LOGS_DIR / "app.log"             # matches existing var/logs/app.log
AUDIT_LOG_PATH: Path = LOGS_DIR / "audit.log"         # matches existing var/logs/audit.log
ENV_FILE: Path = _PROJECT_ROOT / ".env"

# --- Default blocklist files (shared by menus 2.7, 2.8, 4.3) ---
DEFAULT_BLOCKLIST_FILE: Path = BLOCKLIST_DIR / "blocklist.txt"
DEFAULT_F2B_BLOCKLIST_FILE: Path = BLOCKLIST_DIR / "blocklist-f2b.txt"

# --- Pinned files (UI convenience, consumed by interfaces/cli/actions.py) ---
DEFAULT_PINNED_FILES: list[Path] = [
    DEFAULT_BLOCKLIST_FILE,
    DEFAULT_F2B_BLOCKLIST_FILE,
]

# --- All managed runtime directories (for ensure_runtime_dirs) ---
_ALL_RUNTIME_DIRS: tuple[Path, ...] = (
    VAR_DIR,
    DB_DIR,
    CACHE_DIR,
    EXPORTS_DIR,
    BLOCKLIST_DIR,
    BACKUPS_DIR,
    RUNTIME_DIR,
    LOGS_DIR,
    CONFIG_DIR,
)


# ============================================================================
# Public API for module-level usage
# ============================================================================

def ensure_runtime_dirs() -> None:
    """Create all runtime directories if they don't exist.

    Idempotent: safe to call multiple times. Uses exist_ok=True so no error
    is raised if directories already exist.

    Should be called once at bootstrap (app/bootstrap.py) to guarantee that
    var/blocklist, var/exports, var/logs, etc. exist before any action runs.
    """
    for directory in _ALL_RUNTIME_DIRS:
        directory.mkdir(parents=True, exist_ok=True)


def get_project_root() -> Path:
    """Return the project root directory.

    Useful for modules that need the root but don't want to import the
    full AppPaths class.
    """
    return _PROJECT_ROOT


# ============================================================================
# AppPaths class (for dependency injection)
# ============================================================================

class AppPaths:
    """Centralized application paths (injectable version).

    All paths are relative to a base directory (typically the project root).
    Runtime data (db, cache, exports, backups, logs, blocklist) goes under var/.

    This class is the injectable counterpart of the module-level constants.
    Use it when you need configurable base_dir (e.g., in tests) or when the
    application needs to pass paths explicitly via dependency injection.

    For simple usage, prefer the module-level constants (BLOCKLIST_DIR, etc.).
    """

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        """Initialize the paths configuration.

        Args:
            base_dir: Base directory of the application.
                Defaults to the calculated project root (same as _PROJECT_ROOT).
        """
        if base_dir is not None:
            self._base_dir = Path(base_dir).resolve()
        else:
            self._base_dir = _PROJECT_ROOT

    # --- Base directories ---

    @property
    def base_dir(self) -> Path:
        """Get the base directory (project root)."""
        return self._base_dir

    @property
    def src_dir(self) -> Path:
        """Get the source directory (src/omega_fire/)."""
        return self._base_dir / "src" / "omega_fire"

    # --- Runtime directories (all under var/) ---

    @property
    def var_dir(self) -> Path:
        """Get the var directory (runtime data root)."""
        return self._base_dir / "var"

    @property
    def db_dir(self) -> Path:
        """Get the database directory."""
        return self.var_dir / "db"

    @property
    def cache_dir(self) -> Path:
        """Get the cache directory."""
        return self.var_dir / "cache"

    @property
    def exports_dir(self) -> Path:
        """Get the exports directory."""
        return self.var_dir / "exports"

    @property
    def blocklist_dir(self) -> Path:
        """Get the blocklist directory (singular, matches var/blocklist/)."""
        return self.var_dir / "blocklist"

    @property
    def backups_dir(self) -> Path:
        """Get the backups directory."""
        return self.var_dir / "backups"

    @property
    def runtime_dir(self) -> Path:
        """Get the runtime directory (UI state, pinned files, etc.)."""
        return self.var_dir / "runtime"

    @property
    def logs_dir(self) -> Path:
        """Get the logs directory."""
        return self.var_dir / "logs"

    # --- Configuration directories ---

    @property
    def config_dir(self) -> Path:
        """Get the configuration directory."""
        return self._base_dir / "config"

    # --- Key files ---

    @property
    def db_path(self) -> Path:
        """Get the main database file path (omega.db)."""
        return self.db_dir / "omega.db"

    @property
    def app_log_path(self) -> Path:
        """Get the application log file path (app.log)."""
        return self.logs_dir / "app.log"

    @property
    def audit_log_path(self) -> Path:
        """Get the audit log file path (audit.log)."""
        return self.logs_dir / "audit.log"

    @property
    def env_file(self) -> Path:
        """Get the .env file path."""
        return self._base_dir / ".env"

    @property
    def templates_dir(self) -> Path:
        """Get the HTML templates directory (domain/reports/templates/)."""
        return self.src_dir / "domain" / "reports" / "templates"

    # --- Default blocklist files ---

    @property
    def default_blocklist_file(self) -> Path:
        """Get the default blocklist file path (blocklist.txt)."""
        return self.blocklist_dir / "blocklist.txt"

    @property
    def default_f2b_blocklist_file(self) -> Path:
        """Get the default Fail2ban blocklist file path (blocklist-f2b.txt)."""
        return self.blocklist_dir / "blocklist-f2b.txt"

    @property
    def default_pinned_files(self) -> list[Path]:
        """Get the default pinned files (shared by menus 2.7, 2.8, 4.3)."""
        return [
            self.default_blocklist_file,
            self.default_f2b_blocklist_file,
        ]

    # --- Directory management ---

    def ensure_dirs(self) -> None:
        """Ensure all runtime directories exist.

        Creates var/, var/db/, var/cache/, var/exports/, var/blocklist/,
        var/backups/, var/runtime/, var/logs/, config/ if they don't exist.

        Alias for ensure_runtime_dirs() for backward compatibility.
        """
        ensure_runtime_dirs()

    def get_all_dirs(self) -> list[Path]:
        """Get all managed directories.

        Returns:
            List of all runtime directories managed by the application.
        """
        return list(_ALL_RUNTIME_DIRS)


# ============================================================================
# Convenience factory
# ============================================================================

def get_default_paths() -> AppPaths:
    """Get the default paths configuration.

    Returns:
        AppPaths instance with the calculated project root as base.
    """
    return AppPaths()


# ============================================================================
# Public API surface
# ============================================================================

__all__ = [
    # Module-level constants
    "VAR_DIR",
    "DB_DIR",
    "CACHE_DIR",
    "EXPORTS_DIR",
    "BLOCKLIST_DIR",
    "BACKUPS_DIR",
    "RUNTIME_DIR",
    "LOGS_DIR",
    "CONFIG_DIR",
    "SRC_DIR",
    "TEMPLATES_DIR",
    "DB_PATH",
    "APP_LOG_PATH",
    "AUDIT_LOG_PATH",
    "ENV_FILE",
    "DEFAULT_BLOCKLIST_FILE",
    "DEFAULT_F2B_BLOCKLIST_FILE",
    "DEFAULT_PINNED_FILES",
    # Functions
    "ensure_runtime_dirs",
    "get_project_root",
    "get_default_paths",
    # Classes
    "AppPaths",
]
