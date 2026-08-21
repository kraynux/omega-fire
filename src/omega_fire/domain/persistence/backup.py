# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Persistence domain backup logic.

Pure domain logic for backup operations.
This module defines HOW to construct a backup snapshot from domain data,
but does NOT write files, create archives, or compute checksums.
Execution is delegated to infrastructure/.
"""
from datetime import datetime
from typing import Optional
from omega_fire.domain.ip_blacklist.models import BanEntry
from omega_fire.domain.rules.models import FirewallRule
from omega_fire.domain.fail2ban.models import Jail
from omega_fire.domain.persistence.snapshots import (
    Snapshot,
    SnapshotMetadata,
    SnapshotContent,
    SnapshotScope,
    SnapshotStatus,
    SnapshotOrigin,
    BlacklistSnapshot,
    RulesSnapshot,
    Fail2banSnapshot,
    create_snapshot_id,
)
from omega_fire.domain.persistence.exceptions import (
    BackupError,
    EmptyBackupError,
    InvalidSnapshotError,
)


class BackupRequest:
    """Request object for a backup operation.
    
    Describes what should be backed up, without performing any I/O.
    """
    def __init__(
        self,
        scope: SnapshotScope = SnapshotScope.FULL,
        description: str = "",
        include_blacklist: bool = True,
        include_rules: bool = True,
        include_fail2ban: bool = True,
        timestamp: Optional[datetime] = None,
        origin: str = "manual",
    ):
        self.scope = scope
        self.description = description
        self.include_blacklist = include_blacklist
        self.include_rules = include_rules
        self.include_fail2ban = include_fail2ban
        self.timestamp = timestamp or datetime.now()
        self.origin = origin
    
    def validate(self) -> list[str]:
        """Validate the backup request.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        if self.scope == SnapshotScope.CUSTOM:
            if not (self.include_blacklist or self.include_rules or self.include_fail2ban):
                errors.append("Custom scope must include at least one component")
        
        return errors
    
    def is_valid(self) -> bool:
        """Check if the request is valid."""
        return len(self.validate()) == 0


class BackupResult:
    """Result of a backup planning operation.
    
    Contains the constructed snapshot (in memory) and metadata about
    what was backed up. Does NOT contain file paths or checksums —
    those are set by infrastructure/ after writing.
    """
    def __init__(
        self,
        snapshot: Snapshot,
        blacklist_count: int = 0,
        rules_count: int = 0,
        fail2ban_count: int = 0,
    ):
        self.snapshot = snapshot
        self.blacklist_count = blacklist_count
        self.rules_count = rules_count
        self.fail2ban_count = fail2ban_count
    
    @property
    def snapshot_id(self) -> str:
        return self.snapshot.metadata.snapshot_id
    
    @property
    def scope(self) -> SnapshotScope:
        return self.snapshot.metadata.scope
    
    def total_items(self) -> int:
        """Get the total number of items backed up."""
        return self.blacklist_count + self.rules_count + self.fail2ban_count
    
    def get_summary(self) -> dict:
        """Get a summary of the backup result."""
        return {
            "snapshot_id": self.snapshot_id,
            "scope": self.scope.value,
            "blacklist_count": self.blacklist_count,
            "rules_count": self.rules_count,
            "fail2ban_count": self.fail2ban_count,
            "total_items": self.total_items(),
            "created_at": self.snapshot.metadata.created_at.isoformat(),
        }


def build_blacklist_snapshot(banned_ips: list[BanEntry]) -> BlacklistSnapshot:
    """Build a blacklist snapshot from BanEntry objects.
    
    Args:
        banned_ips: List of banned IP entries
    
    Returns:
        BlacklistSnapshot with all entries
    """
    snapshot = BlacklistSnapshot()
    
    for ban in banned_ips:
        snapshot.add_entry(
            ip=ban.ip,
            backend=ban.backend,
            status=ban.status.value,
            comment=ban.comment or "",
        )
    
    return snapshot


