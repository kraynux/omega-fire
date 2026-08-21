# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Persistence domain restore logic.

Pure domain logic for restore operations.
This module defines HOW to extract data from a snapshot and reconstruct
domain objects, but does NOT read files, apply bans, or modify system state.
Execution is delegated to application/ and infrastructure/.
"""
from datetime import datetime
from typing import Optional
from omega_fire.domain.ip_blacklist.models import BanEntry, BanStatus, BanSource
from omega_fire.domain.rules.models import (
    FirewallRule, RuleAction, RuleChain, RuleProtocol, RuleFamily,
)
from omega_fire.domain.fail2ban.models import Jail, JailConfig, JailStatus, JailManagedBy
from omega_fire.domain.persistence.snapshots import (
    Snapshot,
    SnapshotScope,
    SnapshotStatus,
)
from omega_fire.domain.persistence.exceptions import (
    RestoreError,
    SnapshotNotFoundError,
    CorruptedSnapshotError,
    IncompatibleVersionError,
    InvalidRestoreScopeError,
)


class RestoreRequest:
    """Request object for a restore operation.
    
    Describes what should be restored from a snapshot, without performing any I/O.
    """
    def __init__(
        self,
        snapshot: Snapshot,
        restore_blacklist: bool = True,
        restore_rules: bool = True,
        restore_fail2ban: bool = True,
        dry_run: bool = False,
    ):
        self.snapshot = snapshot
        self.restore_blacklist = restore_blacklist
        self.restore_rules = restore_rules
        self.restore_fail2ban = restore_fail2ban
        self.dry_run = dry_run
    
    def validate(self) -> list[str]:
        """Validate the restore request.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Check snapshot validity
        if not self.snapshot.is_valid():
            errors.append("Snapshot is not valid")
        
        # Check scope compatibility
        scope = self.snapshot.metadata.scope
        
        if self.restore_blacklist and scope == SnapshotScope.RULES_ONLY:
            errors.append("Cannot restore blacklist from rules-only snapshot")
        
        if self.restore_rules and scope == SnapshotScope.BLACKLIST_ONLY:
            errors.append("Cannot restore rules from blacklist-only snapshot")
        
        if self.restore_fail2ban and scope in (SnapshotScope.BLACKLIST_ONLY, SnapshotScope.RULES_ONLY):
            errors.append("Cannot restore fail2ban from blacklist/rules-only snapshot")
        
        # Check that at least one component is requested
        if not (self.restore_blacklist or self.restore_rules or self.restore_fail2ban):
            errors.append("At least one component must be selected for restore")
        
        return errors
    
    def is_valid(self) -> bool:
        """Check if the request is valid."""
        return len(self.validate()) == 0


class RestorePlan:
    """Plan for a restore operation.
    
    Contains the reconstructed domain objects and metadata about
    what will be restored. Does NOT execute the restore.
    """
    def __init__(
        self,
        snapshot: Snapshot,
        banned_ips: list[BanEntry],
        rules: list[FirewallRule],
        jails: list[Jail],
        dry_run: bool = False,
    ):
        self.snapshot = snapshot
        self.banned_ips = banned_ips
        self.rules = rules
        self.jails = jails
        self.dry_run = dry_run
    
    @property
    def snapshot_id(self) -> str:
        return self.snapshot.metadata.snapshot_id
    
    def total_items(self) -> int:
        """Get the total number of items to restore."""
        return len(self.banned_ips) + len(self.rules) + len(self.jails)
    
    def get_summary(self) -> dict:
        """Get a summary of the restore plan."""
        return {
            "snapshot_id": self.snapshot_id,
            "banned_ips_count": len(self.banned_ips),
            "rules_count": len(self.rules),
            "jails_count": len(self.jails),
            "total_items": self.total_items(),
            "dry_run": self.dry_run,
        }


def extract_blacklist_from_snapshot(snapshot: Snapshot) -> list[BanEntry]:
    """Extract BanEntry objects from a snapshot.
    
    Args:
        snapshot: Snapshot containing blacklist data
    
    Returns:
        List of BanEntry objects
    
    Raises:
        RestoreError: If snapshot has no blacklist data
    """
    if snapshot.content.blacklist is None:
        raise RestoreError(
            snapshot.metadata.snapshot_id,
            "Snapshot contains no blacklist data"
        )
    
    banned_ips = []
    
    for entry in snapshot.content.blacklist.banned_ips:
        # Map status string to BanStatus enum
        status_str = entry.get("status", "active")
        try:
            status = BanStatus(status_str)
        except ValueError:
            status = BanStatus.ACTIVE
        
        # Map backend to BanSource
        backend = entry.get("backend", "nftables")
        source = BanSource.MANUAL  # Default for restored bans
        
        ban = BanEntry(
            ip=entry["ip"],
            backend=backend,
            status=status,
            source=source,
            comment=entry.get("comment", ""),
            banned_at=snapshot.metadata.created_at,
        )
        banned_ips.append(ban)
    
    return banned_ips


