# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Logs domain rotation logic.

Pure domain logic for log rotation rules.
This module defines WHEN and HOW to rotate logs, but does NOT
perform the actual file operations. Execution is delegated to
infrastructure/.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
from omega_fire.domain.logs.exceptions import InvalidRetentionError


class RotationStrategy(Enum):
    """Strategy for log rotation."""
    BY_SIZE = "by_size"           # Rotate when file exceeds size threshold
    BY_AGE = "by_age"             # Rotate when file exceeds age threshold
    BY_COUNT = "by_count"         # Rotate when line count exceeds threshold
    DAILY = "daily"               # Rotate every day
    WEEKLY = "weekly"             # Rotate every week
    MONTHLY = "monthly"           # Rotate every month


class CompressionFormat(Enum):
    """Compression format for rotated logs."""
    NONE = "none"
    GZIP = "gzip"
    BZIP2 = "bzip2"
    XZ = "xz"

@dataclass
class RotationPolicy:
    """Policy defining when and how to rotate logs."""
    strategy: RotationStrategy
    max_size_bytes: Optional[int] = None
    max_age_days: Optional[int] = None
    max_lines: Optional[int] = None
    max_rotations: int = 10
    compression: CompressionFormat = CompressionFormat.GZIP
    rotate_on_empty: bool = False
    
    def validate(self) -> list[str]:
        """Validate the rotation policy."""
        errors = []
        
        if self.strategy == RotationStrategy.BY_SIZE:
            if self.max_size_bytes is None or self.max_size_bytes <= 0:
                errors.append("max_size_bytes must be > 0 for BY_SIZE strategy")
        
        elif self.strategy == RotationStrategy.BY_AGE:
            if self.max_age_days is None or self.max_age_days <= 0:
                errors.append("max_age_days must be > 0 for BY_AGE strategy")
        
        elif self.strategy == RotationStrategy.BY_COUNT:
            if self.max_lines is None or self.max_lines <= 0:
                errors.append("max_lines must be > 0 for BY_COUNT strategy")
        
        if self.max_rotations < 1:
            errors.append("max_rotations must be >= 1")
        
        return errors
    
    def is_valid(self) -> bool:
        """Check if the policy is valid."""
        return len(self.validate()) == 0


@dataclass
class RotationPlan:
    """Plan of rotation operations."""
    log_path: str
    should_rotate: bool
    reason: Optional[str] = None
    archive_name: Optional[str] = None
    compress: bool = False
    compression_format: CompressionFormat = CompressionFormat.NONE
    rotations_to_delete: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    
    def is_empty(self) -> bool:
        """Check if no rotation is needed."""
        return not self.should_rotate



def should_rotate_by_size(
    file_size_bytes: int,
    max_size_bytes: int
) -> tuple[bool, Optional[str]]:
    """Check if a file should be rotated based on size.
    
    Args:
        file_size_bytes: Current file size in bytes
        max_size_bytes: Maximum allowed size in bytes
    
    Returns:
        Tuple of (should_rotate, reason)
    """
    if file_size_bytes >= max_size_bytes:
        return True, f"File size ({file_size_bytes} bytes) exceeds threshold ({max_size_bytes} bytes)"
    return False, None


def should_rotate_by_age(
    file_mtime: datetime,
    max_age_days: int,
    now: Optional[datetime] = None
) -> tuple[bool, Optional[str]]:
    """Check if a file should be rotated based on age.
    
    Args:
        file_mtime: File modification time
        max_age_days: Maximum allowed age in days
        now: Current time (default: datetime.now())
    
    Returns:
        Tuple of (should_rotate, reason)
    """
    if now is None:
        now = datetime.now()
    
    age = now - file_mtime
    max_age = timedelta(days=max_age_days)
    
    if age >= max_age:
        return True, f"File age ({age.days} days) exceeds threshold ({max_age_days} days)"
    return False, None


def should_rotate_by_count(
    line_count: int,
    max_lines: int
) -> tuple[bool, Optional[str]]:
    """Check if a file should be rotated based on line count.
    
    Args:
        line_count: Current line count
        max_lines: Maximum allowed line count
    
    Returns:
        Tuple of (should_rotate, reason)
    """
    if line_count >= max_lines:
        return True, f"Line count ({line_count}) exceeds threshold ({max_lines})"
    return False, None


