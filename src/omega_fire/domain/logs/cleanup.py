# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Logs domain cleanup logic.

Pure domain logic for log and archive cleanup rules.
This module defines WHAT to purge based on retention policies,
but does NOT perform the actual file deletions. Execution is
delegated to infrastructure/.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
from omega_fire.domain.logs.exceptions import InvalidRetentionError


class RetentionUnit(Enum):
    """Unit for retention period."""
    DAYS = "days"
    WEEKS = "weeks"
    MONTHS = "months"


@dataclass
class RetentionPolicy:
    """Policy defining how long to keep logs and archives.
    
    This is a pure data structure describing retention rules,
    without any knowledge of how to execute them.
    """
    max_age_days: int = 30                # Maximum age for log files
    max_archive_age_days: int = 90        # Maximum age for archived rotations
    max_total_size_bytes: Optional[int] = None  # Maximum total size (all logs + archives)
    min_free_space_bytes: Optional[int] = None  # Minimum free space to preserve
    
    def validate(self) -> list[str]:
        """Validate the retention policy.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        if self.max_age_days < 1:
            errors.append("max_age_days must be >= 1")
        
        if self.max_archive_age_days < 1:
            errors.append("max_archive_age_days must be >= 1")
        
        if self.max_total_size_bytes is not None and self.max_total_size_bytes <= 0:
            errors.append("max_total_size_bytes must be > 0 if set")
        
        if self.min_free_space_bytes is not None and self.min_free_space_bytes <= 0:
            errors.append("min_free_space_bytes must be > 0 if set")
        
        return errors
    
    def is_valid(self) -> bool:
        """Check if the policy is valid."""
        return len(self.validate()) == 0
    
    def to_days(self, value: int, unit: RetentionUnit) -> int:
        """Convert a retention value to days.
        
        Args:
            value: Retention value
            unit: Unit of the value
        
        Returns:
            Equivalent value in days
        """
        if unit == RetentionUnit.DAYS:
            return value
        elif unit == RetentionUnit.WEEKS:
            return value * 7
        elif unit == RetentionUnit.MONTHS:
            return value * 30
        return value


@dataclass
class FileInfo:
    """Metadata about a log or archive file.
    
    This is a pure data structure used for cleanup decisions.
    """
    path: str
    size_bytes: int
    mtime: datetime
    is_archive: bool = False
    
    def age_days(self, now: Optional[datetime] = None) -> float:
        """Calculate the age of the file in days.
        
        Args:
            now: Current time (default: datetime.now())
        
        Returns:
            Age in days (float)
        """
        if now is None:
            now = datetime.now()
        delta = now - self.mtime
        return delta.total_seconds() / 86400.0
    
    def is_expired(self, max_age_days: int, now: Optional[datetime] = None) -> bool:
        """Check if the file is expired based on age.
        
        Args:
            max_age_days: Maximum allowed age in days
            now: Current time (default: datetime.now())
        
        Returns:
            True if the file is older than max_age_days
        """
        return self.age_days(now) >= max_age_days


@dataclass
class CleanupPlan:
    """Plan of cleanup operations.
    
    This is a pure data structure describing what needs to be deleted,
    without any knowledge of how to execute it.
    """
    files_to_delete: list[str] = field(default_factory=list)
    total_size_to_free_bytes: int = 0
    files_to_keep: list[str] = field(default_factory=list)
    reasons: dict[str, str] = field(default_factory=dict)  # path -> reason
    created_at: datetime = datetime.now()
    
    def count(self) -> int:
        """Return the number of files to delete."""
        return len(self.files_to_delete)
    
    def is_empty(self) -> bool:
        """Check if no cleanup is needed."""
        return len(self.files_to_delete) == 0
    
    def size_to_free_mb(self) -> float:
        """Return the total size to free in megabytes."""
        return self.total_size_to_free_bytes / (1024 * 1024)


def identify_expired_files(
    files: list[FileInfo],
    max_age_days: int,
    now: Optional[datetime] = None,
) -> list[FileInfo]:
    """Identify files that are expired based on age.
    
    Args:
        files: List of files to check
        max_age_days: Maximum allowed age in days
        now: Current time (default: datetime.now())
    
    Returns:
        List of expired FileInfo objects
    """
    return [f for f in files if f.is_expired(max_age_days, now)]


def identify_expired_archives(
    files: list[FileInfo],
    max_archive_age_days: int,
    now: Optional[datetime] = None,
) -> list[FileInfo]:
    """Identify archives that are expired based on age.
    
    Args:
        files: List of files to check (only archives are considered)
        max_archive_age_days: Maximum allowed age for archives in days
        now: Current time (default: datetime.now())
    
    Returns:
        List of expired archive FileInfo objects
    """
    archives = [f for f in files if f.is_archive]
    return [f for f in archives if f.is_expired(max_archive_age_days, now)]


def identify_oversized_files(
    files: list[FileInfo],
    max_total_size_bytes: int,
    now: Optional[datetime] = None,
) -> list[FileInfo]:
    """Identify files to delete to stay under total size limit.
    
    Deletes oldest files first until total size is under the limit.
    
    Args:
        files: List of files to check
        max_total_size_bytes: Maximum allowed total size in bytes
        now: Current time (default: datetime.now())
    
    Returns:
        List of FileInfo objects to delete to meet size limit
    """
    total_size = sum(f.size_bytes for f in files)
    
    if total_size <= max_total_size_bytes:
        return []
    
    # Sort by mtime ascending (oldest first)
    sorted_files = sorted(files, key=lambda f: f.mtime)
    
    to_delete = []
    current_size = total_size
    
    for file in sorted_files:
        if current_size <= max_total_size_bytes:
            break
        to_delete.append(file)
        current_size -= file.size_bytes
    
    return to_delete


def compute_total_size(files: list[FileInfo]) -> int:
    """Compute the total size of all files.
    
    Args:
        files: List of files
    
    Returns:
        Total size in bytes
    """
    return sum(f.size_bytes for f in files)


def plan_cleanup(
    files: list[FileInfo],
    policy: RetentionPolicy,
    now: Optional[datetime] = None,
) -> CleanupPlan:
    """Plan a cleanup operation based on retention policy.
    
    This function determines which files should be deleted to comply
    with the retention policy, but does NOT execute the deletions.
    
    Args:
        files: List of all log and archive files
        policy: Retention policy to apply
        now: Current time (default: datetime.now())
    
    Returns:
        CleanupPlan describing what needs to be deleted
    """
    if now is None:
        now = datetime.now()
    
    files_to_delete = []
    reasons: dict[str, str] = {}
    
    # Step 1: Identify expired log files
    expired_logs = identify_expired_files(
        [f for f in files if not f.is_archive],
        policy.max_age_days,
        now,
    )
    for f in expired_logs:
        if f.path not in reasons:
            files_to_delete.append(f)
            reasons[f.path] = f"Expired (age: {f.age_days(now):.1f} days, max: {policy.max_age_days} days)"
    
    # Step 2: Identify expired archives
    expired_archives = identify_expired_archives(files, policy.max_archive_age_days, now)
    for f in expired_archives:
        if f.path not in reasons:
            files_to_delete.append(f)
            reasons[f.path] = f"Archive expired (age: {f.age_days(now):.1f} days, max: {policy.max_archive_age_days} days)"
    
    # Step 3: Check total size limit
    if policy.max_total_size_bytes is not None:
        remaining_files = [f for f in files if f not in files_to_delete]
        oversized = identify_oversized_files(
            remaining_files,
            policy.max_total_size_bytes,
            now,
        )
        for f in oversized:
            if f.path not in reasons:
                files_to_delete.append(f)
                reasons[f.path] = "Total size limit exceeded (oldest files removed first)"
    
    # Compute total size to free
    total_size_to_free = sum(f.size_bytes for f in files_to_delete)
    
    # Compute files to keep
    files_to_keep = [f.path for f in files if f not in files_to_delete]
    
    # Build cleanup plan
    return CleanupPlan(
        files_to_delete=[f.path for f in files_to_delete],
        total_size_to_free_bytes=total_size_to_free,
        files_to_keep=files_to_keep,
        reasons=reasons,
        created_at=now,
    )


def validate_retention_parameters(
    max_age_days: Optional[int] = None,
    max_archive_age_days: Optional[int] = None,
    max_total_size_bytes: Optional[int] = None,
) -> list[str]:
    """Validate retention parameters.
    
    Args:
        max_age_days: Maximum age for log files
        max_archive_age_days: Maximum age for archives
        max_total_size_bytes: Maximum total size
    
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    if max_age_days is not None and max_age_days < 1:
        errors.append(f"max_age_days must be >= 1 (got {max_age_days})")
    
    if max_archive_age_days is not None and max_archive_age_days < 1:
        errors.append(f"max_archive_age_days must be >= 1 (got {max_archive_age_days})")
    
    if max_total_size_bytes is not None and max_total_size_bytes <= 0:
        errors.append(f"max_total_size_bytes must be > 0 (got {max_total_size_bytes})")
    
    if (
        max_age_days is not None
        and max_archive_age_days is not None
        and max_archive_age_days < max_age_days
    ):
        errors.append(
            f"max_archive_age_days ({max_archive_age_days}) should be >= "
            f"max_age_days ({max_age_days})"
        )
    
    return errors

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit les règles métier de purge des logs et archives : quels fichiers supprimer selon les règles de rétention, comment calculer l'espace libéré, quels fichiers sont expirés. Ce module calcule un plan de purge mais n'effectue aucun I/O — l'exécution est déléguée à infrastructure/.
# Pourquoi dans domain/ (charte) :
# - C'est une règle métier : quand et quoi purger (politique de rétention)
# - Aucune dépendance externe (opère sur les modèles du domaine)
# - Fonctions pures : pas d'I/O, pas de suppression fichier
# - Testable avec des métadonnées en mémoire
# Ce qu'il ne contient PAS (règles projet) :
# ❌ Pas d'import depuis infrastructure/ (pas de suppression fichier)
# ❌ Pas d'import depuis interfaces/ (pas de rendu)
# ❌ Pas d'import depuis application/ (pas de cas d'usage)
# ❌ Pas de os.remove(), Path.unlink(), shutil.rmtree() — aucun I/O
# Points clés :
# - RetentionPolicy : définit les règles de rétention (âge max logs, âge max archives, taille totale max)
# - FileInfo : métadonnées d'un fichier (path, size, mtime, is_archive)
# - CleanupPlan : décrit quoi supprimer (liste de fichiers, taille à libérer, raisons)
# - Fonctions d'identification :
#   - identify_expired_files() : logs expirés
#   - identify_expired_archives() : archives expirées
#   - identify_oversized_files() : fichiers à supprimer pour respecter la limite de taille (plus anciens d'abord)
# - plan_cleanup() : point d'entrée principal qui calcule le plan complet
# - validate_retention_parameters() : validation des paramètres de rétention
# - Aucune dépendance externe : opère uniquement sur les modèles du domaine
# - Aucun I/O : ne lit ni ne supprime aucun fichier
# Comment il sera utilisé (aperçu) :
# - domain/logs/service.py appellera plan_cleanup() pour décider quels fichiers purger
# - application/commands/rotate_logs.py exécutera le plan via les ports (infrastructure)
# - infrastructure/storage/files/archive_store.py effectuera les suppressions réelles
# - interfaces/cli/actions.py affichera le plan de purge à l'utilisateur avant exécution (confirmation)
#---------------------------------------------------------------------->
