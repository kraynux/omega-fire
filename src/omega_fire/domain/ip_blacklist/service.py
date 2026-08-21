# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""IP blacklist domain service.

Orchestrates business operations on the IP blacklist.
This service coordinates the domain modules (models, filters, sync, export)
and enforces business rules by raising domain exceptions.
"""
from datetime import datetime
from typing import Optional
from omega_fire.domain.ip_blacklist.models import (
    BanEntry,
    BanSource,
    BanStatus,
    IPList,
)
from omega_fire.domain.ip_blacklist.exceptions import (
    IPAlreadyBannedError,
    IPNotFoundError,
    InvalidIPError,
)
from omega_fire.domain.ip_blacklist.filters import (
    combine_filters,
    filter_active_only,
)
from omega_fire.domain.ip_blacklist.sync import (
    SyncPlan,
    SyncStrategy,
    plan_sync,
    validate_sync_direction,
)
from omega_fire.domain.ip_blacklist.export import (
    ExportData,
    ExportFormat,
    ExportScope,
    prepare_export,
)
from omega_fire.shared.networking import IPAddress


class BlacklistService:
    """Domain service for IP blacklist operations.
    
    This service orchestrates business logic for banning, unbanning,
    listing, syncing, and exporting IPs. It enforces business rules
    and raises domain exceptions when rules are violated.
    """
    
    def __init__(self, ip_list: Optional[IPList] = None):
        """Initialize the service with an optional IP list.
        
        Args:
            ip_list: Existing IP list. If None, creates an empty one.
        """
        self.ip_list = ip_list or IPList()
    
    def ban_ip(
        self,
        ip: str,
        backend: str,
        comment: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        source: BanSource = BanSource.MANUAL,
        jail_name: Optional[str] = None,
    ) -> BanEntry:
        """Ban an IP address.
        
        Business rules:
        - IP must be valid (IPv4 or IPv6)
        - IP must not already be banned on the same backend
        
        Args:
            ip: IP address to ban
            backend: Backend label ('nftables', 'iptables', 'fail2ban')
            comment: Optional comment
            expires_at: Optional expiration date
            source: Source of the ban (default: MANUAL)
            jail_name: Optional jail name (for fail2ban transfers)
        
        Returns:
            The created BanEntry
        
        Raises:
            InvalidIPError: If IP format is invalid
            IPAlreadyBannedError: If IP is already banned on this backend
        """
        # Validate IP format
        try:
            IPAddress(ip)
        except ValueError as e:
            raise InvalidIPError(ip) from e
        
        # Check if already banned on this backend
        existing = [
            e for e in self.ip_list.entries
            if e.ip == ip and e.backend == backend and e.is_active()
        ]
        if existing:
            raise IPAlreadyBannedError(ip, backend)
        
        # Create ban entry
        entry = BanEntry(
            ip=ip,
            backend=backend,
            status=BanStatus.ACTIVE,
            jail_name=jail_name,
            comment=comment,
            banned_at=datetime.now(),
            expires_at=expires_at,
            source=source,
        )
        
        self.ip_list.add(entry)
        return entry
    
    def unban_ip(self, ip: str, backend: Optional[str] = None, by: str = "user") -> list[BanEntry]:
        """Unban an IP address.
        
        Business rules:
        - IP must exist in the blacklist (active bans)
        - If backend is specified, only unban from that backend
        - If backend is None, unban from all backends
        
        Args:
            ip: IP address to unban
            backend: Optional backend to unban from (None = all backends)
            by: Who is unbanning ('user', 'auto', 'sync')
        
        Returns:
            List of unbanned BanEntry objects
        
        Raises:
            IPNotFoundError: If IP is not found in active bans
        """
        # Find active bans for this IP
        if backend:
            active_bans = [
                e for e in self.ip_list.entries
                if e.ip == ip and e.backend == backend and e.is_active()
            ]
        else:
            active_bans = [
                e for e in self.ip_list.entries
                if e.ip == ip and e.is_active()
            ]
        
        if not active_bans:
            raise IPNotFoundError(ip)
        
        # Mark all as removed
        for entry in active_bans:
            entry.mark_removed(by=by)
        
        return active_bans
    
    def list_bans(
        self,
        status: Optional[BanStatus] = None,
        backend: Optional[str] = None,
        ip: Optional[str] = None,
        jail_name: Optional[str] = None,
        source: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        active_only: bool = False,
    ) -> list[BanEntry]:
        """List ban entries with optional filters.
        
        Args:
            status: Filter by status
            backend: Filter by backend
            ip: Filter by IP address
            jail_name: Filter by jail name
            source: Filter by source
            start_date: Filter by minimum ban date
            end_date: Filter by maximum ban date
            active_only: If True, only return active bans
        
        Returns:
            List of BanEntry matching the filters
        """
        entries = self.ip_list.entries
        
        if active_only:
            entries = filter_active_only(entries)
        
        return combine_filters(
            entries,
            status=status,
            backend=backend,
            ip=ip,
            jail_name=jail_name,
            source=source,
            start_date=start_date,
            end_date=end_date,
        )
    
    def get_ban(self, ip: str, backend: str) -> Optional[BanEntry]:
        """Get a specific ban entry.
        
        Args:
            ip: IP address
            backend: Backend name
        
        Returns:
            BanEntry if found, None otherwise
        """
        for entry in self.ip_list.entries:
            if entry.ip == ip and entry.backend == backend:
                return entry
        return None
    
    def plan_sync(
        self,
        source_backend: str,
        target_backend: str,
        strategy: SyncStrategy = SyncStrategy.SKIP_IF_EXISTS,
    ) -> SyncPlan:
        """Plan a synchronization between backends.
        
        Args:
            source_backend: Source backend name
            target_backend: Target backend name
            strategy: Sync strategy (default: SKIP_IF_EXISTS)
        
        Returns:
            SyncPlan describing what needs to be synced
        
        Raises:
            ValueError: If sync direction is not supported
        """
        if not validate_sync_direction(source_backend, target_backend):
            raise ValueError(
                f"Unsupported sync direction: {source_backend} -> {target_backend}"
            )
        
        source_entries = self.list_bans(backend=source_backend, active_only=True)
        target_entries = self.list_bans(backend=target_backend, active_only=True)
        
        return plan_sync(
            source_entries=source_entries,
            target_entries=target_entries,
            source_backend=source_backend,
            target_backend=target_backend,
            strategy=strategy,
        )
    
    def prepare_export(
        self,
        export_format: ExportFormat,
        scope: ExportScope = ExportScope.ACTIVE_ONLY,
        backend_filter: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> ExportData:
        """Prepare ban data for export.
        
        Args:
            export_format: Target format (JSON, TXT, CSV)
            scope: Export scope (default: ACTIVE_ONLY)
            backend_filter: Backend name if scope is BY_BACKEND
            start_date: Start date if scope is BY_DATE_RANGE
            end_date: End date if scope is BY_DATE_RANGE
        
        Returns:
            ExportData ready for infrastructure exporters
        """
        return prepare_export(
            entries=self.ip_list.entries,
            export_format=export_format,
            scope=scope,
            backend_filter=backend_filter,
            start_date=start_date,
            end_date=end_date,
        )
    
    def count_active(self) -> int:
        """Count active bans."""
        return len(self.ip_list.get_active())
    
    def count_by_backend(self, backend: str) -> int:
        """Count active bans for a specific backend."""
        return len([e for e in self.ip_list.get_active() if e.backend == backend])

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Orchestration métier des opérations sur la blacklist. Ce service coordonne les modules du domaine (models, filters, sync, export) et applique les règles métier (vérifications, validations). Il lève les exceptions métier quand une règle est violée.
# Pourquoi dans domain/ : 
# - C'est la logique métier centrale du sous-domaine blacklist
# - Utilise uniquement les autres modules du domaine (models, filters, sync, export)
# - Lève les exceptions métier définies dans exceptions.py
# - Aucune dépendance externe (pas de subprocess, sqlite3, rich)
# Ce qu'il ne contient PAS (règles projet) :
# ❌ Pas d'import depuis infrastructure/ (pas d'appel système, pas de DB)
# ❌ Pas d'import depuis application/ (pas de cas d'usage)
# ❌ Pas d'import depuis interfaces/ (pas de rendu)
# ❌ Pas de logique d'exécution (juste l'orchestration métier)
# Points clés :
# - Orchestration métier : coordonne models, filters, sync, export
# - Validation stricte : vérifie les règles métier (IP valide, pas de doublon)
# - Exceptions métier : lève InvalidIPError, IPAlreadyBannedError, IPNotFoundError
# - Aucune dépendance externe : utilise uniquement shared/networking.py pour la validation IP
# - Testable en mémoire : peut être testé sans aucun backend réel
# - IPList injectable : permet de travailler sur une liste existante ou d'en créer une nouvelle
# Comment il sera utilisé (aperçu) :
# - application/commands/ban_ip.py instanciera BlacklistService et appellera ban_ip()
# - application/queries/list_banned_ips.py appellera list_bans() avec les filtres
# - application/commands/sync_backends.py appellera plan_sync() pour calculer le plan
# - application/commands/export_report.py appellera prepare_export() pour préparer les données
#---------------------------------------------------------------------->
