# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Conntrack output parser.

Parses the output of conntrack commands (conntrack -L, conntrack -C)
into structured data. Handles connection listing and counter queries.

This module performs no I/O — it only parses strings. The actual command
execution is done by the adapter.
"""
import re
from typing import Optional


class ConntrackParser:
    """Parses conntrack command output into structured data."""

    def parse_connection_list(self, output: str) -> list[dict]:
        """Parse the list of connections from conntrack -L.

        Args:
            output: Raw output from 'conntrack -L'

        Returns:
            List of connection dictionaries
        """
        connections = []

        for line in output.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue

            conn = self._parse_connection_line(stripped)
            if conn:
                connections.append(conn)

        return connections

    def _parse_connection_line(self, line: str) -> Optional[dict]:
        """Parse a single conntrack connection line.

        Args:
            line: Single line from conntrack -L output

        Returns:
            Connection dictionary or None if parsing fails
        """
        conn = {"raw": line}

        # Extract protocol
        proto_match = re.search(r"\b(tcp|udp|icmp)\b", line, re.IGNORECASE)
        if proto_match:
            conn["protocol"] = proto_match.group(1).lower()

        # Extract source IP and port.
        #
        # Real conntrack -L line structure (verified against live
        # output, 2026-08-11), e.g.:
        #   src=192.168.1.107 dst=54.167.136.58 sport=54960 dport=8883
        #   src=54.167.136.58 dst=192.168.1.107 sport=8883 dport=54960
        # Two full src=/dst=/sport=/dport= groups appear for any NATed
        # connection (original direction, then reply direction), with
        # dst= sitting BETWEEN src= and sport= within each group — so
        # neither a bare "src=...\s+sport=..." anchor (too strict, never
        # matches — first regression) nor an unbounded greedy ".*"
        # (matches past the first group into the second — second
        # regression, the original "?" bug in menu 8.2) work correctly.
        #
        # This pattern captures the FIRST full group only: src= and
        # dst= as any non-whitespace token (IPv4 dotted-quad OR IPv6,
        # which contains ':' and hex letters — [\d.]+ alone silently
        # failed on IPv6 addresses, e.g. the observed
        # "2a02:842a:8541:c301:..." entry), immediately followed by
        # sport=/dport= with only whitespace and any icmp-only fields
        # in between — non-greedy .*? bounded to stop at the first
        # sport=/dport=, never crossing into the reply-direction group.
        src_match = re.search(r"src=(\S+)\s+dst=(\S+)\s+sport=(\d+)\s+dport=(\d+)", line)
        if src_match:
            conn["source_ip"] = src_match.group(1)
            conn["destination_ip"] = src_match.group(2)
            conn["source_port"] = int(src_match.group(3))
            conn["destination_port"] = int(src_match.group(4))

        # Extract destination IP and port (same anchoring rationale).
        dst_match = re.search(r"dst=([\d.]+)\s+dport=(\d+)", line)
        if dst_match:
            conn["destination_ip"] = dst_match.group(1)
            conn["destination_port"] = int(dst_match.group(2))

        # Extract state (for TCP)
        state_match = re.search(r"\b(ESTABLISHED|SYN_SENT|SYN_RECV|FIN_WAIT|TIME_WAIT|CLOSE_WAIT|LAST_ACK|LISTEN)\b", line)
        if state_match:
            conn["state"] = state_match.group(1)

        # Extract packets and bytes
        packets_match = re.search(r"packets=(\d+)", line)
        if packets_match:
            conn["packets"] = int(packets_match.group(1))

        bytes_match = re.search(r"bytes=(\d+)", line)
        if bytes_match:
            conn["bytes"] = int(bytes_match.group(1))

        return conn

    def parse_connection_count(self, output: str) -> int:
        """Parse the connection count from conntrack -C.

        Args:
            output: Raw output from 'conntrack -C'

        Returns:
            Number of connections
        """
        try:
            return int(output.strip())
        except ValueError:
            return 0


def parse_conntrack_connections(output: str) -> list[dict]:
    """Convenience function to parse connection list."""
    return ConntrackParser().parse_connection_list(output)


def parse_conntrack_count(output: str) -> int:
    """Convenience function to parse connection count."""
    return ConntrackParser().parse_connection_count(output)


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Parse la sortie textuelle des commandes conntrack en structures de données
# - Gère le parsing de la liste des connexions et du compteur
# - Extrait les informations clés : protocole, IP source/destination, ports, état, paquets, bytes
# Pourquoi dans infrastructure/ (charte) :
# - C'est un parser technique qui traite la sortie brute d'une commande système
# - Le format de sortie conntrack est un détail d'implémentation
# - Produit des dicts bruts qui seront mappés en objets métier
# Ce qu'il ne contient PAS :
# ❌ Pas d'appels système (reçoit la sortie en string, ne lance pas conntrack)
# ❌ Pas de logique métier (pas de filtrage, pas de politiques)
# ❌ Pas de dépendance vers domain/, application/ ou interfaces/
# Points clés :
# - ConntrackParser : classe principale avec 2 méthodes de parsing
# - parse_connection_list() : parse 'conntrack -L' pour extraire les connexions
#   - Extrait protocol, source_ip, source_port, destination_ip, destination_port, state, packets, bytes
# - parse_connection_count() : parse 'conntrack -C' pour extraire le nombre de connexions
# - Utilise des regex pour extraire les champs de la sortie textuelle
# - Ne fait aucun I/O : reçoit des strings, retourne des dicts/int
# - Fonctions de convenance : parse_conntrack_connections(), parse_conntrack_count()
# Comment il sera utilisé (aperçu) :
# - infrastructure/backends/conntrack/adapter.py l'appellera après chaque commande
# - Les tests utiliseront des fixtures de sortie conntrack pour vérifier le parsing
#---------------------------------------------------------------------->
