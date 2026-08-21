# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Persistence domain snapshots.

Pure domain logic for system state snapshots.
This module defines what a snapshot IS, not how it is created
or restored. Snapshots capture the state of the firewall system
at a given point in time.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Any


class SnapshotStatus(Enum):
    """Status of a snapshot."""
    PENDING = "pending"           # Snapshot creation in progress
    COMPLETED = "completed"       # Snapshot successfully created
    FAILED = "failed"             # Snapshot creation failed
    CORRUPTED = "corrupted"       # Snapshot file is damaged
    RESTORED = "restored"         # Snapshot has been restored


class SnapshotScope(Enum):
    """Scope of what the snapshot includes."""
    FULL = "full"                 # Complete system state
    BLACKLIST_ONLY = "blacklist"  # Only IP blacklist
    RULES_ONLY = "rules"          # Only firewall rules
    FAIL2BAN_ONLY = "fail2ban"    # Only fail2ban configuration
    CUSTOM = "custom"             # User-selected components

class SnapshotOrigin(Enum):
    """Origin of a snapshot: how and why it was created.

    Determines the retention policy:
    - MANUAL: created explicitly via menu 7.1, kept indefinitely.
    - AUTO_PRESET: created automatically before a firewall preset
      change (menu 3.4), subject to automatic rotation (max 5).
    """
    MANUAL = "manual"
    AUTO_PRESET = "auto_preset"


@dataclass
class SnapshotMetadata:
    """Metadata about a snapshot.
    
    Contains information about when, how, and what was snapshotted.
    Does not contain the actual data — that is in SnapshotContent.
    """
    snapshot_id: str
    created_at: datetime
    scope: SnapshotScope
    description: str = ""
    origin: SnapshotOrigin = SnapshotOrigin.MANUAL
    version: str = "1.0"
    source_system: str = "omega-fire"
    
    # Optional context
    hostname: Optional[str] = None
    os_info: Optional[str] = None
    app_version: Optional[str] = None
    
    # Status tracking
    status: SnapshotStatus = SnapshotStatus.COMPLETED
    error_message: Optional[str] = None
    
    # File information (set after creation)
    file_path: Optional[str] = None
    file_size_bytes: Optional[int] = None
    checksum: Optional[str] = None  # SHA256
    
    def is_valid(self) -> bool:
        """Check if the snapshot metadata is valid.
    
        Returns:
            True if all required fields are present
        """
        return (
            self.snapshot_id != ""
            and self.status == SnapshotStatus.COMPLETED
        )
    
    def age_days(self, now: Optional[datetime] = None) -> float:
        """Calculate the age of the snapshot in days.
        
        Args:
            now: Current time (default: datetime.now())
        
        Returns:
            Age in days (float)
        """
        if now is None:
            now = datetime.now()
        delta = now - self.created_at
        return delta.total_seconds() / 86400.0
    
    def is_recent(self, max_age_days: int = 7, now: Optional[datetime] = None) -> bool:
            """Check if the snapshot is recent.
    
            Args:
                max_age_days: Maximum age in days (default: 7)
                now: Current time (default: datetime.now())
    
            Returns:
                True if the snapshot is within the age limit
            """
            if now is None:
                now = datetime.now()
            return self.age_days(now) <= max_age_days
    
    def get_summary(self) -> dict[str, Any]:
        """Get a summary of the snapshot metadata.
        
        Returns:
            Dictionary with key information
        """
        return {
            "id": self.snapshot_id,
            "created_at": self.created_at.isoformat(),
            "scope": self.scope.value,
            "status": self.status.value,
            "description": self.description,
            "file_path": self.file_path,
            "file_size_mb": (
                self.file_size_bytes / (1024 * 1024)
                if self.file_size_bytes else None
            ),
        }


@dataclass
class BlacklistSnapshot:
    """Snapshot of the IP blacklist state.
    
    Contains all banned IPs with their metadata.
    """
    banned_ips: list[dict[str, Any]] = field(default_factory=list)
    count: int = 0
    
    def add_entry(self, ip: str, backend: str, status: str, comment: str = "") -> None:
        """Add a banned IP entry to the snapshot.
        
        Args:
            ip: IP address
            backend: Backend name (nftables, iptables, fail2ban)
            status: Ban status
            comment: Optional comment
        """
        self.banned_ips.append({
            "ip": ip,
            "backend": backend,
            "status": status,
            "comment": comment,
        })
        self.count = len(self.banned_ips)


