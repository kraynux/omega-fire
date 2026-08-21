# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Fail2ban jail mapper.

Maps parsed fail2ban data (from parser.py) to domain models (from domain/).
This is the bridge between infrastructure parsing and domain objects.
"""
from typing import Optional
from omega_fire.domain.fail2ban.models import Jail, JailConfig, JailStatus, JailManagedBy
from omega_fire.domain.ip_blacklist.models import BanEntry, BanStatus, BanSource


class JailMapper:
    """Maps parsed fail2ban data to domain models."""

    def map_jail_status(self, jail_name: str, status: dict) -> Jail:
        """Map a jail status dict to a Jail domain model.

        Args:
            jail_name: Name of the jail
            status: Dictionary from Fail2banParser.parse_jail_status()

        Returns:
            Jail object
        """
        config = JailConfig(
            jail_name=jail_name,
            backend="nftables",  # Default, could be detected
            maxretry=5,  # Default, could be fetched via get_jail_config
            bantime=3600,
            findtime=600,
        )

        return Jail(
            name=jail_name,
            config=config,
            status=JailStatus.ACTIVE,  # Assume active if status query succeeded
            managed_by=JailManagedBy.EXTERNAL,
            currently_banned=status.get("currently_banned", 0),
            total_banned=status.get("total_banned", 0),
        )

    def map_ban(self, ip: str, jail_name: str) -> BanEntry:
        """Map an IP from a jail to a BanEntry domain model.

        Args:
            ip: IP address
            jail_name: Name of the jail

        Returns:
            BanEntry object
        """
        return BanEntry(
            ip=ip,
            backend="fail2ban",
            status=BanStatus.ACTIVE,
            source=BanSource.MANUAL,
            comment=f"Banned via jail {jail_name}",
        )

    def map_bans(self, ips: list[str], jail_name: str) -> list[BanEntry]:
        """Map multiple IPs from a jail to BanEntry domain models.

        Args:
            ips: List of IP addresses
            jail_name: Name of the jail

        Returns:
            List of BanEntry objects
        """
        return [self.map_ban(ip, jail_name) for ip in ips]


def map_jail_status(jail_name: str, status: dict) -> Jail:
    """Convenience function to map jail status."""
    return JailMapper().map_jail_status(jail_name, status)


def map_jail_bans(ips: list[str], jail_name: str) -> list[BanEntry]:
    """Convenience function to map jail ban IPs."""
    return JailMapper().map_bans(ips, jail_name)


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Mappe les données parsées de fail2ban (dicts) vers les modèles du domaine
# - Fait le pont entre infrastructure (parser) et domain (Jail, BanEntry)
# - Gère la conversion des statuts et la création des objets Jail
# Pourquoi dans infrastructure/ (charte) :
# - C'est un composant d'infrastructure qui connaît à la fois le format fail2ban
#   et les modèles du domaine pour faire la traduction
# - Le domaine ne doit pas connaître le format fail2ban (règle de dépendance)
# - L'application/ ne doit pas importer ce mapper directement
# Ce qu'il ne contient PAS :
# ❌ Pas d'appels système (travaille sur des données déjà parsées)
# ❌ Pas de logique métier (pas de validation, pas de politiques)
# ❌ Pas de dépendance vers application/ ou interfaces/
# Points clés :
# - JailMapper : classe principale avec 3 méthodes de mapping
# - map_jail_status() : dict status → Jail
#   - Crée un JailConfig avec des valeurs par défaut
#   - Mappe currently_banned et total_banned
#   - Suppose JailStatus.ACTIVE si la requête a réussi
# - map_ban() : IP string → BanEntry (backend="fail2ban")
# - map_bans() : liste d'IPs → liste de BanEntry
# - Fonctions de convenance : map_jail_status(), map_jail_bans()
# Comment il sera utilisé (aperçu) :
# - infrastructure/backends/fail2ban/adapter.py l'appellera après parsing
# - Le résultat sera retourné via les ports à l'application/
# - Les tests vérifieront que les mappings sont corrects pour différents formats
#---------------------------------------------------------------------->
