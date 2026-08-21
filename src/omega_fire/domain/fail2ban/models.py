# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Fail2ban domain models.

Pure domain logic for fail2ban jails. No external dependencies.
This module defines what a jail IS, not how it is managed
by fail2ban-client or the underlying service.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class JailStatus(Enum):
    """Operational status of a fail2ban jail."""
    ACTIVE = "active"
    DISABLED = "disabled"
    ERROR = "error"


class JailManagedBy(Enum):
    """Who manages this jail."""
    OMEGA = "omega"      # Created/managed by Omega-Fire
    EXTERNAL = "external"  # Pre-existing, managed externally


@dataclass
class JailConfig:
    """Configuration parameters for a fail2ban jail.
    
    Pure domain model. Contains only the configuration values,
    not the runtime state (number of bans, etc.).
    """
    jail_name: str
    backend: str = "nftables"  # Backend used by this jail
    log_path: Optional[str] = None
    filter_name: Optional[str] = None
    maxretry: int = 5
    bantime: int = 3600  # seconds
    findtime: int = 600  # seconds
    port: Optional[str] = None  # Can be "80", "80,443", "http,https"
    protocol: Optional[str] = None  # tcp, udp, or both
    action: Optional[str] = None  # fail2ban action name
    enabled: bool = True
    
    def validate(self) -> list[str]:
        """Validate the jail configuration.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        if self.maxretry < 1:
            errors.append("maxretry must be >= 1")
        
        if self.bantime < 0:
            errors.append("bantime must be >= 0")
        
        if self.findtime < 0:
            errors.append("findtime must be >= 0")
        
        if not self.log_path:
            errors.append("log_path is required")
        
        return errors
    
    def is_valid(self) -> bool:
        """Check if the configuration is valid."""
        return len(self.validate()) == 0


@dataclass
class Jail:
    """A fail2ban jail.
    
    Pure domain model. The 'managed_by' field indicates whether
    Omega-Fire created this jail or if it's pre-existing.
    """
    name: str
    config: JailConfig
    status: JailStatus = JailStatus.ACTIVE
    managed_by: JailManagedBy = JailManagedBy.EXTERNAL
    last_seen: datetime = field(default_factory=datetime.now)
    
    # Runtime state (observed, not controlled by domain)
    currently_banned: int = 0
    total_banned: int = 0
    
    def is_active(self) -> bool:
        """Check if the jail is currently active."""
        return self.status == JailStatus.ACTIVE and self.config.enabled
    
    def is_managed_by_omega(self) -> bool:
        """Check if this jail is managed by Omega-Fire."""
        return self.managed_by == JailManagedBy.OMEGA
    
    def mark_disabled(self) -> None:
        """Mark the jail as disabled."""
        self.status = JailStatus.DISABLED
    
    def mark_error(self) -> None:
        """Mark the jail as in error state."""
        self.status = JailStatus.ERROR
    
    def update_runtime_stats(self, currently_banned: int, total_banned: int) -> None:
        """Update runtime statistics (called after observing fail2ban status).
        
        Args:
            currently_banned: Number of currently banned IPs
            total_banned: Total number of bans since jail start
        """
        self.currently_banned = currently_banned
        self.total_banned = total_banned
        self.last_seen = datetime.now()


@dataclass
class JailList:
    """Collection of fail2ban jails with query helpers."""
    jails: list[Jail] = field(default_factory=list)
    
    def add(self, jail: Jail) -> None:
        """Add a jail to the list."""
        self.jails.append(jail)
    
    def get_by_name(self, name: str) -> Optional[Jail]:
        """Get a jail by name. Returns None if not found."""
        for jail in self.jails:
            if jail.name == name:
                return jail
        return None
    
    def get_active(self) -> list[Jail]:
        """Get only active jails."""
        return [j for j in self.jails if j.is_active()]
    
    def get_managed_by_omega(self) -> list[Jail]:
        """Get only jails managed by Omega-Fire."""
        return [j for j in self.jails if j.is_managed_by_omega()]
    
    def get_by_backend(self, backend: str) -> list[Jail]:
        """Get jails filtered by backend."""
        return [j for j in self.jails if j.config.backend == backend]
    
    def count(self) -> int:
        """Return the total number of jails."""
        return len(self.jails)
    
    def count_active(self) -> int:
        """Return the number of active jails."""
        return len(self.get_active())

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit les modèles métier pour fail2ban. Ce sont des dataclasses pures qui représentent un jail (configuration, état), le statut d'un jail (actif, désactivé, en erreur), et les concepts associés (paramètres de jail, liste de jails).
# Pourquoi dans domain/ (charte) :
# - C'est une règle métier : qu'est-ce qu'un jail fail2ban, quels sont ses paramètres, son cycle de vie
# - Aucune dépendance externe (juste dataclasses, enum, typing)
# - Testable sans aucun backend réel (pas besoin de fail2ban-client)
# - Utilisé par application/commands/jail_ban.py et domain/fail2ban/service.py
# Ce qu'il ne contient PAS :
# ❌ Pas d'import depuis infrastructure/ (pas d'appel à fail2ban-client)
# ❌ Pas d'import depuis interfaces/ (pas de rendu)
# ❌ Pas d'import depuis application/ (pas de cas d'usage)
# ❌ Pas de logique d'exécution (juste la structure de données)
# Points clés :
# - JailConfig : configuration pure d'un jail (paramètres, pas d'état runtime)
# - Jail : modèle complet d'un jail (config + état + statistiques runtime)
# - JailList : conteneur avec des requêtes métier (par nom, statut, backend)
# - managed_by : distingue les jails créés par Omega-Fire vs pré-existants
# - validate() : validation métier de la configuration (maxretry, bantime, findtime)
# - Aucune dépendance externe : testable en mémoire pure
# Comment il sera utilisé (aperçu) :
# - domain/fail2ban/service.py utilisera ces modèles pour orchestrer les opérations sur les jails
# - application/commands/jail_ban.py construira un Jail et le passera au service
# - infrastructure/backends/fail2ban/adapter.py transformera un Jail en commandes fail2ban-client
#---------------------------------------------------------------------->
