# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Monitoring domain conntrack models.

Pure domain logic for network connection tracking.
This module defines what a connection IS, not how it is read
from /proc/net/nf_conntrack or conntrack-tools.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional


class ConnectionState(Enum):
    """State of a tracked network connection."""
    NEW = "new"
    ESTABLISHED = "established"
    RELATED = "related"
    INVALID = "invalid"
    TIME_WAIT = "time_wait"
    CLOSE_WAIT = "close_wait"
    SYN_SENT = "syn_sent"
    SYN_RECV = "syn_recv"
    FIN_WAIT = "fin_wait"
    LAST_ACK = "last_ack"
    CLOSED = "closed"


class ConnectionProtocol(Enum):
    """Network protocol of a connection."""
    TCP = "tcp"
    UDP = "udp"
    ICMP = "icmp"
    UNKNOWN = "unknown"


@dataclass
class Connection:
    """A single tracked network connection.
    
    Pure domain model. Contains only the structured data extracted
    from conntrack. Does not know how to read /proc or call conntrack.
    """
    source_ip: str
    destination_ip: str
    protocol: ConnectionProtocol
    state: ConnectionState = ConnectionState.NEW
    
    source_port: Optional[int] = None
    destination_port: Optional[int] = None
    
    # Counters
    packets: int = 0
    bytes_transferred: int = 0
    
    # Timing
    start_time: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    timeout: Optional[int] = None  # seconds
    
    # Optional metadata
    interface_in: Optional[str] = None
    interface_out: Optional[str] = None
    mark: Optional[int] = None
    labels: list[str] = field(default_factory=list)
    
    def is_established(self) -> bool:
        """Check if the connection is fully established."""
        return self.state == ConnectionState.ESTABLISHED
    
    def is_active(self) -> bool:
        """Check if the connection is in an active state."""
        return self.state in (
            ConnectionState.NEW,
            ConnectionState.ESTABLISHED,
            ConnectionState.RELATED,
            ConnectionState.SYN_SENT,
            ConnectionState.SYN_RECV,
        )
    
    def is_closing(self) -> bool:
        """Check if the connection is in a closing state."""
        return self.state in (
            ConnectionState.TIME_WAIT,
            ConnectionState.CLOSE_WAIT,
            ConnectionState.FIN_WAIT,
            ConnectionState.LAST_ACK,
            ConnectionState.CLOSED,
        )
    
    def is_tcp(self) -> bool:
        """Check if the connection uses TCP."""
        return self.protocol == ConnectionProtocol.TCP
    
    def is_udp(self) -> bool:
        """Check if the connection uses UDP."""
        return self.protocol == ConnectionProtocol.UDP
    
    def duration(self, now: Optional[datetime] = None) -> Optional[timedelta]:
        """Calculate the duration of the connection.
        
        Args:
            now: Current time (default: datetime.now())
        
        Returns:
            Duration as timedelta, or None if start_time is unknown
        """
        if self.start_time is None:
            return None
        
        if now is None:
            now = datetime.now()
        
        return now - self.start_time
    
    def duration_seconds(self, now: Optional[datetime] = None) -> Optional[float]:
        """Calculate the duration in seconds.
        
        Args:
            now: Current time (default: datetime.now())
        
        Returns:
            Duration in seconds, or None if start_time is unknown
        """
        duration = self.duration(now)
        if duration is None:
            return None
        return duration.total_seconds()
    
        """Check if the connection has been active for a long time.
        
        Args:
            threshold_seconds: Duration threshold in seconds (default: 1 hour)
        
        Returns:
            True if duration exceeds threshold
        """
    def is_long_lived(self, threshold_seconds: int = 3600, now: Optional[datetime] = None) -> bool:
        duration_secs = self.duration_seconds(now)
        if duration_secs is None:
            return False
        return duration_secs >= threshold_seconds   
    
    def is_suspicious(self, max_packets: int = 100000, max_bytes: int = 1_000_000_000) -> bool:
        """Check if the connection shows suspicious behavior.
        
        A connection is suspicious if it has unusually high packet or byte counts,
        which may indicate data exfiltration or DDoS.
        
        Args:
            max_packets: Maximum expected packet count
            max_bytes: Maximum expected byte count (default: 1 GB)
        
        Returns:
            True if the connection is suspicious
        """
        return self.packets > max_packets or self.bytes_transferred > max_bytes
    
    def matches_ip(self, ip: str) -> bool:
        """Check if this connection involves a specific IP (source or destination).
        
        Args:
            ip: IP address to match
        
        Returns:
            True if the IP matches source or destination
        """
        return self.source_ip == ip or self.destination_ip == ip
    
    def matches_port(self, port: int) -> bool:
        """Check if this connection involves a specific port (source or destination).
        
        Args:
            port: Port number to match
        
        Returns:
            True if the port matches source or destination
        """
        return self.source_port == port or self.destination_port == port
    
    def get_port_display(self) -> str:
        """Get a human-readable port display.
        
        Returns:
            String like "80 -> 443" or "N/A"
        """
        src = str(self.source_port) if self.source_port is not None else "?"
        dst = str(self.destination_port) if self.destination_port is not None else "?"
        return f"{src} -> {dst}"
    
    def get_summary(self) -> str:
        """Get a one-line summary of the connection.
        
        Returns:
            String like "tcp 10.0.0.1:80 -> 192.168.1.1:443 ESTABLISHED"
        """
        src_port = f":{self.source_port}" if self.source_port else ""
        dst_port = f":{self.destination_port}" if self.destination_port else ""
        return (
            f"{self.protocol.value} "
            f"{self.source_ip}{src_port} -> "
            f"{self.destination_ip}{dst_port} "
            f"{self.state.value}"
        )


