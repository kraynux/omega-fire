# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Application health, disk usage, and database integrity collection
(sections 11, 12, 14).

Pure collection functions where possible. Disk usage and DB integrity
require light I/O (shutil.disk_usage, PRAGMA integrity_check) — kept
here rather than in infrastructure/ since they are read-only diagnostic
checks specific to this report, not reusable infrastructure adapters.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from omega_fire.infrastructure.config.paths import BACKUPS_DIR, LOGS_DIR, DB_PATH
from omega_fire.application.queries.audit_report.models import (
    AppHealth,
    DiskUsage,
    DatabaseIntegrity,
)

DISK_WARNING_THRESHOLD_PERCENT = 80


def collect_app_health() -> AppHealth:
    """Collect a minimal application health snapshot (section 11).

    No version identifier exists in the project yet (no pyproject.toml
    version field, no __version__) — reported as "N/A" rather than
    guessed. Backup info reflects menu 7.1 once it exists; until then,
    reported as not configured.

    Returns:
        AppHealth with best-effort values.
    """
    return AppHealth(
        version="N/A",
        last_backup_info="N/A — non configuré (menu 7.1)",
        config_integrity="N/A",
    )


def collect_disk_usage() -> DiskUsage:
    """Collect disk usage of var/ subdirectories (section 12).

    Returns:
        DiskUsage with sizes in MB, free space, and an optional warning
        if free space is below the threshold.
    """
    def _dir_size_mb(path: Path) -> float:
        if not path.exists():
            return 0.0
        total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
        return total / (1024 * 1024)

    backups_size = _dir_size_mb(BACKUPS_DIR)
    backups_count = len(list(BACKUPS_DIR.glob("*.tar.gz"))) if BACKUPS_DIR.exists() else 0
    logs_size = _dir_size_mb(LOGS_DIR)
    db_size = DB_PATH.stat().st_size / (1024 * 1024) if DB_PATH.exists() else 0.0

    warning = None
    free_gb = 0.0
    try:
        import shutil as _shutil
        usage = _shutil.disk_usage(BACKUPS_DIR if BACKUPS_DIR.exists() else Path("."))
        free_gb = usage.free / (1024 * 1024 * 1024)
        used_percent = (usage.used / usage.total) * 100 if usage.total else 0
        if used_percent >= DISK_WARNING_THRESHOLD_PERCENT:
            warning = f"Espace disque utilisé à {used_percent:.0f}% — surveiller"
    except Exception:
        pass

    return DiskUsage(
        backups_size_mb=round(backups_size, 2),
        backups_count=backups_count,
        db_size_mb=round(db_size, 2),
        logs_size_mb=round(logs_size, 2),
        free_space_gb=round(free_gb, 2),
        warning=warning,
    )


def check_database_integrity(db_connection: Any) -> DatabaseIntegrity:
    """Run a basic SQLite integrity check (section 14).

    Args:
        db_connection: DatabaseConnection instance
            (infrastructure/storage/sqlite/connection.py).

    Returns:
        DatabaseIntegrity with the check result and DB file size.
    """
    if db_connection is None:
        return DatabaseIntegrity(
            integrity_ok=False,
            integrity_details="Connexion base de données non disponible",
        )

    try:
        cursor = db_connection.execute("PRAGMA integrity_check")
        row = cursor.fetchone()
        result = row[0] if row else "unknown"
        integrity_ok = (result == "ok")
    except Exception as e:
        result = f"Erreur lors de la vérification : {e}"
        integrity_ok = False

    db_size = DB_PATH.stat().st_size / (1024 * 1024) if DB_PATH.exists() else 0.0

    schema_version = "N/A"
    try:
        from omega_fire.infrastructure.storage.sqlite.schema import get_schema_version
        schema_version = get_schema_version(db_connection)
    except Exception:
        pass

    return DatabaseIntegrity(
        integrity_ok=integrity_ok,
        integrity_details=str(result),
        db_size_mb=round(db_size, 2),
        schema_version=schema_version,
    )


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Collecte la santé applicative (11), l'usage disque (12) et
#   l'intégrité de la base de données (14) pour le rapport d'audit
#   (menu 6.3).
#
# Pourquoi dans application/queries/audit_report/ (charte) :
# - Diagnostics en lecture seule, spécifiques à ce rapport — pas des
#   adapters infrastructure/ réutilisables ailleurs, donc pas déplacés
#   là-bas.
# - check_database_integrity() reste un appel SQL en lecture pure
#   (PRAGMA), pas une modification — cohérent avec le rôle de query.
#
# Points clés :
# - collect_app_health() : version "N/A" (aucune source de version
#   dans le projet actuellement — non deviné).
# - collect_disk_usage() : tailles réelles via rglob + stat, seuil
#   d'alerte à 80% d'espace disque utilisé.
# - check_database_integrity() : PRAGMA integrity_check SQLite,
#   réutilise get_schema_version() existant (schema.py).
#
# Comment il sera utilisé :
# - report_builder.py (application/queries/audit_report/report_builder.py)
#   appelle ces 3 fonctions pour peupler AuditReportData.
#----------------------------------------------------------------------