def extract_rules_from_snapshot(snapshot: Snapshot) -> list[FirewallRule]:
    """Extract FirewallRule objects from a snapshot.
    
    Args:
        snapshot: Snapshot containing rules data
    
    Returns:
        List of FirewallRule objects
    
    Raises:
        RestoreError: If snapshot has no rules data
    """
    if snapshot.content.rules is None:
        raise RestoreError(
            snapshot.metadata.snapshot_id,
            "Snapshot contains no rules data"
        )
    
    rules = []
    
    for entry in snapshot.content.rules.rules:
        # Map action string to RuleAction enum
        action_str = entry.get("action", "accept")
        try:
            action = RuleAction(action_str)
        except ValueError:
            action = RuleAction.ACCEPT
        
        # Map chain string to RuleChain enum
        chain_str = entry.get("chain", "input")
        try:
            chain = RuleChain(chain_str)
        except ValueError:
            chain = RuleChain.INPUT
        
        # Map protocol string to RuleProtocol enum
        protocol_str = entry.get("protocol")
        protocol = None
        if protocol_str:
            try:
                protocol = RuleProtocol(protocol_str)
            except ValueError:
                protocol = None
        
        # Parse port (could be "80" or "80-443" or None)
        port_str = entry.get("port")
        port_start = None
        port_end = None
        if port_str and port_str != "?":
            if "-" in port_str:
                parts = port_str.split("-")
                try:
                    port_start = int(parts[0])
                    port_end = int(parts[1])
                except (ValueError, IndexError):
                    pass
            else:
                try:
                    port_start = int(port_str)
                    port_end = port_start
                except ValueError:
                    pass
        
        # Default to INET family
        family = RuleFamily.INET
        
        rule = FirewallRule(
            backend=entry.get("backend", "nftables"),
            family=family,
            table_name="filter",
            chain=chain,
            action=action,
            protocol=protocol,
            port_start=port_start,
            port_end=port_end,
            source_cidr=entry.get("source"),
            dest_cidr=entry.get("destination"),
            comment=entry.get("comment", ""),
        )
        rules.append(rule)
    
    return rules


def extract_jails_from_snapshot(snapshot: Snapshot) -> list[Jail]:
    """Extract Jail objects from a snapshot.
    
    Args:
        snapshot: Snapshot containing fail2ban data
    
    Returns:
        List of Jail objects
    
    Raises:
        RestoreError: If snapshot has no fail2ban data
    """
    if snapshot.content.fail2ban is None:
        raise RestoreError(
            snapshot.metadata.snapshot_id,
            "Snapshot contains no fail2ban data"
        )
    
    jails = []
    
    for entry in snapshot.content.fail2ban.jails:
        # Map status string to JailStatus enum
        status_str = entry.get("status", "active")
        try:
            status = JailStatus(status_str)
        except ValueError:
            status = JailStatus.ACTIVE
        
        # Build JailConfig
        config = JailConfig(
            jail_name=entry["name"],
            log_path="/var/log/auth.log",  # Default, will be overridden by infrastructure
            maxretry=entry.get("maxretry", 5),
            bantime=entry.get("bantime", 3600),
            findtime=entry.get("findtime", 600),
        )
        
        jail = Jail(
            name=entry["name"],
            config=config,
            status=status,
            managed_by=JailManagedBy.EXTERNAL,
            currently_banned=0,  # Sera mis à jour par infrastructure après restauration
            total_banned=0,
        )
        jails.append(jail)
    
    return jails


def validate_restore_compatibility(
    snapshot: Snapshot,
    current_app_version: str,
) -> list[str]:
    """Validate that a snapshot is compatible with the current application.
    
    Args:
        snapshot: Snapshot to validate
        current_app_version: Current application version
    
    Returns:
        List of compatibility error messages (empty if compatible)
    """
    errors = []
    
    # Check snapshot status
    if snapshot.metadata.status != SnapshotStatus.COMPLETED:
        errors.append(
            f"Snapshot status is {snapshot.metadata.status.value}, not COMPLETED"
        )
    
    # Check version compatibility (simple check: major version must match)
    snapshot_version = snapshot.metadata.version
    if snapshot_version and current_app_version:
        # Extract major version (e.g., "1.0" from "1.0.0")
        snapshot_major = snapshot_version.split(".")[0]
        app_major = current_app_version.split(".")[0]
        
        if snapshot_major != app_major:
            errors.append(
                f"Version mismatch: snapshot={snapshot_version}, app={current_app_version}"
            )
    
    return errors