@dataclass
class RulesSnapshot:
    """Snapshot of the firewall rules state.
    
    Contains all firewall rules with their configuration.
    """
    rules: list[dict[str, Any]] = field(default_factory=list)
    count: int = 0
    
    def add_rule(
        self,
        backend: str,
        chain: str,
        action: str,
        protocol: Optional[str] = None,
        port: Optional[str] = None,
        source: Optional[str] = None,
        destination: Optional[str] = None,
        comment: str = "",
        order: int = 0,
    ) -> None:
        """Add a firewall rule to the snapshot.
        
        Args:
            backend: Backend name (nftables, iptables)
            chain: Chain name (input, output, forward)
            action: Rule action (accept, drop, reject)
            protocol: Optional protocol (tcp, udp, icmp)
            port: Optional port or port range
            source: Optional source CIDR
            destination: Optional destination CIDR
            comment: Optional comment
        """
        self.rules.append({
            "backend": backend,
            "chain": chain,
            "action": action,
            "protocol": protocol,
            "port": port,
            "source": source,
            "destination": destination,
            "comment": comment,
            "order": order,
        })
        self.count = len(self.rules)


@dataclass
class Fail2banSnapshot:
    """Snapshot of the fail2ban state.
    
    Contains all jails with their configuration and banned IPs.
    """
    jails: list[dict[str, Any]] = field(default_factory=list)
    count: int = 0
    
    def add_jail(
        self,
        name: str,
        status: str,
        maxretry: int,
        bantime: int,
        findtime: int,
        banned_ips: list[str],
    ) -> None:
        """Add a jail to the snapshot.
        
        Args:
            name: Jail name
            status: Jail status (active, disabled)
            maxretry: Maximum retry count
            bantime: Ban time in seconds
            findtime: Find time in seconds
            banned_ips: List of currently banned IPs
        """
        self.jails.append({
            "name": name,
            "status": status,
            "maxretry": maxretry,
            "bantime": bantime,
            "findtime": findtime,
            "banned_ips": banned_ips,
        })
        self.count = len(self.jails)


@dataclass
class SnapshotContent:
    """Complete content of a snapshot.
    
    Aggregates all component snapshots into a single structure.
    """
    blacklist: Optional[BlacklistSnapshot] = None
    rules: Optional[RulesSnapshot] = None
    fail2ban: Optional[Fail2banSnapshot] = None
    
    # Metadata about the snapshot
    total_bans: int = 0
    total_rules: int = 0
    total_jails: int = 0
    
    def compute_totals(self) -> None:
        """Compute total counts from component snapshots."""
        if self.blacklist:
            self.total_bans = self.blacklist.count
        if self.rules:
            self.total_rules = self.rules.count
        if self.fail2ban:
            self.total_jails = self.fail2ban.count
    
    def is_empty(self) -> bool:
        """Check if the snapshot contains no data.
        
        Returns:
            True if all components are None or empty
        """
        return (
            (self.blacklist is None or self.blacklist.count == 0)
            and (self.rules is None or self.rules.count == 0)
            and (self.fail2ban is None or self.fail2ban.count == 0)
        )
    
    def get_summary(self) -> dict[str, int]:
        """Get a summary of the snapshot content.
        
        Returns:
            Dictionary with counts
        """
        return {
            "total_bans": self.total_bans,
            "total_rules": self.total_rules,
            "total_jails": self.total_jails,
        }


@dataclass
class Snapshot:
    """Complete snapshot with metadata and content.
    
    This is the main data structure representing a system state backup.
    """
    metadata: SnapshotMetadata
    content: SnapshotContent
    
    def is_valid(self) -> bool:
        """Check if the snapshot is valid.
        
        Returns:
            True if metadata is valid and content is not empty
        """
        return self.metadata.is_valid() and not self.content.is_empty()
    
    def get_full_summary(self) -> dict[str, Any]:
        """Get a complete summary of the snapshot.
        
        Returns:
            Dictionary with metadata and content summaries
        """
        return {
            "metadata": self.metadata.get_summary(),
            "content": self.content.get_summary(),
        }


def create_snapshot_id(timestamp: Optional[datetime] = None) -> str:
    """Generate a unique snapshot ID based on timestamp.
    
    Args:
        timestamp: Timestamp to use (default: datetime.now())
    
    Returns:
        Snapshot ID string (format: snapshot_YYYYMMDD_HHMMSS)
    """
    if timestamp is None:
        timestamp = datetime.now()
    return f"snapshot_{timestamp.strftime('%Y%m%d_%H%M%S')}"


