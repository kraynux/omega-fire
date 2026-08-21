# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Iptables data mapper.

Maps parsed iptables data (from parser.py) to domain models (from domain/).
"""
from typing import Optional
from omega_fire.domain.rules.models import FirewallRule, RuleAction, RuleChain, RuleProtocol, RuleFamily
from omega_fire.domain.ip_blacklist.models import BanEntry, BanStatus, BanSource


class IptMapper:
    """Maps parsed iptables data to domain models."""

    def map_rule(self, parsed: dict) -> Optional[FirewallRule]:
        """Map a parsed iptables rule to a FirewallRule domain model."""
        try:
            # Map action
            action_str = parsed.get("action", "accept")
            action_map = {
                "accept": RuleAction.ACCEPT,
                "drop": RuleAction.DROP,
                "reject": RuleAction.REJECT,
                "log": RuleAction.LOG,
            }
            action = action_map.get(action_str, RuleAction.ACCEPT)

            # Map chain
            chain_str = parsed.get("chain", "INPUT").lower()
            try:
                chain = RuleChain(chain_str)
            except ValueError:
                chain = RuleChain.INPUT

            # Map protocol
            proto_str = parsed.get("protocol")
            protocol = None
            if proto_str and proto_str != "all":
                try:
                    protocol = RuleProtocol(proto_str)
                except ValueError:
                    protocol = None

            # Parse port
            port_str = parsed.get("port")
            port_start = None
            port_end = None
            if port_str:
                if ":" in port_str:
                    parts = port_str.split(":")
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

            # Clean source/destination (remove 0.0.0.0/0)
            source = parsed.get("source")
            if source in ("0.0.0.0/0", "0.0.0.0"):
                source = None

            destination = parsed.get("destination")
            if destination in ("0.0.0.0/0", "0.0.0.0"):
                destination = None

            return FirewallRule(
                backend="iptables",
                family=RuleFamily.INET,
                table_name="filter",
                chain=chain,
                action=action,
                protocol=protocol,
                port_start=port_start,
                port_end=port_end,
                source_cidr=source,
                dest_cidr=destination,
                comment=parsed.get("comment"),
                external_ref=parsed.get("raw"),
            )

        except Exception:
            return None

    def map_rules(self, parsed_list: list[dict]) -> list[FirewallRule]:
        """Map multiple parsed rules to domain models."""
        rules = []
        for parsed in parsed_list:
            rule = self.map_rule(parsed)
            if rule:
                rules.append(rule)
        return rules

    def map_ban(self, ip: str) -> BanEntry:
        """Map an IP to a BanEntry domain model."""
        return BanEntry(
            ip=ip,
            backend="iptables",
            status=BanStatus.ACTIVE,
            source=BanSource.MANUAL,
        )

    def map_bans(self, ips: list[str]) -> list[BanEntry]:
        """Map multiple IPs to BanEntry domain models."""
        return [self.map_ban(ip) for ip in ips]


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Mappe les données parsées d'iptables (dicts) vers les modèles du domaine
# - Miroir de nftables/mapper.py mais pour iptables
# Pourquoi dans infrastructure/ (charte) :
# - Fait le pont entre infrastructure (parser) et domain (modèles)
# - Le domaine ne doit pas connaître le format iptables
# Ce qu'il ne contient PAS :
# ❌ Pas d'appels système, pas de logique métier, pas de dépendances vers application/
# Points clés :
# - IptMapper : map_rule(), map_rules(), map_ban(), map_bans()
# - Différence avec nftables :
#   - Pas de handle → rule_id non défini
#   - Pas de famille → toujours RuleFamily.INET
#   - Nettoyage des 0.0.0.0/0 en source/destination
#   - Mapping d'action : ACCEPT/DROP/REJECT/LOG
# Comment il est utilisé :
# - infrastructure/backends/iptables/adapter.py l'appelle après parsing
#---------------------------------------------------------------------->
