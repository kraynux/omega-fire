# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Nftables command serializer.

Converts domain model operations into nft command strings.
This module translates abstract operations (ban IP, add rule, flush)
into concrete nft command-line arguments.

This module performs no I/O — it only builds command strings.
The actual execution is done by the adapter.
"""
from typing import Optional

from omega_fire.shared.networking import CIDR


def addr_family_keyword(cidr_or_ip: str) -> str:
    """"ip" ou "ip6" selon la famille de l'adresse/CIDR (référentiel §50,
    plan IPv6 Phase B). Repli sur "ip" (comportement d'avant ce correctif,
    seule famille jamais gérée) si la valeur n'est pas un CIDR/IP
    reconnaissable par ipaddress — laisse nft lui-même signaler l'erreur
    de format plutôt que de faire échouer la construction de la commande
    ici, en amont de toute exécution réelle."""
    try:
        return "ip6" if CIDR(cidr_or_ip).version == 6 else "ip"
    except ValueError:
        return "ip"


class NftSerializer:
    """Serializes operations into nft command strings."""

    def build_ban_command(
        self,
        ip: str,
        table: str = "filter",
        chain: str = "input",
        family: str = "inet",
        set_name: str = "blacklist",
        comment: str = "",
    ) -> list[str]:
        if comment:
            clean_comment = comment.replace('"', '\\"')
            element_expr = f'{{ {ip} comment "{clean_comment}" }}'
        else:
            element_expr = f'{{ {ip} }}'

        return ["nft", "add", "element", family, table, set_name, element_expr]

    def build_unban_command(
        self,
        ip: str,
        table: str = "filter",
        family: str = "inet",
        set_name: str = "blacklist",
    ) -> list[str]:
        """Build the nft command to unban an IP.

        Args:
            ip: IP address to unban
            table: nft table name
            family: nft family
            set_name: Name of the nft set

        Returns:
            Command as list of arguments
        """
        return ["nft", "delete", "element", f"{family} {table} {set_name}", f"{{ {ip} }}"]

    def build_add_rule_command(
        self,
        family: str,
        table: str,
        chain: str,
        action: str,
        protocol: Optional[str] = None,
        port: Optional[str] = None,
        source: Optional[str] = None,
        destination: Optional[str] = None,
        comment: str = "",
    ) -> list[str]:
        """Build the nft command to add a rule.

        Args:
            family: nft family
            table: nft table name
            chain: nft chain name
            action: Rule action (accept, drop, reject, log)
            protocol: Optional protocol (tcp, udp, icmp)
            port: Optional port or port range
            source: Optional source CIDR
            destination: Optional destination CIDR
            comment: Optional comment

        Returns:
            Command as list of arguments
        """
        cmd = ["nft", "add", "rule", f"{family} {table} {chain}"]

        if protocol and port:
            cmd.append(protocol)
            cmd.extend(["dport", port])
        elif protocol:
            # Protocole seul, sans port : "tcp accept" n'est pas une
            # syntaxe nft valide (pas d'expression de correspondance).
            # meta l4proto exprime explicitement "tout paquet de ce
            # protocole", peu importe le port.
            cmd.extend(["meta", "l4proto", protocol])
        elif port:
            cmd.extend(["dport", port])

        if source:
            cmd.extend([addr_family_keyword(source), "saddr", source])

        if destination:
            cmd.extend([addr_family_keyword(destination), "daddr", destination])

        cmd.append(action)

        if comment:
            cmd.extend(["comment", f'"{comment}"'])

        return cmd

    def build_delete_rule_command(
        self,
        family: str,
        table: str,
        chain: str,
        handle: int,
    ) -> list[str]:
        """Build the nft command to delete a rule by handle.

        Args:
            family: nft family
            table: nft table name
            chain: nft chain name
            handle: Rule handle to delete

        Returns:
            Command as list of arguments
        """
        return ["nft", "delete", "rule", f"{family} {table} {chain}", "handle", str(handle)]

    def build_flush_chain_command(
        self,
        family: str,
        table: str,
        chain: str,
    ) -> list[str]:
        """Build the nft command to flush a chain.

        Args:
            family: nft family
            table: nft table name
            chain: nft chain name

        Returns:
            Command as list of arguments
        """
        return ["nft", "flush", "chain", f"{family} {table} {chain}"]

    def build_flush_table_command(
        self,
        family: str,
        table: str,
    ) -> list[str]:
        """Build the nft command to flush a table.

        Args:
            family: nft family
            table: nft table name

        Returns:
            Command as list of arguments
        """
        return ["nft", "flush", "table", f"{family} {table}"]

    def build_list_ruleset_command(self) -> list[str]:
        """Build the nft command to list the full ruleset."""
        return ["nft", "list", "ruleset"]

    def build_list_table_command(self, family: str, table: str) -> list[str]:
        """Build the nft command to list a table, including rule handles.

        The -a flag is required for nft to print each rule's handle in the
        output — without it, handles are silently omitted, which breaks
        external_ref capture (dedup in 3.3, post-apply lookup in 3.1).
        """
        return ["nft", "-a", "list", "table", f"{family} {table}"]

    def build_list_set_command(
        self,
        family: str,
        table: str,
        set_name: str,
    ) -> list[str]:
        """Build the nft command to list a set."""
        return ["nft", "list", "set", f"{family} {table} {set_name}"]

    def build_create_set_command(
        self,
        family: str,
        table: str,
        set_name: str,
        set_type: str = "ipv4_addr",
    ) -> list[str]:
        """Build the nft command to create a set."""
        return [
            "nft", "add", "set", f"{family} {table} {set_name}",
            f"{{ type {set_type}; }}",
        ]


def build_ban_command(ip: str, **kwargs) -> list[str]:
    """Convenience function to build a ban command."""
    return NftSerializer().build_ban_command(ip, **kwargs)


def build_add_rule_command(**kwargs) -> list[str]:
    """Convenience function to build an add rule command."""
    return NftSerializer().build_add_rule_command(**kwargs)


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Convertit les opérations abstraites en commandes nft concrètes
# - Traduit ban/unban/add_rule/delete_rule/flush en arguments CLI
# - Produit des listes de strings prêtes pour subprocess.run()
# Pourquoi dans infrastructure/ (charte) :
# - C'est un détail d'implémentation technique (format de commande nft)
# - Le domaine ne doit pas connaître la syntaxe nft
# - Séparé de l'adapter pour faciliter les tests unitaires
# Ce qu'il ne contient PAS :
# ❌ Pas d'appels système (ne lance pas subprocess, juste construit les commandes)
# ❌ Pas de logique métier (pas de validation, pas de politiques)
# ❌ Pas de dépendance vers domain/, application/ ou interfaces/
# Points clés :
# - NftSerializer : classe principale avec méthodes de sérialisation
# - build_ban_command() : 'nft add element inet filter blacklist { IP }'
# - build_unban_command() : 'nft delete element inet filter blacklist { IP }'
# - build_add_rule_command() : 'nft add rule inet filter input tcp dport 80 accept'
# - build_delete_rule_command() : 'nft delete rule inet filter input handle 42'
# - build_flush_chain_command() / build_flush_table_command()
# - build_list_ruleset_command() / build_list_table_command() / build_list_set_command()
# - build_create_set_command() : crée un set pour les bans
# - Toutes les méthodes retournent list[str] pour subprocess.run()
# - Fonctions de convenance : build_ban_command(), build_add_rule_command()
# Comment il sera utilisé (aperçu) :
# - infrastructure/backends/nftables/adapter.py l'appellera pour construire les commandes
# - Les tests vérifieront que les commandes sont correctement formatées
#---------------------------------------------------------------------->