def should_rotate_by_schedule(
    last_rotation: datetime,
    strategy: RotationStrategy,
    now: Optional[datetime] = None
) -> tuple[bool, Optional[str]]:
    """Check if a file should be rotated based on schedule.
    
    Args:
        last_rotation: Time of last rotation
        strategy: Rotation strategy (DAILY, WEEKLY, MONTHLY)
        now: Current time (default: datetime.now())
    
    Returns:
        Tuple of (should_rotate, reason)
    """
    if now is None:
        now = datetime.now()
    
    if strategy == RotationStrategy.DAILY:
        if now.date() > last_rotation.date():
            return True, "Daily rotation: new day started"
    
    elif strategy == RotationStrategy.WEEKLY:
        # Rotate if week number changed
        if now.isocalendar()[1] != last_rotation.isocalendar()[1]:
            return True, "Weekly rotation: new week started"
    
    elif strategy == RotationStrategy.MONTHLY:
        # Rotate if month changed
        if now.month != last_rotation.month or now.year != last_rotation.year:
            return True, "Monthly rotation: new month started"
    
    return False, None


def generate_archive_name(
    log_path: str,
    rotation_number: int,
    timestamp: datetime,
    compression: CompressionFormat = CompressionFormat.NONE
) -> str:
    """Generate the archive filename for a rotated log.
    
    Args:
        log_path: Original log file path
        rotation_number: Rotation sequence number
        timestamp: Rotation timestamp
        compression: Compression format
    
    Returns:
        Archive filename (without directory path)
    """
    # Extract base name
    import os
    base_name = os.path.basename(log_path)
    
    # Format timestamp
    timestamp_str = timestamp.strftime("%Y%m%d-%H%M%S")
    
    # Build archive name
    archive_name = f"{base_name}.{timestamp_str}.{rotation_number}"
    
    # Add compression extension
    if compression == CompressionFormat.GZIP:
        archive_name += ".gz"
    elif compression == CompressionFormat.BZIP2:
        archive_name += ".bz2"
    elif compression == CompressionFormat.XZ:
        archive_name += ".xz"
    
    return archive_name


def compute_rotations_to_delete(
    existing_rotations: list[str],
    max_rotations: int
) -> list[str]:
    """Compute which old rotations should be deleted.
    
    Args:
        existing_rotations: List of existing rotation filenames (sorted oldest first)
        max_rotations: Maximum number of rotations to keep
    
    Returns:
        List of rotation filenames to delete
    """
    if len(existing_rotations) <= max_rotations:
        return []
    
    # Delete oldest rotations to stay within limit
    rotations_to_delete = existing_rotations[:len(existing_rotations) - max_rotations]
    return rotations_to_delete