def filter_connections_by_state(
    connections: list[Connection],
    state: ConnectionState,
) -> list[Connection]:
    """Filter connections by state.
    
    Args:
        connections: List of connections to filter
        state: State to match
    
    Returns:
        List of connections in the specified state
    """
    return [c for c in connections if c.state == state]


def filter_connections_by_ip(
    connections: list[Connection],
    ip: str,
) -> list[Connection]:
    """Filter connections involving a specific IP.
    
    Args:
        connections: List of connections to filter
        ip: IP address to match (source or destination)
    
    Returns:
        List of connections involving the IP
    """
    return [c for c in connections if c.matches_ip(ip)]


def filter_connections_by_protocol(
    connections: list[Connection],
    protocol: ConnectionProtocol,
) -> list[Connection]:
    """Filter connections by protocol.
    
    Args:
        connections: List of connections to filter
        protocol: Protocol to match
    
    Returns:
        List of connections using the specified protocol
    """
    return [c for c in connections if c.protocol == protocol]


def filter_active_connections(connections: list[Connection]) -> list[Connection]:
    """Filter to keep only active connections.
    
    Args:
        connections: List of connections to filter
    
    Returns:
        List of active connections
    """
    return [c for c in connections if c.is_active()]


def filter_suspicious_connections(
    connections: list[Connection],
    max_packets: int = 100000,
    max_bytes: int = 1_000_000_000,
) -> list[Connection]:
    """Filter to keep only suspicious connections.
    
    Args:
        connections: List of connections to filter
        max_packets: Maximum expected packet count
        max_bytes: Maximum expected byte count
    
    Returns:
        List of suspicious connections
    """
    return [
        c for c in connections
        if c.is_suspicious(max_packets=max_packets, max_bytes=max_bytes)
    ]


def count_by_state(connections: list[Connection]) -> dict[str, int]:
    """Count connections grouped by state.
    
    Args:
        connections: List of connections
    
    Returns:
        Dictionary mapping state name to count
    """
    counts: dict[str, int] = {}
    for conn in connections:
        state_name = conn.state.value
        counts[state_name] = counts.get(state_name, 0) + 1
    return counts


def count_by_protocol(connections: list[Connection]) -> dict[str, int]:
    """Count connections grouped by protocol.
    
    Args:
        connections: List of connections
    
    Returns:
        Dictionary mapping protocol name to count
    """
    counts: dict[str, int] = {}
    for conn in connections:
        proto_name = conn.protocol.value
        counts[proto_name] = counts.get(proto_name, 0) + 1
    return counts


