# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Contrat pour la gestion de la blacklist d'IPs unifiée."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from omega_fire.shared.networking import IPAddress


@dataclass(frozen=True, slots=True)
class BanEntry:
    """Entrée de blacklist immuable.

    Attributs:
        ip: adresse IP bannie.
        backend: backend cible (nftables, iptables, fail2ban).
        reason: raison du ban (commentaire optionnel).
        banned_at: date et heure du ban.
        expires_at: date d'expiration (None = ban permanent).
        jail: nom du jail fail2ban (None si non applicable).
    """
    ip: IPAddress
    backend: str
    reason: str = ""
    banned_at: datetime | None = None
    expires_at: datetime | None = None
    jail: str | None = None


class BlacklistPort(Protocol):
    """Contrat pour la gestion de la blacklist unifiée.

    Définit les opérations attendues pour bannir, débannir, lister
    et synchroniser les IPs entre backends.
    """

    @abstractmethod
    def ban(
        self,
        ip: IPAddress,
        backend: str,
        *,
        reason: str = "",
        expires_at: datetime | None = None,
        jail: str | None = None,
    ) -> BanEntry:
        """Bannit une IP sur un backend spécifique.

        Args:
            ip: adresse IP à bannir.
            backend: backend cible (nftables, iptables, fail2ban).
            reason: raison du ban (optionnel).
            expires_at: date d'expiration (None = permanent).
            jail: nom du jail fail2ban (optionnel).

        Returns:
            BanEntry créée.

        Raises:
            IPAlreadyBannedError: si l'IP est déjà bannie sur ce backend.
        """
        ...

    @abstractmethod
    def unban(self, ip: IPAddress, backend: str) -> None:
        """Débannit une IP d'un backend spécifique.

        Args:
            ip: adresse IP à débannir.
            backend: backend cible.

        Raises:
            IPNotFoundError: si l'IP n'est pas bannie sur ce backend.
        """
        ...

    @abstractmethod
    def list_banned(
        self,
        *,
        backend: str | None = None,
        include_expired: bool = False,
    ) -> list[BanEntry]:
        """Liste les IPs bannies.

        Args:
            backend: filtre par backend (None = tous).
            include_expired: True pour inclure les bans expirés.

        Returns:
            Liste de BanEntry.
        """
        ...

    @abstractmethod
    def is_banned(self, ip: IPAddress, backend: str | None = None) -> bool:
        """Vérifie si une IP est bannie.

        Args:
            ip: adresse IP à vérifier.
            backend: backend spécifique (None = tous).

        Returns:
            True si l'IP est bannie.
        """
        ...

    @abstractmethod
    def sync(self, source_backend: str, target_backend: str) -> int:
        """Synchronise les IPs d'un backend vers un autre.

        Args:
            source_backend: backend source.
            target_backend: backend cible.

        Returns:
            Nombre d'IPs synchronisées.
        """
        ...

    @abstractmethod
    def flush(self, backend: str | None = None) -> int:
        """Vide complètement un backend ou tous.

        Args:
            backend: backend à vider (None = tous).

        Returns:
            Nombre d'IPs supprimées.
        """
        ...

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit le contrat (Protocol) pour la gestion de la blacklist unifiée.
# - Fournit BanEntry (dataclass frozen) représentant une IP bannie.
# - Spécifie les opérations : ban(), unban(), list_banned(), is_banned(),
#   sync(), flush().
#
# Pourquoi dans ports/ (charte) :
# - C'est un contrat attendu par le cœur applicatif (application/commands/)
# - Pas d'implémentation concrète (c'est le rôle de infrastructure/backends/)
# - Aucune dépendance vers domain/, application/, infrastructure/, interfaces/
#
# Ce qu'il ne contient PAS :
# ❌ Pas d'implémentation concrète (appels nft/iptables/fail2ban)
# ❌ Pas d'import depuis domain/
# ❌ Pas d'import depuis application/
# ❌ Pas d'import depuis infrastructure/
# ❌ Pas d'import depuis interfaces/
# ❌ Pas de logique de synchronisation concrète
#
# Points clés :
# - BanEntry : dataclass frozen avec ip, backend, reason, banned_at, expires_at, jail
# - BlacklistPort : Protocol définissant ban(), unban(), list_banned(), is_banned(),
#   sync(), flush()
# - IPAddress importé depuis shared/networking.py (validation stricte)
# - Toutes les méthodes sont abstraites (via Protocol)
# - BanEntry est immuable (frozen=True, slots=True)
#
# Comment il sera utilisé (aperçu) :
# - application/commands/ban_ip.py appellera blacklist_port.ban()
# - application/commands/unban_ip.py appellera blacklist_port.unban()
# - infrastructure/backends/nftables/adapter.py implémentera BlacklistPort
# - infrastructure/backends/iptables/adapter.py implémentera BlacklistPort
# - infrastructure/backends/fail2ban/adapter.py implémentera BlacklistPort
# - interfaces/cli/actions.py appellera blacklist_port.list_banned() pour menu 2.5
#---------------------------------------------------------------------->        
