# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Persistence domain service.

Orchestrates business operations for persistence.
This service coordinates the domain modules (backup, restore, snapshots)
and enforces business rules by raising domain exceptions.
"""
from datetime import datetime
from typing import Optional
from omega_fire.domain.ip_blacklist.models import BanEntry
from omega_fire.domain.rules.models import FirewallRule
from omega_fire.domain.fail2ban.models import Jail
from omega_fire.domain.persistence.snapshots import (
    Snapshot,
    SnapshotScope,
    SnapshotStatus,
)
from omega_fire.domain.persistence.backup import (
    BackupRequest,
    BackupResult,
    plan_backup,
    validate_backup_data,
)
from omega_fire.domain.persistence.restore import (
    RestoreRequest,
    RestorePlan,
    plan_restore,
)
from omega_fire.domain.persistence.exceptions import (
    PersistenceError,
    InvalidSnapshotError,
    BackupError,
    RestoreError,
    SnapshotNotFoundError,
    CorruptedSnapshotError,
    IncompatibleVersionError,
    EmptyBackupError,
    InvalidRestoreScopeError,
)


class PersistenceService:
    """Domain service for persistence operations.
    
    This service orchestrates business logic for backup and restore.
    It enforces business rules and raises domain exceptions when rules
    are violated.
    """
    
    def create_backup(
        self,
        banned_ips: Optional[list[BanEntry]] = None,
        rules: Optional[list[FirewallRule]] = None,
        jails: Optional[list[Jail]] = None,
        scope: SnapshotScope = SnapshotScope.FULL,
        description: str = "",
        include_blacklist: bool = True,
        include_rules: bool = True,
        include_fail2ban: bool = True,
        hostname: Optional[str] = None,
        os_info: Optional[str] = None,
        app_version: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        origin: str = "manual",
    ) -> BackupResult:
        """Create a backup by planning a snapshot.
        
        This method validates the request, builds the snapshot in memory,
        and returns the result. It does NOT write any files.
        
        Args:
            banned_ips: List of banned IP entries
            rules: List of firewall rules
            jails: List of fail2ban jails
            scope: Snapshot scope (FULL, BLACKLIST_ONLY, etc.)
            description: Optional description
            include_blacklist: Whether to include blacklist (for CUSTOM scope)
            include_rules: Whether to include rules (for CUSTOM scope)
            include_fail2ban: Whether to include fail2ban (for CUSTOM scope)
            hostname: Optional hostname for metadata
            os_info: Optional OS info for metadata
            app_version: Optional app version for metadata
            timestamp: Optional timestamp (default: now)
        
        Returns:
            BackupResult with the constructed snapshot
        
        Raises:
            BackupError: If the request is invalid
            EmptyBackupError: If no data is available
            InvalidSnapshotError: If the snapshot is invalid
        """
        # Build request
        request = BackupRequest(
            scope=scope,
            description=description,
            include_blacklist=include_blacklist,
            include_rules=include_rules,
            include_fail2ban=include_fail2ban,
            timestamp=timestamp,
            origin=origin,
        )
        # Validate data before planning
        validation_errors = validate_backup_data(
            banned_ips=banned_ips,
            rules=rules,
            jails=jails,
        )
        if validation_errors:
            raise BackupError("data_validation", "; ".join(validation_errors))
        
        # Plan backup
        try:
            return plan_backup(
                request=request,
                banned_ips=banned_ips,
                rules=rules,
                jails=jails,
                hostname=hostname,
                os_info=os_info,
                app_version=app_version,
            )
        except (BackupError, EmptyBackupError, InvalidSnapshotError):
            raise
        except Exception as e:
            raise BackupError("planning", f"Unexpected error: {e}") from e
    
    def create_full_backup(
        self,
        banned_ips: list[BanEntry],
        rules: list[FirewallRule],
        jails: list[Jail],
        description: str = "",
        app_version: Optional[str] = None,
        origin: str = "manual",
    ) -> BackupResult:
        """Create a full backup of all components.
        
        Convenience method that creates a FULL scope backup.
        
        Args:
            banned_ips: List of banned IP entries
            rules: List of firewall rules
            jails: List of fail2ban jails
            description: Optional description
            app_version: Optional app version
            origin: Snapshot origin ("manual" or "auto_preset")
        
        Returns:
            BackupResult with the constructed snapshot
        """
        return self.create_backup(
            banned_ips=banned_ips,
            rules=rules,
            jails=jails,
            scope=SnapshotScope.FULL,
            description=description,
            app_version=app_version,
            origin=origin,
        )
    
    def create_blacklist_backup(
        self,
        banned_ips: list[BanEntry],
        description: str = "",
    ) -> BackupResult:
        """Create a backup of the blacklist only.
        
        Args:
            banned_ips: List of banned IP entries
            description: Optional description
        
        Returns:
            BackupResult with the constructed snapshot
        """
        return self.create_backup(
            banned_ips=banned_ips,
            scope=SnapshotScope.BLACKLIST_ONLY,
            description=description,
            include_rules=False,
            include_fail2ban=False,
        )
    
    def create_rules_backup(
        self,
        rules: list[FirewallRule],
        description: str = "",
    ) -> BackupResult:
        """Create a backup of the rules only.
        
        Args:
            rules: List of firewall rules
            description: Optional description
        
        Returns:
            BackupResult with the constructed snapshot
        """
        return self.create_backup(
            rules=rules,
            scope=SnapshotScope.RULES_ONLY,
            description=description,
            include_blacklist=False,
            include_fail2ban=False,
        )
    
    def create_fail2ban_backup(
        self,
        jails: list[Jail],
        description: str = "",
    ) -> BackupResult:
        """Create a backup of the fail2ban configuration only.
        
        Args:
            jails: List of fail2ban jails
            description: Optional description
        
        Returns:
            BackupResult with the constructed snapshot
        """
        return self.create_backup(
            jails=jails,
            scope=SnapshotScope.FAIL2BAN_ONLY,
            description=description,
            include_blacklist=False,
            include_rules=False,
        )
    
    def plan_restore(
        self,
        snapshot: Snapshot,
        restore_blacklist: bool = True,
        restore_rules: bool = True,
        restore_fail2ban: bool = True,
        dry_run: bool = False,
        current_app_version: str = "1.0",
    ) -> RestorePlan:
        """Plan a restore operation from a snapshot.
        
        This method validates the request, extracts domain objects from
        the snapshot, and returns a restore plan. It does NOT apply the
        restoration.
        
        Args:
            snapshot: Snapshot to restore from
            restore_blacklist: Whether to restore blacklist
            restore_rules: Whether to restore rules
            restore_fail2ban: Whether to restore fail2ban
            dry_run: If True, plan only without execution
            current_app_version: Current app version for compatibility check
        
        Returns:
            RestorePlan with reconstructed domain objects
        
        Raises:
            RestoreError: If the request is invalid
            CorruptedSnapshotError: If the snapshot is corrupted
            IncompatibleVersionError: If the snapshot version is incompatible
            InvalidRestoreScopeError: If the restore scope doesn't match
        """
        # Build request
        request = RestoreRequest(
            snapshot=snapshot,
            restore_blacklist=restore_blacklist,
            restore_rules=restore_rules,
            restore_fail2ban=restore_fail2ban,
            dry_run=dry_run,
        )
        
        # Plan restore
        try:
            return plan_restore(
                request=request,
                current_app_version=current_app_version,
            )
        except (RestoreError, CorruptedSnapshotError, IncompatibleVersionError, InvalidRestoreScopeError):
            raise
        except Exception as e:
            raise RestoreError(
                snapshot.metadata.snapshot_id,
                f"Unexpected error: {e}"
            ) from e
    
    def validate_snapshot(self, snapshot: Snapshot) -> list[str]:
        """Validate a snapshot for restore compatibility.
        
        Args:
            snapshot: Snapshot to validate
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Check metadata
        if not snapshot.metadata.is_valid():
            errors.append("Snapshot metadata is invalid")
        
        # Check status
        if snapshot.metadata.status != SnapshotStatus.COMPLETED:
            errors.append(
                f"Snapshot status is {snapshot.metadata.status.value}, not COMPLETED"
            )
        
        # Check content
        if snapshot.content.is_empty():
            errors.append("Snapshot content is empty")
        
        return errors
    
    def is_snapshot_valid(self, snapshot: Snapshot) -> bool:
        """Check if a snapshot is valid for restore.
        
        Args:
            snapshot: Snapshot to check
        
        Returns:
            True if the snapshot is valid
        """
        return len(self.validate_snapshot(snapshot)) == 0
    
    def get_snapshot_summary(self, snapshot: Snapshot) -> dict:
        """Get a complete summary of a snapshot.
        
        Args:
            snapshot: Snapshot to summarize
        
        Returns:
            Dictionary with metadata and content summaries
        """
        return snapshot.get_full_summary()

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Orchestration métier des opérations de persistance. Ce service coordonne les modules backup.py et restore.py, valide les requêtes, et lève les exceptions métier appropriées. Il ne fait aucun I/O — l'exécution réelle est déléguée à application/ et infrastructure/.
# Pourquoi dans domain/ (charte) :
# - C'est la logique métier centrale du sous-domaine persistence
# - Utilise uniquement les autres modules du domaine (snapshots, backup, restore, exceptions)
# - Lève les exceptions métier définies dans exceptions.py
# - Aucune dépendance externe (pas de subprocess, sqlite3, rich)
# Ce qu'il ne contient PAS (règles projet) :
# ❌ Pas d'import depuis infrastructure/ (pas de lecture/écriture fichier, pas de DB)
# ❌ Pas d'import depuis application/ (pas de cas d'usage)
# ❌ Pas d'import depuis interfaces/ (pas de rendu)
# ❌ Pas de logique d'exécution (juste l'orchestration métier)
# Points clés :
# - Orchestration métier : coordonne backup.py et restore.py
# - Validation stricte : vérifie les requêtes et les données avant de planifier
# - Exceptions métier : lève BackupError, RestoreError, EmptyBackupError, InvalidSnapshotError, etc.
# - Méthodes de convenance : create_full_backup(), create_blacklist_backup(), create_rules_backup(), create_fail2ban_backup()
# - Aucune dépendance externe : utilise uniquement les modules du domaine
# - Aucun I/O : ne lit ni n'écrit aucun fichier
# Comment il sera utilisé (aperçu) :
# - application/commands/backup_state.py instanciera PersistenceService et appellera create_backup()
# - application/commands/restore_state.py appellera plan_restore() pour construire le plan
# - application/queries/snapshot_info.py appellera get_snapshot_summary() pour afficher les infos
# - interfaces/cli/actions.py utilisera les méthodes de convenance pour proposer les options
#---------------------------------------------------------------------->