def build_rules_snapshot(rules: list[FirewallRule]) -> RulesSnapshot:
    """Build a rules snapshot, preserving live evaluation order.

    CRITICAL: rules are evaluated in order by nftables/iptables — a
    catch-all DROP placed before ACCEPT rules blocks everything,
    regardless of what follows. The 'order' field records each rule's
    position in the live ruleset (as returned by list_rules(), which
    reflects real kernel evaluation order) so restoration can reapply
    rules in the exact same relative order, per chain.
    """
    snapshot = RulesSnapshot()
    
    for index, rule in enumerate(rules):
        snapshot.add_rule(
            backend=rule.backend,
            chain=rule.chain.value,
            action=rule.action.value,
            protocol=rule.protocol.value if rule.protocol else None,
            port=rule.get_port_display(),
            source=rule.source_cidr,
            destination=rule.dest_cidr,
            comment=rule.comment or "",
            order=index,
        )
    
    return snapshot

def build_fail2ban_snapshot(jails: list[Jail]) -> Fail2banSnapshot:
    """Build a fail2ban snapshot from Jail objects.
    
    Args:
        jails: List of fail2ban jails
    
    Returns:
        Fail2banSnapshot with all jails
    """
    snapshot = Fail2banSnapshot()
    
    for jail in jails:
        snapshot.add_jail(
           name=jail.name,
           status=jail.status.value,
           maxretry=jail.config.maxretry,
           bantime=jail.config.bantime,
           findtime=jail.config.findtime,
           banned_ips=[],  # Jail n'a pas de liste d'IPs bannies, juste des compteurs
        )
    
    return snapshot


def plan_backup(
    request: BackupRequest,
    banned_ips: Optional[list[BanEntry]] = None,
    rules: Optional[list[FirewallRule]] = None,
    jails: Optional[list[Jail]] = None,
    hostname: Optional[str] = None,
    os_info: Optional[str] = None,
    app_version: Optional[str] = None,
) -> BackupResult:
    """Plan a backup operation by constructing a Snapshot in memory.
    
    This function builds the logical snapshot structure without
    writing any files. The infrastructure layer will handle
    serialization, archiving, and checksum computation.
    
    Args:
        request: Backup request describing what to include
        banned_ips: List of banned IP entries (if include_blacklist)
        rules: List of firewall rules (if include_rules)
        jails: List of fail2ban jails (if include_fail2ban)
        hostname: Optional hostname for metadata
        os_info: Optional OS info for metadata
        app_version: Optional app version for metadata
    
    Returns:
        BackupResult with the constructed snapshot
    
    Raises:
        BackupError: If the request is invalid
        EmptyBackupError: If no data is available to backup
    """
    # Validate request
    errors = request.validate()
    if errors:
        raise BackupError("validation", "; ".join(errors))
    
    # Determine actual scope
    scope = request.scope
    if scope == SnapshotScope.CUSTOM:
        # Keep custom scope
        pass
    elif scope == SnapshotScope.BLACKLIST_ONLY:
        request.include_rules = False
        request.include_fail2ban = False
    elif scope == SnapshotScope.RULES_ONLY:
        request.include_blacklist = False
        request.include_fail2ban = False
    elif scope == SnapshotScope.FAIL2BAN_ONLY:
        request.include_blacklist = False
        request.include_rules = False
    
    # Build content
    content = SnapshotContent()
    blacklist_count = 0
    rules_count = 0
    fail2ban_count = 0
    
    # Blacklist
    if request.include_blacklist and banned_ips is not None:
        content.blacklist = build_blacklist_snapshot(banned_ips)
        blacklist_count = content.blacklist.count
    
    # Rules
    if request.include_rules and rules is not None:
        content.rules = build_rules_snapshot(rules)
        rules_count = content.rules.count
    
    # Fail2ban
    if request.include_fail2ban and jails is not None:
        content.fail2ban = build_fail2ban_snapshot(jails)
        fail2ban_count = content.fail2ban.count
    
    # Compute totals
    content.compute_totals()
    
    # Check for empty backup
    if content.is_empty():
        raise EmptyBackupError("No data available to backup")
    
    # Build metadata
    snapshot_id = create_snapshot_id(request.timestamp)
    metadata = SnapshotMetadata(
        snapshot_id=snapshot_id,
        created_at=request.timestamp,
        scope=scope,
        description=request.description,
        version=app_version or "1.0",
        source_system="omega-fire",
        hostname=hostname,
        os_info=os_info,
        app_version=app_version,
        status=SnapshotStatus.COMPLETED,
        origin=SnapshotOrigin(request.origin),
    )
    
    # Build snapshot
    snapshot = Snapshot(metadata=metadata, content=content)
    
    # Validate snapshot
    if not snapshot.is_valid():
        raise InvalidSnapshotError(
            snapshot_id,
            "Snapshot validation failed after construction"
        )
    
    return BackupResult(
        snapshot=snapshot,
        blacklist_count=blacklist_count,
        rules_count=rules_count,
        fail2ban_count=fail2ban_count,
    )