def plan_restore(
    request: RestoreRequest,
    current_app_version: str = "1.0",
) -> RestorePlan:
    """Plan a restore operation by extracting domain objects from a snapshot.
    
    This function reconstructs the logical domain objects without
    applying them to the system. The application layer will handle
    the actual restoration.
    
    Args:
        request: Restore request describing what to restore
        current_app_version: Current application version for compatibility check
    
    Returns:
        RestorePlan with reconstructed domain objects
    
    Raises:
        RestoreError: If the request is invalid
        CorruptedSnapshotError: If the snapshot is corrupted
        IncompatibleVersionError: If the snapshot version is incompatible
        InvalidRestoreScopeError: If the restore scope doesn't match snapshot content
    """
    # Validate request
    errors = request.validate()
    if errors:
        raise RestoreError(
            request.snapshot.metadata.snapshot_id,
            "; ".join(errors)
        )
    
    # Check compatibility
    compat_errors = validate_restore_compatibility(
        request.snapshot,
        current_app_version
    )
    if compat_errors:
        # Check if it's a version mismatch
        if any("Version mismatch" in err for err in compat_errors):
            raise IncompatibleVersionError(
                request.snapshot.metadata.version,
                current_app_version
            )
        raise CorruptedSnapshotError(
            request.snapshot.metadata.snapshot_id,
            "; ".join(compat_errors)
        )
    
    # Extract domain objects
    banned_ips = []
    rules = []
    jails = []
    
    if request.restore_blacklist and request.snapshot.content.blacklist:
        try:
            banned_ips = extract_blacklist_from_snapshot(request.snapshot)
        except RestoreError as e:
            raise InvalidRestoreScopeError(
                "blacklist",
                "snapshot has no blacklist data"
            ) from e
    
    if request.restore_rules and request.snapshot.content.rules:
        try:
            rules = extract_rules_from_snapshot(request.snapshot)
        except RestoreError as e:
            raise InvalidRestoreScopeError(
                "rules",
                "snapshot has no rules data"
            ) from e
    
    if request.restore_fail2ban and request.snapshot.content.fail2ban:
        try:
            jails = extract_jails_from_snapshot(request.snapshot)
        except RestoreError as e:
            raise InvalidRestoreScopeError(
                "fail2ban",
                "snapshot has no fail2ban data"
            ) from e
    
    return RestorePlan(
        snapshot=request.snapshot,
        banned_ips=banned_ips,
        rules=rules,
        jails=jails,
        dry_run=request.dry_run,
    )

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit la logique métier de restauration : comment extraire les données d'un Snapshot pour reconstruire les objets métier (BanEntry, FirewallRule, Jail), comment valider la compatibilité d'un snapshot, comment planifier une restauration. Ce module ne fait aucun I/O — il construit uniquement des plans de restauration en mémoire. L'exécution réelle (application des bans, règles, jails) est déléguée à application/ et infrastructure/.
# Pourquoi dans domain/ (charte) :
# - C'est une règle métier : comment reconstruire l'état à partir d'un snapshot
# - Aucune dépendance externe (opère sur les modèles du domaine)
# - Fonctions pures : pas d'I/O, pas de lecture fichier
# - Testable en mémoire pure
# Ce qu'il ne contient PAS (règles projet) :
# ❌ Pas d'import depuis infrastructure/ (pas de lecture fichier, pas d'application des bans)
# ❌ Pas d'import depuis interfaces/ (pas de rendu)
# ❌ Pas d'import depuis application/ (pas de cas d'usage)
# ❌ Pas de open(), tarfile, Path.read() — aucun I/O
# Points clés :
# - RestoreRequest : objet de requête décrivant quoi restaurer (composants, dry_run)
# - RestorePlan : plan de restauration avec les objets métier reconstruits
# - extract_blacklist_from_snapshot() : reconstruit les BanEntry depuis le snapshot
# - extract_rules_from_snapshot() : reconstruit les FirewallRule depuis le snapshot
# - extract_jails_from_snapshot() : reconstruit les Jail depuis le snapshot
# - validate_restore_compatibility() : vérifie que le snapshot est compatible (statut, version)
# - plan_restore() : point d'entrée principal qui construit le plan complet
# - Gestion des enums : conversion robuste des strings vers les enums (BanStatus, RuleAction, etc.)
# - Parsing des ports : gestion des formats "80", "80-443", ou None
# - Aucune dépendance externe : opère uniquement sur les modèles du domaine
# - Aucun I/O : ne lit ni n'applique aucun état système
# Comment il sera utilisé (aperçu) :
# application/commands/restore_state.py appellera plan_restore() pour construire le plan
# application/commands/restore_state.py appliquera ensuite les BanEntry, FirewallRule, Jail via les ports
# interfaces/cli/actions.py proposera les options de restauration à l'utilisateur
# interfaces/cli/actions.py affichera le résumé du plan avant exécution
#---------------------------------------------------------------------->
