# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Fail2ban domain service.

Orchestrates business operations on fail2ban jails.
This service coordinates the domain modules (models, jails, transfer, validation)
and enforces business rules by raising domain exceptions.
"""
from typing import Optional
from omega_fire.domain.fail2ban.models import (
    Jail,
    JailConfig,
    JailList,
    JailManagedBy,
    JailStatus,
)
from omega_fire.domain.fail2ban.exceptions import (
    JailNotFoundError,
    JailAlreadyExistsError,
    JailDisabledError,
    InvalidIPForJailError,
    TransferError,
    InvalidJailConfigError,
)
from omega_fire.domain.fail2ban.jails import (
    create_valid_jail,
    validate_jail_name,
)
from omega_fire.domain.fail2ban.transfer import (
    TransferPlan,
    TransferStrategy,
    plan_transfer,
    validate_transfer_feasibility,
)
from omega_fire.domain.ip_blacklist.models import BanEntry
from omega_fire.shared.networking import IPAddress


class Fail2banService:
    """Domain service for fail2ban operations.
    
    This service orchestrates business logic for managing jails,
    banning/unbanning IPs, and planning transfers to the blacklist.
    It enforces business rules and raises domain exceptions when
    rules are violated.
    """
    
    def __init__(self, jail_list: Optional[JailList] = None):
        """Initialize the service with an optional jail list.
        
        Args:
            jail_list: Existing jail list. If None, creates an empty one.
        """
        self.jail_list = jail_list or JailList()
    
    def create_jail(
        self,
        jail_name: str,
        log_path: str,
        maxretry: int = 5,
        bantime: int = 3600,
        findtime: int = 600,
        backend: str = "nftables",
        filter_name: Optional[str] = None,
        port: Optional[str] = None,
        protocol: Optional[str] = None,
        action: Optional[str] = None,
        enabled: bool = True,
        managed_by: JailManagedBy = JailManagedBy.EXTERNAL,
    ) -> Jail:
        """Create a new fail2ban jail.
        
        Business rules:
        - Jail name must be valid and unique
        - All parameters must be valid
        - Configuration must pass validation
        
        Args:
            jail_name: Name of the jail
            log_path: Path to the log file to monitor
            maxretry: Number of failures before ban
            bantime: Ban duration in seconds (0 = permanent)
            findtime: Time window for counting failures
            backend: Backend used by this jail
            filter_name: Fail2ban filter name (optional)
            port: Port(s) to monitor (optional)
            protocol: Protocol (optional)
            action: Fail2ban action name (optional)
            enabled: Whether the jail is enabled
            managed_by: Who manages this jail
        
        Returns:
            The created Jail
        
        Raises:
            JailAlreadyExistsError: If a jail with this name already exists
            InvalidJailConfigError: If the jail configuration is invalid
        """
        # Check uniqueness
        if self.jail_list.get_by_name(jail_name) is not None:
            raise JailAlreadyExistsError(jail_name)
        
        # Create and validate the jail (raises on invalid config)
        jail = create_valid_jail(
            jail_name=jail_name,
            log_path=log_path,
            maxretry=maxretry,
            bantime=bantime,
            findtime=findtime,
            backend=backend,
            filter_name=filter_name,
            port=port,
            protocol=protocol,
            action=action,
            enabled=enabled,
            managed_by=managed_by,
        )
        
        self.jail_list.add(jail)
        return jail
    
    def delete_jail(self, jail_name: str) -> Jail:
        """Delete a jail by name.
        
        Args:
            jail_name: Name of the jail to delete
        
        Returns:
            The deleted Jail
        
        Raises:
            JailNotFoundError: If the jail does not exist
        """
        jail = self.jail_list.get_by_name(jail_name)
        if jail is None:
            raise JailNotFoundError(jail_name)
        
        self.jail_list.jails.remove(jail)
        return jail
    
    def get_jail(self, jail_name: str) -> Jail:
        """Get a jail by name.
        
        Args:
            jail_name: Name of the jail
        
        Returns:
            The Jail
        
        Raises:
            JailNotFoundError: If the jail does not exist
        """
        jail = self.jail_list.get_by_name(jail_name)
        if jail is None:
            raise JailNotFoundError(jail_name)
        return jail
    
    def list_jails(
        self,
        active_only: bool = False,
        managed_by_omega_only: bool = False,
        backend: Optional[str] = None,
    ) -> list[Jail]:
        """List jails with optional filters.
        
        Args:
            active_only: If True, only return active jails
            managed_by_omega_only: If True, only return Omega-managed jails
            backend: Filter by backend
        
        Returns:
            List of Jail matching the filters
        """
        jails = self.jail_list.jails
        
        if active_only:
            jails = [j for j in jails if j.is_active()]
        if managed_by_omega_only:
            jails = [j for j in jails if j.is_managed_by_omega()]
        if backend:
            jails = [j for j in jails if j.config.backend == backend]
        
        return jails
    
    def ban_ip_in_jail(self, jail_name: str, ip: str) -> None:
        """Record a ban of an IP in a jail.
        
        Business rules:
        - Jail must exist
        - Jail must be active
        - IP must be valid
        
        Note: This only records the ban in the domain model.
        Actual execution is done by infrastructure via ports.
        
        Args:
            jail_name: Name of the jail
            ip: IP address to ban
        
        Raises:
            JailNotFoundError: If the jail does not exist
            JailDisabledError: If the jail is not active
            InvalidIPForJailError: If the IP format is invalid
        """
        jail = self.get_jail(jail_name)
        
        if not jail.is_active():
            raise JailDisabledError(jail_name)
        
        # Validate IP format
        try:
            IPAddress(ip)
        except ValueError as e:
            raise InvalidIPForJailError(
                ip,
                jail_name,
                f"Invalid IP format: {e}"
            ) from e
        
        # Update runtime stats (in real usage, infrastructure will
        # observe the actual state from fail2ban-client)
        jail.update_runtime_stats(
            currently_banned=jail.currently_banned + 1,
            total_banned=jail.total_banned + 1,
        )
    
    def unban_ip_in_jail(self, jail_name: str, ip: str) -> None:
        """Record an unban of an IP in a jail.
        
        Business rules:
        - Jail must exist
        - Jail must be active
        
        Args:
            jail_name: Name of the jail
            ip: IP address to unban
        
        Raises:
            JailNotFoundError: If the jail does not exist
            JailDisabledError: If the jail is not active
            InvalidIPForJailError: If the IP format is invalid
        """
        jail = self.get_jail(jail_name)
        
        if not jail.is_active():
            raise JailDisabledError(jail_name)
        
        # Validate IP format
        try:
            IPAddress(ip)
        except ValueError as e:
            raise InvalidIPForJailError(
                ip,
                jail_name,
                f"Invalid IP format: {e}"
            ) from e
        
        # Update runtime stats
        if jail.currently_banned > 0:
            jail.update_runtime_stats(
                currently_banned=jail.currently_banned - 1,
                total_banned=jail.total_banned,
            )
    
    def plan_transfer_to_blacklist(
        self,
        jail_name: str,
        banned_ips: list[str],
        existing_blacklist: list[BanEntry],
        target_backend: str,
        strategy: TransferStrategy = TransferStrategy.NEW_ONLY,
        threshold: int = 1,
    ) -> TransferPlan:
        """Plan a transfer of banned IPs from a jail to the blacklist.
        
        Business rules:
        - Jail must exist
        - Transfer must be feasible (jail active, backend compatible)
        
        Args:
            jail_name: Name of the source jail
            banned_ips: List of currently banned IPs in the jail
            existing_blacklist: Current blacklist entries
            target_backend: Target backend for transfer
            strategy: Transfer strategy
            threshold: Threshold for WITH_THRESHOLD strategy
        
        Returns:
            TransferPlan describing what needs to be transferred
        
        Raises:
            JailNotFoundError: If the jail does not exist
            TransferError: If the transfer is not feasible
        """
        jail = self.get_jail(jail_name)
        
        # Validate feasibility
        is_feasible, reason = validate_transfer_feasibility(jail, target_backend)
        if not is_feasible:
            raise TransferError(jail_name, reason)
        
        return plan_transfer(
            jail=jail,
            banned_ips=banned_ips,
            existing_blacklist=existing_blacklist,
            target_backend=target_backend,
            strategy=strategy,
            threshold=threshold,
        )
    
    def update_jail_runtime_stats(
        self,
        jail_name: str,
        currently_banned: int,
        total_banned: int,
    ) -> None:
        """Update runtime statistics for a jail.
        
        This is typically called after observing the actual state
        from fail2ban-client via infrastructure.
        
        Args:
            jail_name: Name of the jail
            currently_banned: Number of currently banned IPs
            total_banned: Total number of bans since jail start
        
        Raises:
            JailNotFoundError: If the jail does not exist
        """
        jail = self.get_jail(jail_name)
        jail.update_runtime_stats(currently_banned, total_banned)
    
    def count_jails(self) -> int:
        """Count total jails."""
        return self.jail_list.count()
    
    def count_active_jails(self) -> int:
        """Count active jails."""
        return self.jail_list.count_active()

# <-- INFO DEV ---------------------------------------------------------
# Rôle
# - Orchestration métier des opérations sur les jails fail2ban. Ce service coordonne les modules du domaine (models, jails, transfer, validation) et applique les règles métier (validation, vérification d'existence, planification de transfert). Il lève les exceptions métier quand une règle est violée.
# Pourquoi dans domain/ (charte) :
# - C'est la logique métier centrale du sous-domaine fail2ban
# - Utilise uniquement les autres modules du domaine
# - Lève les exceptions métier définies dans exceptions.py
# - Aucune dépendance externe (pas de subprocess, sqlite3, rich)
# ❌ Ce qu'il ne contient PAS
# ❌ Pas d'import depuis infrastructure/ (pas d'appel à fail2ban-client, pas de DB)
# ❌ Pas d'import depuis application/ (pas de cas d'usage)
# ❌ Pas d'import depuis interfaces/ (pas de rendu)
# ❌ Pas de logique d'exécution (juste l'orchestration métier)
# Points clés :
# - Orchestration métier : coordonne models, jails, transfer, validation
# - Validation stricte : vérifie les règles métier (jail existe, est actif, IP valide)
# - Exceptions métier : lève JailNotFoundError, JailAlreadyExistsError, JailDisabledError, InvalidIPForJailError, TransferError
# - Aucune dépendance externe : utilise uniquement les modules du domaine + shared/networking.py
# - Testable en mémoire : peut être testé sans fail2ban-client ni DB
# - JailList injectable : permet de travailler sur une liste existante ou d'en créer une nouvelle
# - 🔗 Comment il sera utilisé (aperçu)
# - application/commands/jail_ban.py instanciera Fail2banService et appellera ban_ip_in_jail()
# - application/queries/jail_status.py appellera get_jail() et list_jails()
# - application/commands/sync_backends.py appellera plan_transfer_to_blacklist()
# - interfaces/cli/actions.py proposera les jails disponibles à l'utilisateur
#---------------------------------------------------------------------->