def validate_backup_data(
    banned_ips: Optional[list[BanEntry]] = None,
    rules: Optional[list[FirewallRule]] = None,
    jails: Optional[list[Jail]] = None,
) -> list[str]:
    """Validate backup data before planning.
    
    Args:
        banned_ips: List of banned IP entries
        rules: List of firewall rules
        jails: List of fail2ban jails
    
    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []
    
    # Check for None values (data not provided)
    if banned_ips is None and rules is None and jails is None:
        errors.append("No data provided for backup")
    
    # Check for invalid entries
    if banned_ips is not None:
        for i, ban in enumerate(banned_ips):
            if not ban.ip:
                errors.append(f"Ban entry {i} has empty IP")
    
    if rules is not None:
        for i, rule in enumerate(rules):
            if not rule.backend:
                errors.append(f"Rule {i} has empty backend")
    
    if jails is not None:
        for i, jail in enumerate(jails):
            if not jail.name:
                errors.append(f"Jail {i} has empty name")
    
    return errors

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit la logique métier de sauvegarde : comment construire un Snapshot à partir des données métier (bans, rules, jails), comment valider les données, comment calculer le scope, comment générer un ID. Ce module ne fait aucun I/O — il construit uniquement des structures en mémoire. L'écriture réelle (tar.gz, checksum, fichier) est déléguée à infrastructure/.
# Pourquoi dans domain/ (charte) :
# - C'est une règle métier : quoi inclure dans une sauvegarde, comment valider
# - Aucune dépendance externe (opère sur les modèles du domaine)
# - Fonctions pures : pas d'I/O, pas de tarfile, pas de Path.write()
# - Testable en mémoire pure
# Ce qu'il ne contient PAS (règles projet) :
# ❌ Pas d'import depuis infrastructure/ (pas d'écriture fichier)
# ❌ Pas d'import depuis interfaces/ (pas de rendu)
# ❌ Pas d'import depuis application/ (pas de cas d'usage)
# ❌ Pas de tarfile, gzip, open(), Path.write() — aucun I/O
# ❌ Pas de calcul de checksum réel (ça c'est infrastructure)
# Points clés :
# - BackupRequest : objet de requête décrivant quoi sauvegarder (scope, description, composants)
# - BackupResult : résultat du planning (snapshot en mémoire + compteurs)
# - build_blacklist_snapshot() : construit un BlacklistSnapshot à partir de BanEntry
# - build_rules_snapshot() : construit un RulesSnapshot à partir de FirewallRule
# - build_fail2ban_snapshot() : construit un Fail2banSnapshot à partir de Jail
# - plan_backup() : point d'entrée principal qui construit le Snapshot complet
# - validate_backup_data() : validation des données avant backup
# - Aucune dépendance externe : opère uniquement sur les modèles du domaine
# - Aucun I/O : ne crée ni archive, ni fichier, ni checksum
# Comment il sera utilisé (aperçu) :
# - application/commands/backup_state.py appellera plan_backup() pour construire le snapshot
# - infrastructure/storage/files/archive_store.py prendra le Snapshot et le sérialisera en .tar.gz
# - interfaces/cli/actions.py proposera les options de backup à l'utilisateur
#---------------------------------------------------------------------->