def plan_rotation(
    log_path: str,
    policy: RotationPolicy,
    file_size_bytes: Optional[int] = None,
    file_mtime: Optional[datetime] = None,
    line_count: Optional[int] = None,
    last_rotation: Optional[datetime] = None,
    existing_rotations: Optional[list[str]] = None,
    rotation_number: int = 1,
    now: Optional[datetime] = None,
) -> RotationPlan:
    """Plan a log rotation operation.
    
    This function determines if rotation is needed and what operations
    should be performed, but does NOT execute them.
    
    Args:
        log_path: Path to the log file
        policy: Rotation policy to apply
        file_size_bytes: Current file size (for BY_SIZE strategy)
        file_mtime: File modification time (for BY_AGE strategy)
        line_count: Current line count (for BY_COUNT strategy)
        last_rotation: Time of last rotation (for DAILY/WEEKLY/MONTHLY)
        existing_rotations: List of existing rotation filenames
        rotation_number: Sequence number for this rotation
        now: Current time (default: datetime.now())
    
    Returns:
        RotationPlan describing what needs to be done
    """
    if now is None:
        now = datetime.now()
    
    if existing_rotations is None:
        existing_rotations = []
    
    should_rotate = False
    reason = None
    
    # Check rotation condition based on strategy
    if policy.strategy == RotationStrategy.BY_SIZE:
        if file_size_bytes is not None and policy.max_size_bytes is not None:
            should_rotate, reason = should_rotate_by_size(file_size_bytes, policy.max_size_bytes)
    
    elif policy.strategy == RotationStrategy.BY_AGE:
        if file_mtime is not None and policy.max_age_days is not None:
            should_rotate, reason = should_rotate_by_age(file_mtime, policy.max_age_days, now)
    
    elif policy.strategy == RotationStrategy.BY_COUNT:
        if line_count is not None and policy.max_lines is not None:
            should_rotate, reason = should_rotate_by_count(line_count, policy.max_lines)
    
    elif policy.strategy in (RotationStrategy.DAILY, RotationStrategy.WEEKLY, RotationStrategy.MONTHLY):
        if last_rotation is not None:
            should_rotate, reason = should_rotate_by_schedule(last_rotation, policy.strategy, now)
    
    # If no rotation needed, return empty plan
    if not should_rotate:
        return RotationPlan(
            log_path=log_path,
            should_rotate=False,
        )
    
    # Generate archive name
    archive_name = generate_archive_name(
        log_path=log_path,
        rotation_number=rotation_number,
        timestamp=now,
        compression=policy.compression,
    )
    
    # Compute rotations to delete
    rotations_to_delete = compute_rotations_to_delete(
        existing_rotations=existing_rotations,
        max_rotations=policy.max_rotations,
    )
    
    # Build rotation plan
    return RotationPlan(
        log_path=log_path,
        should_rotate=True,
        reason=reason,
        archive_name=archive_name,
        compress=(policy.compression != CompressionFormat.NONE),
        compression_format=policy.compression,
        rotations_to_delete=rotations_to_delete,
        created_at=now,
    )

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit les règles métier de rotation des logs : quand tourner un fichier (par taille, par âge), comment nommer les archives, combien de rotations garder, etc. Ce module calcule des plans de rotation mais n'effectue aucun I/O — l'exécution est déléguée à infrastructure/.
# Pourquoi dans domain/ (charte) :
# - C'est une règle métier : quand et comment tourner les logs
# - Aucune dépendance externe (opère sur les modèles du domaine)
# - Fonctions pures : pas d'I/O, pas de manipulation fichier
# - Testable avec des métadonnées en mémoire
# Ce qu'il ne contient PAS (règles projet) :
# ❌ Pas d'import depuis infrastructure/ (pas de manipulation fichier)
# ❌ Pas d'import depuis interfaces/ (pas de rendu)
# ❌ Pas d'import depuis application/ (pas de cas d'usage)
# ❌ Pas de os.rename(), shutil.move(), Path.write() — aucun I/O
# Points clés :
# - RotationPolicy : définit la stratégie (BY_SIZE, BY_AGE, BY_COUNT, DAILY, WEEKLY, MONTHLY) et les paramètres
# - RotationPlan : décrit quoi faire (rotation nécessaire, nom d'archive, compression, rotations à supprimer)
# - Fonctions de décision : should_rotate_by_size(), should_rotate_by_age(), should_rotate_by_count(), should_rotate_by_schedule()
# - generate_archive_name() : génère le nom d'archive avec timestamp et extension de compression
# - compute_rotations_to_delete() : calcule quelles anciennes rotations supprimer pour respecter max_rotations
# - plan_rotation() : point d'entrée principal qui calcule le plan complet
# - Aucune dépendance externe : opère uniquement sur les modèles du domaine
# - Aucun I/O : ne lit ni n'écrit aucun fichier
# Comment il sera utilisé (aperçu) :
# - domain/logs/service.py appellera plan_rotation() pour décider si un fichier doit être tourné
# - application/commands/rotate_logs.py exécutera le plan via les ports (infrastructure)
# - infrastructure/storage/files/archive_store.py effectuera les opérations réelles (rename, compress, delete)
# - interfaces/cli/actions.py affichera le plan de rotation à l'utilisateur avant exécution
#---------------------------------------------------------------------->
