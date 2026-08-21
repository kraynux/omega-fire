# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Iptables output parser.

Parses the output of iptables commands (iptables -L, iptables -S, etc.)
into structured data. Handles both the verbose (-L -n -v) and save (-S) formats.
"""
import re
from typing import Optional


class IptParser:
    """Parses iptables command output into structured data."""

    def parse_rules_save(self, output: str) -> list[dict]:
        """Parse iptables-save format output (-S).

        Args:
            output: Raw output from 'iptables -S'

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
        """Parse a single iptables-save rule line."""
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
        """Parse iptables -L -n -v format output.

        Args:
            output: Raw output from 'iptables -L -n -v'

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
        """Parse an iptables -v packet/byte counter.

        iptables abbreviates large counters with K/M/G suffixes (base
        1000, iptables' own convention — not 1024) once the value grows
        large enough, e.g. "47M" packets, "159G" bytes. Confirmed by real
        testing: a plain int(raw) silently threw ValueError on these,
        which (via the broad except in _parse_verbose_line) dropped the
        entire rest of that rule's parsing — the rule with the most
        actual traffic on the system was the one invisibly missing from
        every aggregate.

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
        """Parse a single verbose iptables rule line."""
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
        """Parse iptables output to extract banned IPs.

        Looks for DROP/REJECT rules with source IPs.

        Args:
            output: Raw output from iptables -S or -L

        Returns:
            List of banned IP addresses
        """
        ips = []
        for line in output.split("\n"):
            stripped = line.strip()
            if ("DROP" in stripped or "REJECT" in stripped) and "-s" in stripped:
                src_match = re.search(r"-s\s+(\d+\.\d+\.\d+\.\d+(?:/\d+)?)", stripped)
                if src_match:
                    ip = src_match.group(1)
                    if ip not in ips:
                        ips.append(ip)
        return ips


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Parse la sortie textuelle des commandes iptables en structures de données
# - Gère deux formats : iptables-save (-S) et verbose (-L -n -v)
# - Extrait chaîne, protocole, port, source, destination, action, compteurs
# Pourquoi dans infrastructure/ (charte) :
# - C'est un parser technique qui traite la sortie brute d'une commande système
# - Le format de sortie iptables est un détail d'implémentation
# - Produit des dicts bruts qui seront mappés en objets métier par mapper.py
# Ce qu'il ne contient PAS :
# ❌ Pas d'appels système, pas de logique métier, pas de dépendances externes
# Points clés :
# - IptParser : classe principale avec 3 méthodes de parsing
# - parse_rules_save() : parse 'iptables -S' (format iptables-save)
# - parse_rules_verbose() : parse 'iptables -L -n -v' (format tableau)
# - parse_ban_list() : extrait les IPs des règles DROP/REJECT
# - Différence avec nftables : iptables n'a pas de handles ni de sets
# Comment il est utilisé :
# - infrastructure/backends/iptables/adapter.py l'appelle après chaque commande
# - infrastructure/backends/iptables/mapper.py transforme les dicts en objets métier
#---------------------------------------------------------------------->