def get_top_source_ips(
    connections: list[Connection],
    n: int = 10,
) -> list[tuple[str, int]]:
    """Get the top N source IPs by connection count.
    
    Args:
        connections: List of connections
        n: Number of top IPs to return
    
    Returns:
        List of (ip, count) tuples, sorted by count descending
    """
    ip_counts: dict[str, int] = {}
    for conn in connections:
        ip_counts[conn.source_ip] = ip_counts.get(conn.source_ip, 0) + 1
    
    sorted_ips = sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)
    return sorted_ips[:n]


def get_top_destination_ips(
    connections: list[Connection],
    n: int = 10,
) -> list[tuple[str, int]]:
    """Get the top N destination IPs by connection count.
    
    Args:
        connections: List of connections
        n: Number of top IPs to return
    
    Returns:
        List of (ip, count) tuples, sorted by count descending
    """
    ip_counts: dict[str, int] = {}
    for conn in connections:
        ip_counts[conn.destination_ip] = ip_counts.get(conn.destination_ip, 0) + 1
    
    sorted_ips = sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)
    return sorted_ips[:n]


def get_long_lived_connections(
    connections: list[Connection],
    threshold_seconds: int = 3600,
) -> list[Connection]:
    """Get connections that have been active for a long time.
    
    Args:
        connections: List of connections
        threshold_seconds: Duration threshold in seconds
    
    Returns:
        List of long-lived connections
    """
    return [c for c in connections if c.is_long_lived(threshold_seconds)]

# <-- INFO DEV ---------------------------------------------------------
# Rôle : 
# - Définit les modèles métier pour les connexions réseau trackées (conntrack). Ce sont des dataclasses pures qui représentent une connexion active (source, destination, port, protocole, état, durée, compteurs). Ce module ne lit aucun fichier système — il opère uniquement sur des données en mémoire.
# Pourquoi dans domain/ (charte) :
# - C'est une règle métier : qu'est-ce qu'une connexion, comment la structurer, comment la filtrer
# - Aucune dépendance externe (juste dataclasses, enum, datetime, typing)
# - Testable sans aucun accès au système (pas de lecture /proc/net/nf_conntrack)
# - Utilisé par domain/monitoring/service.py pour agréger les statistiques
# Ce qu'il ne contient PAS (règles projet) :
# ❌ Pas d'import depuis infrastructure/ (pas de lecture fichier, pas de subprocess)
# ❌ Pas d'import depuis interfaces/ (pas de rendu)
# ❌ Pas d'import depuis application/ (pas de cas d'usage)
# ❌ Pas de open(), Path.read_text(), subprocess.run() — aucun I/O
# Points clés :
# - ConnectionState : 11 états possibles (NEW, ESTABLISHED, RELATED, TIME_WAIT, etc.)
# - ConnectionProtocol : TCP, UDP, ICMP, UNKNOWN
# - Connection : dataclass principale avec IP source/dest, ports, protocole, état, compteurs, timing
# - Méthodes utilitaires :
#   - is_established(), is_active(), is_closing() : vérification d'état
#   - duration(), duration_seconds() : calcul de durée
#   - is_long_lived() : détection de connexions persistantes
#   - is_suspicious() : détection de comportement anormal (DDoS, exfiltration)
#   - matches_ip(), matches_port() : filtrage
#   - get_summary() : affichage one-line
# - Fonctions de filtrage : filter_connections_by_state(), filter_connections_by_ip(), filter_active_connections(), filter_suspicious_connections()
# - Fonctions d'agrégation : count_by_state(), count_by_protocol(), get_top_source_ips(), get_top_destination_ips()
# - Aucune dépendance externe : utilise uniquement dataclasses, enum, datetime, typing
# - Aucun I/O : ne lit ni /proc/net/nf_conntrack, ni n'appelle conntrack
# Comment il sera utilisé (aperçu) :
# - infrastructure/backends/conntrack/adapter.py lira les connexions réelles et construira des Connection
# - domain/monitoring/service.py utilisera Connection pour calculer les statistiques globales
# - application/queries/conntrack_status.py affichera l'état des connexions
# - interfaces/cli/renderers/monitoring_live.py affichera les connexions en temps réel
#---------------------------------------------------------------------->
