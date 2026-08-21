# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ip6tables data mapper.

Maps parsed ip6tables data (from parser.py) to domain models (from domain/).
"""
from typing import Optional
from omega_fire.domain.rules.models import FirewallRule, RuleAction, RuleChain, RuleProtocol, RuleFamily
from omega_fire.domain.ip_blacklist.models import BanEntry, BanStatus, BanSource


class Ip6tMapper:
    """Maps parsed ip6tables data to domain models."""

    def map_rule(self, parsed: dict) -> Optional[FirewallRule]:
        """Map a parsed ip6tables rule to a FirewallRule domain model."""
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

            # Clean source/destination (remove ::/0, la route par défaut IPv6)
            source = parsed.get("source")
            if source in ("::/0", "::"):
                source = None

            destination = parsed.get("destination")
            if destination in ("::/0", "::"):
                destination = None

            return FirewallRule(
                backend="ip6tables",
                family=RuleFamily.IP6,
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
            backend="ip6tables",
            status=BanStatus.ACTIVE,
            source=BanSource.MANUAL,
        )

    def map_bans(self, ips: list[str]) -> list[BanEntry]:
        """Map multiple IPs to BanEntry domain models."""
        return [self.map_ban(ip) for ip in ips]


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Mappe les données parsées d'ip6tables (dicts) vers les modèles du domaine
# - Miroir de iptables/mapper.py mais pour ip6tables (plan IPv6 iptables,
#   référentiel §53, Phase A)
# Pourquoi dans infrastructure/ (charte) :
# - Fait le pont entre infrastructure (parser) et domain (modèles)
# - Le domaine ne doit pas connaître le format ip6tables
# Ce qu'il ne contient PAS :
# ❌ Pas d'appels système, pas de logique métier, pas de dépendances vers application/
# Points clés :
# - Ip6tMapper : map_rule(), map_rules(), map_ban(), map_bans()
# - Différences volontaires avec IptMapper (pas une copie strictement
#   mécanique — seuls ces 2 points changent) :
#   - backend="ip6tables" (au lieu de "iptables")
#   - family=RuleFamily.IP6 (au lieu de RuleFamily.INET) — plus fidèle,
#     RuleFamily.IP6 existait déjà dans le modèle mais n'avait jamais
#     d'affectation réelle avant ce chantier
#   - Nettoyage de la route par défaut : "::/0"/"::" (au lieu de "0.0.0.0/0")
# Comment il est utilisé :
# - infrastructure/backends/ip6tables/adapter.py l'appelle après parsing
#---------------------------------------------------------------------->
