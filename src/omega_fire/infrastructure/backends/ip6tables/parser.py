# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ip6tables output parser.

Parses the output of ip6tables commands (ip6tables -L, ip6tables -S, etc.)
into structured data. Handles both the verbose (-L -n -v) and save (-S) formats.
"""
import re
from typing import Optional


class Ip6tParser:
    """Parses ip6tables command output into structured data."""

    def parse_rules_save(self, output: str) -> list[dict]:
        """Parse ip6tables-save format output (-S).

        Args:
            output: Raw output from 'ip6tables -S'

        Returns:
            List of rule dictionaries
        """
        rules = []
        for line in output.split("\n"):
            stripped = line.strip()
            if stripped.startswith("-A "):
                rule = self._parse_save_line(stripped)
                if rule:
                    rules.append(rule)
        return rules

    def _parse_save_line(self, line: str) -> Optional[dict]:
        """Parse a single ip6tables-save rule line."""
        rule = {"raw": line}

        # Extract chain
        chain_match = re.match(r"-A\s+(\S+)", line)
        if chain_match:
            rule["chain"] = chain_match.group(1)

        # Extract protocol
        proto_match = re.search(r"-p\s+(\S+)", line)
        if proto_match:
            rule["protocol"] = proto_match.group(1)

        # Extract source
        src_match = re.search(r"-s\s+(\S+)", line)
        if src_match:
            rule["source"] = src_match.group(1)

        # Extract destination
        dst_match = re.search(r"-d\s+(\S+)", line)
        if dst_match:
            rule["destination"] = dst_match.group(1)

        # Extract port
        dport_match = re.search(r"--dport\s+(\S+)", line)
        if dport_match:
            rule["port"] = dport_match.group(1)

        # Extract action (target)
        target_match = re.search(r"-j\s+(\S+)", line)
        if target_match:
            rule["action"] = target_match.group(1).lower()

        # Extract comment
        comment_match = re.search(r'--comment\s+"([^"]+)"', line)
        if comment_match:
            rule["comment"] = comment_match.group(1)

        return rule

    def parse_rules_verbose(self, output: str) -> list[dict]:
        """Parse ip6tables -L -n -v format output.

        Args:
            output: Raw output from 'ip6tables -L -n -v'

        Returns:
            List of rule dictionaries
        """
        rules = []
        current_chain = ""

        for line in output.split("\n"):
            stripped = line.strip()

            if stripped.startswith("Chain "):
                chain_match = re.match(r"Chain\s+(\S+)", stripped)
                if chain_match:
                    current_chain = chain_match.group(1)

            elif (
                stripped
                and not stripped.startswith("target")
                and not stripped.startswith("num")
                and not stripped.startswith("pkts")
            ):
                rule = self._parse_verbose_line(stripped, current_chain)
                if rule:
                    rules.append(rule)

        return rules

    def _parse_counter_value(self, raw: str) -> int:
        """Parse an ip6tables -v packet/byte counter.

        Same K/M/G abbreviation convention (base 1000) as iptables — see
        IptParser._parse_counter_value() for the real-testing rationale
        behind this handling (referentiel iptables adapter).

        Args:
            raw: Raw counter token (e.g. "0", "47M", "1.5K")

        Returns:
            The counter as a plain int.
        """
        raw = raw.strip()
        multipliers = {"K": 1_000, "M": 1_000_000, "G": 1_000_000_000}
        if raw and raw[-1] in multipliers:
            return int(float(raw[:-1]) * multipliers[raw[-1]])
        return int(raw)

    def _parse_verbose_line(self, line: str, chain: str) -> Optional[dict]:
        """Parse a single verbose ip6tables rule line."""
        parts = line.split()
        if len(parts) < 4:
            return None

        rule = {
            "chain": chain,
            "raw": line,
        }

        # Typical format: pkts bytes target prot opt in out source destination [options]
        try:
            rule["packets"] = self._parse_counter_value(parts[0])
            rule["bytes"] = self._parse_counter_value(parts[1])
            rule["action"] = parts[2].lower()
            rule["protocol"] = parts[3]

            if len(parts) > 7:
                rule["source"] = parts[7]
            if len(parts) > 8:
                rule["destination"] = parts[8]

            # Extract port from remaining options
            for i, part in enumerate(parts):
                if part == "dpt:" and i + 1 < len(parts):
                    rule["port"] = parts[i + 1]
                elif part.startswith("dpt:"):
                    rule["port"] = part[4:]

        except (ValueError, IndexError):
            pass

        return rule

    def parse_ban_list(self, output: str) -> list[str]:
        """Parse ip6tables output to extract banned IPv6 addresses.

        Looks for DROP/REJECT rules with source IPv6 addresses.

        Différence volontaire avec IptParser.parse_ban_list() : la classe de
        caractères capture de l'hexadécimal/deux-points (adresse IPv6), pas
        des chiffres/points (IPv4) — plan IPv6 iptables, référentiel §53,
        Phase A. Sans ce correctif, aucune IPv6 bannie via ip6tables ne
        serait jamais retrouvée par is_ip_banned()/unban_single_ip().

        Args:
            output: Raw output from ip6tables -S or -L

        Returns:
            List of banned IPv6 addresses
        """
        ips = []
        for line in output.split("\n"):
            stripped = line.strip()
            if ("DROP" in stripped or "REJECT" in stripped) and "-s" in stripped:
                src_match = re.search(r"-s\s+([0-9a-fA-F:]+(?:/\d+)?)", stripped)
                if src_match:
                    ip = src_match.group(1)
                    if ip not in ips:
                        ips.append(ip)
        return ips


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Parse la sortie textuelle des commandes ip6tables en structures de données
# - Gère deux formats : ip6tables-save (-S) et verbose (-L -n -v)
# - Extrait chaîne, protocole, port, source, destination, action, compteurs
# Pourquoi dans infrastructure/ (charte) :
# - C'est un parser technique qui traite la sortie brute d'une commande système
# - Le format de sortie ip6tables est un détail d'implémentation
# - Produit des dicts bruts qui seront mappés en objets métier par mapper.py
# Ce qu'il ne contient PAS :
# ❌ Pas d'appels système, pas de logique métier, pas de dépendances externes
# Points clés :
# - Ip6tParser : miroir de IptParser, mêmes 3 méthodes de parsing
# - Seule différence réelle avec IptParser : parse_ban_list() capture une
#   adresse IPv6 (hexadécimal + ':'), pas une IPv4 — le reste du parsing
#   (chaîne, protocole, port, compteurs) est déjà agnostique de la famille
#   d'adresse (tokens \S+ génériques)
# Comment il est utilisé :
# - infrastructure/backends/ip6tables/adapter.py l'appelle après chaque commande
# - infrastructure/backends/ip6tables/mapper.py transforme les dicts en objets métier
#---------------------------------------------------------------------->
