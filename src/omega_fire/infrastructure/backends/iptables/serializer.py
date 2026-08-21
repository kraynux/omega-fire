# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Iptables command serializer.

Converts domain model operations into iptables command strings.
"""
from typing import Optional


class IptSerializer:
    """Serializes operations into iptables command strings."""

    def build_ban_command(
        self,
        ip: str,
        chain: str = "INPUT",
        action: str = "DROP",
        comment: str = "",
    ) -> list[str]:
        """Build the iptables command to ban an IP."""
        cmd = ["iptables", "-A", chain, "-s", ip, "-j", action]
        if comment:
            cmd.extend(["-m", "comment", "--comment", comment])
        return cmd

    def build_unban_command(
        self,
        ip: str,
        chain: str = "INPUT",
        action: str = "DROP",
    ) -> list[str]:
        """Build the iptables command to unban an IP."""
        return ["iptables", "-D", chain, "-s", ip, "-j", action]

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
        """Build the iptables command to add a rule."""
        cmd = ["iptables", "-A", chain]

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
        """Build the iptables command to delete a rule by number."""
        return ["iptables", "-D", chain, str(rule_num)]

    def build_flush_chain_command(self, chain: str) -> list[str]:
        """Build the iptables command to flush a chain."""
        return ["iptables", "-F", chain]

    def build_flush_all_command(self) -> list[str]:
        """Build the iptables command to flush all chains."""
        return ["iptables", "-F"]

    def build_list_command(self, chain: str = "") -> list[str]:
        """Build the iptables command to list rules."""
        cmd = ["iptables", "-S"]
        if chain:
            cmd.append(chain)
        return cmd

    def build_list_verbose_command(self, chain: str = "") -> list[str]:
        """Build the iptables command to list rules verbosely."""
        cmd = ["iptables", "-L", "-n", "-v"]
        if chain:
            cmd.append(chain)
        return cmd


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Convertit les opérations abstraites en commandes iptables concrètes
# - Miroir de nftables/serializer.py mais pour iptables
# Pourquoi dans infrastructure/ (charte) :
# - Détail d'implémentation technique (syntaxe iptables)
# - Le domaine ne doit pas connaître la syntaxe iptables
# Ce qu'il ne contient PAS :
# ❌ Pas d'appels système, pas de logique métier, pas de dépendances externes
# Points clés :
# - IptSerializer : build_ban/unban/add_rule/delete_rule/flush/list
# - Différence avec nftables : iptables utilise -A/-D/-F, pas de sets
# - Ban = 'iptables -A INPUT -s IP -j DROP'
# - Unban = 'iptables -D INPUT -s IP -j DROP'
# - Suppression par numéro de règle (pas de handle)
# Comment il est utilisé :
# - infrastructure/backends/iptables/adapter.py l'appellera pour construire les commandes
#---------------------------------------------------------------------->
