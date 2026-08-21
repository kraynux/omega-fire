# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ip6tables command serializer.

Converts domain model operations into ip6tables command strings.
"""
from typing import Optional


class Ip6tSerializer:
    """Serializes operations into ip6tables command strings."""

    def build_ban_command(
        self,
        ip: str,
        chain: str = "INPUT",
        action: str = "DROP",
        comment: str = "",
    ) -> list[str]:
        """Build the ip6tables command to ban an IP."""
        cmd = ["ip6tables", "-A", chain, "-s", ip, "-j", action]
        if comment:
            cmd.extend(["-m", "comment", "--comment", comment])
        return cmd

    def build_unban_command(
        self,
        ip: str,
        chain: str = "INPUT",
        action: str = "DROP",
    ) -> list[str]:
        """Build the ip6tables command to unban an IP."""
        return ["ip6tables", "-D", chain, "-s", ip, "-j", action]

    def build_add_rule_command(
        self,
        chain: str,
        action: str,
        protocol: Optional[str] = None,
        port: Optional[str] = None,
        source: Optional[str] = None,
        destination: Optional[str] = None,
        comment: str = "",
    ) -> list[str]:
        """Build the ip6tables command to add a rule."""
        cmd = ["ip6tables", "-A", chain]

        if protocol:
            cmd.extend(["-p", protocol])

        if port:
            cmd.extend(["--dport", port])

        if source:
            cmd.extend(["-s", source])

        if destination:
            cmd.extend(["-d", destination])

        cmd.extend(["-j", action.upper()])

        if comment:
            cmd.extend(["-m", "comment", "--comment", comment])

        return cmd

    def build_delete_rule_command(
        self,
        chain: str,
        rule_num: int,
    ) -> list[str]:
        """Build the ip6tables command to delete a rule by number."""
        return ["ip6tables", "-D", chain, str(rule_num)]

    def build_flush_chain_command(self, chain: str) -> list[str]:
        """Build the ip6tables command to flush a chain."""
        return ["ip6tables", "-F", chain]

    def build_flush_all_command(self) -> list[str]:
        """Build the ip6tables command to flush all chains."""
        return ["ip6tables", "-F"]

    def build_list_command(self, chain: str = "") -> list[str]:
        """Build the ip6tables command to list rules."""
        cmd = ["ip6tables", "-S"]
        if chain:
            cmd.append(chain)
        return cmd

    def build_list_verbose_command(self, chain: str = "") -> list[str]:
        """Build the ip6tables command to list rules verbosely."""
        cmd = ["ip6tables", "-L", "-n", "-v"]
        if chain:
            cmd.append(chain)
        return cmd


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Convertit les opérations abstraites en commandes ip6tables concrètes
# - Miroir de iptables/serializer.py mais pour ip6tables (plan IPv6 iptables,
#   référentiel §53, Phase A)
# Pourquoi dans infrastructure/ (charte) :
# - Détail d'implémentation technique (syntaxe ip6tables)
# - Le domaine ne doit pas connaître la syntaxe ip6tables
# Ce qu'il ne contient PAS :
# ❌ Pas d'appels système, pas de logique métier, pas de dépendances externes
# Points clés :
# - Ip6tSerializer : build_ban/unban/add_rule/delete_rule/flush/list
# - Identique syntaxiquement à IptSerializer (-A/-D/-F, pas de sets) — seul
#   le nom du binaire change ("ip6tables" au lieu de "iptables")
# - Ban = 'ip6tables -A INPUT -s IP -j DROP'
# - Unban = 'ip6tables -D INPUT -s IP -j DROP'
# Comment il est utilisé :
# - infrastructure/backends/ip6tables/adapter.py l'appellera pour construire
#   les commandes
#---------------------------------------------------------------------->
