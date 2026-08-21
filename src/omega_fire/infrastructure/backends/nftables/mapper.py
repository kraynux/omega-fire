# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Nftables data mapper.

Maps parsed nft data (from parser.py) to domain models (from domain/).
This is the bridge between infrastructure parsing and domain objects.
"""
from typing import Optional
from omega_fire.domain.rules.models import FirewallRule, RuleAction, RuleChain, RuleProtocol, RuleFamily
from omega_fire.domain.ip_blacklist.models import BanEntry, BanStatus, BanSource


class NftMapper:
    """Maps parsed nft data to domain models."""

    def map_rule(self, parsed: dict) -> Optional[FirewallRule]:
        """Map a parsed nft rule to a FirewallRule domain model.

        Args:
            parsed: Dictionary from NftParser

        Returns:
            FirewallRule or None if mapping fails
        """
        try:
            # Map family
            family_str = parsed.get("family", "inet")
            try:
                family = RuleFamily(family_str)
            except ValueError:
                family = RuleFamily.INET

            # Map action
            action_str = parsed.get("action", "accept")
            try:
                action = RuleAction(action_str)
            except ValueError:
                action = RuleAction.ACCEPT

            # Map chain
            chain_str = parsed.get("chain", "input")
            try:
                chain = RuleChain(chain_str)
            except ValueError:
                chain = RuleChain.INPUT
    
            # Map protocol
            proto_str = parsed.get("protocol")
            protocol = None
            if proto_str:
                try:
                    protocol = RuleProtocol(proto_str)
                except ValueError:
                    protocol = None

            # Parse port
            port_str = parsed.get("port")
            port_start = None
            port_end = None
            if port_str:
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

            handle = parsed.get("handle")
            return FirewallRule(
                backend="nftables",
                family=family,
                table_name=parsed.get("table", "filter"),
                chain=chain,
                action=action,
                protocol=protocol,
                port_start=port_start,
                port_end=port_end,
                source_cidr=parsed.get("source"),
                dest_cidr=parsed.get("destination"),
                comment=parsed.get("comment"),
                external_ref=str(handle) if handle is not None else None,
            )

        except Exception:
            return None

    def map_rules(self, parsed_list: list[dict]) -> list[FirewallRule]:
        """Map multiple parsed rules to domain models.

        Args:
            parsed_list: List of parsed rule dictionaries

        Returns:
            List of FirewallRule objects
        """
        rules = []
        for parsed in parsed_list:
            rule = self.map_rule(parsed)
            if rule:
                rules.append(rule)
        return rules

    def map_ban(self, ip: str, comment: str = "") -> BanEntry:
        """Map an IP from nft set to a BanEntry domain model.

        Args:
            ip: IP address from nft set
            comment: Optional comment

        Returns:
            BanEntry object
        """
        return BanEntry(
            ip=ip,
            backend="nftables",
            status=BanStatus.ACTIVE,
            source=BanSource.MANUAL,
            comment=comment,
        )

    def map_bans(self, ips: list[str]) -> list[BanEntry]:
        """Map multiple IPs from nft set to BanEntry domain models.

        Args:
            ips: List of IP addresses

        Returns:
            List of BanEntry objects
        """
        return [self.map_ban(ip) for ip in ips]


def map_nft_rules(parsed_list: list[dict]) -> list[FirewallRule]:
    """Convenience function to map parsed nft rules."""
    return NftMapper().map_rules(parsed_list)


def map_nft_bans(ips: list[str]) -> list[BanEntry]:
    """Convenience function to map nft ban IPs."""
    return NftMapper().map_bans(ips)


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Mappe les données parsées de nft (dicts) vers les modèles du domaine
# - Fait le pont entre infrastructure (parser) et domain (FirewallRule, BanEntry)
# - Gère la conversion des enums (string → RuleAction, RuleChain, etc.)
# Pourquoi dans infrastructure/ (charte) :
# - C'est un composant d'infrastructure qui connaît à la fois le format nft
#   et les modèles du domaine pour faire la traduction
# - Le domaine ne doit pas connaître le format nft (règle de dépendance)
# - L'application/ ne doit pas importer ce mapper directement
# Ce qu'il ne contient PAS :
# ❌ Pas d'appels système (travaille sur des données déjà parsées)
# ❌ Pas de logique métier (pas de validation, pas de politiques)
# ❌ Pas de dépendance vers application/ ou interfaces/
# Points clés :
# - NftMapper : classe principale avec 4 méthodes de mapping
# - map_rule() : dict parsé → FirewallRule
#   - Convertit family, action, chain, protocol (string → enum)
#   - Parse les ports (simple ou range)
#   - Mappe source/destination vers source_cidr/dest_cidr
#   - Mappe handle vers rule_id
# - map_rules() : liste de dicts → liste de FirewallRule
# - map_ban() : IP string → BanEntry (backend="nftables")
# - map_bans() : liste d'IPs → liste de BanEntry
# - Gestion robuste des enums : ValueError → valeur par défaut
# - Fonctions de convenance : map_nft_rules(), map_nft_bans()
# Comment il sera utilisé (aperçu) :
# - infrastructure/backends/nftables/adapter.py l'appellera après parsing
# - Le résultat sera retourné via les ports à l'application/
# - Les tests vérifieront que les mappings sont corrects pour différents formats
#---------------------------------------------------------------------->
