# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Nftables output parser.

Parses the output of nft commands (nft list ruleset, nft list table, etc.)
into structured data. This module handles the textual output format of nft
and converts it into dictionaries that can be mapped to domain models.

This module performs no I/O — it only parses strings. The actual command
execution is done by the adapter.
"""
import re
from typing import Optional


class NftParser:
    """Parses nft command output into structured data."""

    def parse_ruleset(self, output: str) -> list[dict]:
        """Parse the full nft ruleset output.

        Args:
            output: Raw output from 'nft list ruleset'

        Returns:
            List of rule dictionaries
        """
        rules = []
        current_table = ""
        current_chain = ""
        current_family = ""

        for line in output.split("\n"):
            stripped = line.strip()

            if stripped.startswith("table "):
                parts = stripped.split()
                if len(parts) >= 3:
                    current_family = parts[1]
                    current_table = parts[2].rstrip(" {")

            elif stripped.startswith("chain "):
                parts = stripped.split()
                if len(parts) >= 2:
                    current_chain = parts[1].rstrip(" {")

            elif (
                stripped
                and not stripped.startswith("#")
                and not stripped.startswith("type ")
                and stripped not in ("{", "}")
            ):
                rule = self._parse_rule_line(stripped, current_family, current_table, current_chain)
                if rule:
                    rules.append(rule)

        return rules

    def _parse_rule_line(self, line: str, family: str, table: str, chain: str) -> Optional[dict]:
        """Parse a single nft rule line.

        Args:
            line: Single line from nft output
            family: Current table family
            table: Current table name
            chain: Current chain name

        Returns:
            Rule dictionary or None if line is not a rule
        """
        rule = {
            "family": family,
            "table": table,
            "chain": chain,
            "raw": line,
        }

        # Extract handle
        handle_match = re.search(r"handle\s+(\d+)", line)
        if handle_match:
            rule["handle"] = int(handle_match.group(1))

        # Extract protocol
        proto_match = re.search(r"(tcp|udp|icmp|icmpv6)", line)
        if proto_match:
            rule["protocol"] = proto_match.group(1)

        # Extract port
        # Handles both a single port/range ("dport 22", "dport 22-100")
        # and a multi-port set ("dport { 22, 80, 443 }") — nftables uses
        # the latter whenever a preset rule lists more than one port.
        port_match = re.search(
            r"(?:dport|sport)\s+(?:\{\s*([\d,\s-]+?)\s*\}|(\d+(?:-\d+)?))",
            line,
        )
        if port_match:
            raw_port = port_match.group(1) or port_match.group(2)
            rule["port"] = raw_port.replace(" ", "")

        # Extract source/destination — classe de caractères élargie aux
        # chiffres hexadécimaux et ":" pour capturer une adresse/CIDR IPv6
        # (ex: "ip6 saddr 2001:db8::/32") en plus d'IPv4 ; auparavant
        # [\d./] ne matchait jamais une IPv6 (référentiel §50, plan IPv6
        # Phase B) — même préfixe "saddr"/"daddr" pour "ip saddr"/"ip6 saddr".
        saddr_match = re.search(r"saddr\s+([0-9a-fA-F:./]+)", line)
        if saddr_match:
            rule["source"] = saddr_match.group(1)

        daddr_match = re.search(r"daddr\s+([0-9a-fA-F:./]+)", line)
        if daddr_match:
            rule["destination"] = daddr_match.group(1)

        # Extract action
        for action in ("accept", "drop", "reject", "log", "return", "jump", "goto"):
            if action in line.lower():
                rule["action"] = action
                break

        # Extract comment
        comment_match = re.search(r'comment\s+"([^"]+)"', line)
        if comment_match:
            rule["comment"] = comment_match.group(1)

        # Extract counters
        counter_match = re.search(r"counter\s+packets\s+(\d+)\s+bytes\s+(\d+)", line)
        if counter_match:
            rule["packets"] = int(counter_match.group(1))
            rule["bytes"] = int(counter_match.group(2))

        return rule

    def parse_tables(self, output: str) -> list[dict]:
        """Parse nft table listing.

        Args:
            output: Raw output from 'nft list tables'

        Returns:
            List of table dictionaries
        """
        tables = []
        for line in output.split("\n"):
            stripped = line.strip()
            if stripped.startswith("table "):
                parts = stripped.split()
                if len(parts) >= 3:
                    tables.append({
                        "family": parts[1],
                        "name": parts[2],
                    })
        return tables

    def parse_chains(self, output: str) -> list[dict]:
        """Parse nft chain listing.

        Args:
            output: Raw output from 'nft list chains'

        Returns:
            List of chain dictionaries
        """
        chains = []
        for line in output.split("\n"):
            stripped = line.strip()
            if stripped.startswith("chain "):
                parts = stripped.split()
                if len(parts) >= 2:
                    chains.append({
                        "name": parts[1].rstrip(" {"),
                        "raw": stripped,
                    })
        return chains

    def parse_ban_set(self, output: str, set_name: str = "blackhole") -> list[str]:
        """Parse an nft set to extract banned IPs.

        Args:
            output: Raw output from 'nft list set'
            set_name: Name of the set to parse

        Returns:
            List of banned IP addresses
        """
        ips = []
        in_set = False

        for line in output.split("\n"):
            stripped = line.strip()

            if f"set {set_name}" in stripped:
                in_set = True
                continue

            if in_set:
                if stripped == "}":
                    break
                # Extract IP from element line
                ip_match = re.search(r"(\d+\.\d+\.\d+\.\d+(?:/\d+)?)", stripped)
                if ip_match:
                    ips.append(ip_match.group(1))

        return ips


def parse_nft_ruleset(output: str) -> list[dict]:
    """Convenience function to parse nft ruleset."""
    return NftParser().parse_ruleset(output)


def parse_nft_ban_set(output: str, set_name: str = "blackhole") -> list[str]:
    """Convenience function to parse nft ban set."""
    return NftParser().parse_ban_set(output, set_name)


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Parse la sortie textuelle des commandes nft en structures de données
# - Gère le parsing de ruleset, tables, chains et sets de bannissement
# - Extrait les informations clés : handle, protocole, port, source, destination,
#   action, commentaire, compteurs
# Pourquoi dans infrastructure/ (charte) :
# - C'est un parser technique qui traite la sortie brute d'une commande système
# - Le format de sortie nft est un détail d'implémentation, pas une règle métier
# - Produit des dicts bruts qui seront mappés en objets métier par mapper.py
# Ce qu'il ne contient PAS :
# ❌ Pas d'appels système (reçoit la sortie en string, ne lance pas nft)
# ❌ Pas de logique métier (pas de validation de règles, pas de politiques)
# ❌ Pas de dépendance vers domain/, application/ ou interfaces/
# Points clés :
# - NftParser : classe principale avec 4 méthodes de parsing
# - parse_ruleset() : parse 'nft list ruleset' complet
#   - Extrait table, chain, handle, protocol, port, source, dest, action, comment, counters
# - parse_tables() : parse 'nft list tables'
# - parse_chains() : parse 'nft list chains'
# - parse_ban_set() : parse un set nft pour extraire les IPs bannies
# - Utilise des regex pour extraire les champs de la sortie textuelle
# - Ne fait aucun I/O : reçoit des strings, retourne des dicts
# - Fonctions de convenance : parse_nft_ruleset(), parse_nft_ban_set()
# Comment il sera utilisé (aperçu) :
# - infrastructure/backends/nftables/adapter.py l'appellera après chaque commande nft
# - infrastructure/backends/nftables/mapper.py transformera les dicts en objets métier
# - Les tests utiliseront des fixtures de sortie nft pour vérifier le parsing
#---------------------------------------------------------------------->
