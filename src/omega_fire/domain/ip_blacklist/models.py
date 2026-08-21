# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""IP blacklist domain models.

Pure domain logic for IP ban entries. No external dependencies.
This module defines what a ban IS, not how it is stored or applied.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class BanStatus(Enum):
    """Lifecycle status of a ban entry."""
    ACTIVE = "active"
    EXPIRED = "expired"
    REMOVED = "removed"


class BanSource(Enum):
    """Origin of a ban entry."""
    MANUAL = "manual"
    SYNC = "sync"
    IMPORT = "import"
    FAIL2BAN_TRANSFER = "fail2ban_transfer"


@dataclass
class BanEntry:
    """A single banned IP address.

    Pure domain model. The 'backend' field is a label only
    ('nftables', 'iptables', 'fail2ban'), not a dependency.
    """
    ip: str
    backend: str  # label: 'nftables' | 'iptables' | 'fail2ban'
    status: BanStatus = BanStatus.ACTIVE
    jail_name: Optional[str] = None
    comment: Optional[str] = None
    banned_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    removed_at: Optional[datetime] = None
    removed_by: Optional[str] = None  # 'user' | 'auto' | 'sync'
    source: BanSource = BanSource.MANUAL

    def is_active(self) -> bool:
        """A ban is active only if status is ACTIVE and not expired."""
        if self.status != BanStatus.ACTIVE:
            return False
        if self.expires_at and datetime.now() > self.expires_at:
            return False
        return True

    def is_expired(self) -> bool:
        """Check if the ban has reached its expiration date."""
        return self.expires_at is not None and datetime.now() > self.expires_at

    def mark_removed(self, by: str = "user") -> None:
        """Transition the ban to REMOVED state."""
        self.status = BanStatus.REMOVED
        self.removed_at = datetime.now()
        self.removed_by = by


@dataclass
class IPList:
    """Collection of ban entries with query helpers."""
    entries: list[BanEntry] = field(default_factory=list)

    def add(self, entry: BanEntry) -> None:
        """Add a ban entry to the list."""
        self.entries.append(entry)

    def get_active(self) -> list[BanEntry]:
        """Return only currently active bans."""
        return [e for e in self.entries if e.is_active()]

    def get_by_backend(self, backend: str) -> list[BanEntry]:
        """Return bans filtered by backend label."""
        return [e for e in self.entries if e.backend == backend]

    def get_by_ip(self, ip: str) -> list[BanEntry]:
        """Return all bans (any status) for a given IP."""
        return [e for e in self.entries if e.ip == ip]

    def get_by_jail(self, jail_name: str) -> list[BanEntry]:
        """Return bans associated with a specific fail2ban jail."""
        return [e for e in self.entries if e.jail_name == jail_name]
        
# <-- INFO DEV ---------------------------------------------------------
# Rôle
# - Définit les modèles métier pour la blacklist d'IPs. Ce sont des dataclasses pures — elles ne savent rien de nftables, iptables, fail2ban, SQLite ou Rich.
# Pourquoi dans domain/ (charte) :
# - C'est une règle métier : qu'est-ce qu'une IP bannie, quel est son cycle de vie
# - Aucune dépendance externe (juste dataclasses, datetime, enum)
# - Testable sans aucun backend réel
# Ce qu'il ne contient PAS (règles projet)
# ❌ Pas de subprocess (pas d'appel à nft, iptables)
# ❌ Pas de sqlite3 (pas de persistence)
# ❌ Pas de rich (pas de rendu)
# ❌ Pas d'import depuis application/, infrastructure/ ou interfaces/
# Points clés à retenir :
# - BanEntry est immutable par convention (sauf transitions explicites via mark_removed)
# - backend est une chaîne label, pas une référence à un adaptateur
# - Les méthodes is_active() / is_expired() contiennent la règle métier du cycle de vie
# - IPList est un conteneur avec des requêtes métier (pas du SQL)
#---------------------------------------------------------------------->