def filter_snapshots_by_scope(
    snapshots: list[Snapshot],
    scope: SnapshotScope,
) -> list[Snapshot]:
    """Filter snapshots by scope.
    
    Args:
        snapshots: List of snapshots to filter
        scope: Scope to match
    
    Returns:
        List of snapshots with the specified scope
    """
    return [s for s in snapshots if s.metadata.scope == scope]


def filter_snapshots_by_status(
    snapshots: list[Snapshot],
    status: SnapshotStatus,
) -> list[Snapshot]:
    """Filter snapshots by status.
    
    Args:
        snapshots: List of snapshots to filter
        status: Status to match
    
    Returns:
        List of snapshots with the specified status
    """
    return [s for s in snapshots if s.metadata.status == status]


def get_most_recent_snapshot(
    snapshots: list[Snapshot],
) -> Optional[Snapshot]:
    """Get the most recent snapshot.
    
    Args:
        snapshots: List of snapshots
    
    Returns:
        Most recent snapshot, or None if list is empty
    """
    if not snapshots:
        return None
    return max(snapshots, key=lambda s: s.metadata.created_at)


def get_oldest_snapshot(
    snapshots: list[Snapshot],
) -> Optional[Snapshot]:
    """Get the oldest snapshot.
    
    Args:
        snapshots: List of snapshots
    
    Returns:
        Oldest snapshot, or None if list is empty
    """
    if not snapshots:
        return None
    return min(snapshots, key=lambda s: s.metadata.created_at)


def filter_recent_snapshots(
    snapshots: list[Snapshot],
    max_age_days: int = 7,
) -> list[Snapshot]:
    """Filter to keep only recent snapshots.
    
    Args:
        snapshots: List of snapshots to filter
        max_age_days: Maximum age in days (default: 7)
    
    Returns:
        List of recent snapshots
    """
    return [s for s in snapshots if s.metadata.is_recent(max_age_days)]

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit les modèles métier pour les snapshots (sauvegardes d'état) : structure d'un snapshot, métadonnées, état du système à un instant T. Ce module ne fait aucun I/O — il décrit uniquement la structure des données.
# Pourquoi dans domain/ (charte) :
# - C'est une règle métier : qu'est-ce qu'un snapshot, comment le structurer
# - Aucune dépendance externe (juste dataclasses, datetime, typing)
# - Testable en mémoire pure
# - Utilisé par domain/persistence/backup.py et restore.py
# Ce qu'il ne contient PAS (règles projet) :
# ❌ Pas d'import depuis infrastructure/ (pas de lecture/écriture fichier, pas de tar.gz)
# ❌ Pas d'import depuis interfaces/ (pas de rendu)
# ❌ Pas d'import depuis application/ (pas de cas d'usage)
# ❌ Pas de open(), tarfile, Path.write() — aucun I/O
# Points clés :
# - SnapshotStatus : PENDING, COMPLETED, FAILED, CORRUPTED, RESTORED
# - SnapshotScope : FULL, BLACKLIST_ONLY, RULES_ONLY, FAIL2BAN_ONLY, CUSTOM
# - SnapshotMetadata : métadonnées du snapshot (ID, date, scope, origin, fichier, checksum)
# - SnapshotOrigin : MANUAL (menu 7.1, illimité) ou AUTO_PRESET (menu 3.4,
#   rotation automatique max 5) — utilisé par domain/persistence/rotation.py
# - BlacklistSnapshot : snapshot des IPs bannies
# - RulesSnapshot : snapshot des règles firewall
# - Fail2banSnapshot : snapshot des jails fail2ban
# - SnapshotContent : agrège les 3 types de snapshots
# - Snapshot : structure complète (metadata + content)
# - Fonctions utilitaires : create_snapshot_id(), filter_snapshots_by_scope(), get_most_recent_snapshot(), etc.
# - Aucune dépendance externe : utilise uniquement dataclasses, datetime, enum, typing
# - Aucun I/O : ne crée ni ne restaure aucun fichier
# Comment il sera utilisé (aperçu) :
# - domain/persistence/backup.py construira des Snapshot à partir de l'état actuel
# - domain/persistence/restore.py utilisera les Snapshot pour restaurer l'état
# - infrastructure/storage/files/archive_store.py écrira/lira les fichiers .tar.gz
# - application/commands/backup_state.py orchestrera la création de snapshots
#---------------------------------------------------------------------->
