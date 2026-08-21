# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Query: Get conntrack connection status.

Provides read-only access to the current network connections tracked by conntrack.
Used by menu 8.2 (État des connexions).

Conforms to Omega-Fire architecture charter:
- Read-only query, no side effects
- Consumes ports/monitoring.py contract (not infrastructure directly)
- Returns formatted string for UI display
- No dependency on interfaces/ or infrastructure/ directly
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass
class ConntrackEntry:
    """DTO representing a conntrack connection entry.
    
    Attributes:
        protocol: Protocol (tcp, udp, icmp).
        source_ip: Source IP address.
        source_port: Source port.
        destination_ip: Destination IP address.
        destination_port: Destination port.
        state: Connection state (ESTABLISHED, SYN_SENT, TIME_WAIT, etc.).
        packets: Number of packets seen.
        bytes: Number of bytes seen.
        timeout: Remaining timeout in seconds.
    """
    protocol: str
    source_ip: str
    source_port: int = 0
    destination_ip: str = ""
    destination_port: int = 0
    state: str = ""
    packets: int = 0
    bytes: int = 0
    timeout: int = 0


@dataclass
class ConntrackStatusResult:
    """Result of the conntrack status query.
    
    Attributes:
        entries: List of conntrack entries.
        total_count: Total number of tracked connections.
        by_protocol: Count per protocol.
        by_state: Count per state.
        message: Human-readable summary.
    """
    entries: List[ConntrackEntry]
    total_count: int
    by_protocol: dict
    by_state: dict
    message: str


def get_conntrack_status(
    monitoring_port: Optional[Any] = None,
    protocol_filter: str = "",
    state_filter: str = "",
    limit: int = 100,
) -> ConntrackStatusResult:
    """8.2: Get the status of tracked connections via conntrack.
    
    Args:
        monitoring_port: MonitoringPort implementation. If None, returns empty result.
        protocol_filter: Optional filter by protocol ("tcp", "udp", "icmp").
        state_filter: Optional filter by state ("ESTABLISHED", "SYN_SENT", etc.).
        limit: Maximum number of entries to return (default: 100).
    
    Returns:
        ConntrackStatusResult with entries and counts.
    """
    if monitoring_port is None:
        return ConntrackStatusResult(
            entries=[],
            total_count=0,
            by_protocol={},
            by_state={},
            message="⚠️ Port MonitoringPort non disponible. Les adapters infrastructure/ ne sont pas encore câblés.",
        )
    
    try:
        if hasattr(monitoring_port, 'list_connections'):
            raw_entries = monitoring_port.list_connections()
        else:
            return ConntrackStatusResult(
                entries=[],
                total_count=0,
                by_protocol={},
                by_state={},
                message="⚠️ Le port ne supporte pas list_connections().",
            )
        
        entries = []
        by_protocol: dict = {}
        by_state: dict = {}
        
        for entry in raw_entries:
            if isinstance(entry, dict):
                dto = ConntrackEntry(
                    protocol=entry.get("protocol", ""),
                    source_ip=entry.get("source_ip", ""),
                    source_port=int(entry.get("source_port", 0)),
                    destination_ip=entry.get("destination_ip", ""),
                    destination_port=int(entry.get("destination_port", 0)),
                    state=entry.get("state", ""),
                    packets=int(entry.get("packets", 0)),
                    bytes=int(entry.get("bytes", 0)),
                    timeout=int(entry.get("timeout", 0)),
                )
            elif hasattr(entry, "protocol"):
                dto = ConntrackEntry(
                    protocol=entry.protocol,
                    source_ip=getattr(entry, "source_ip", ""),
                    source_port=int(getattr(entry, "source_port", 0)),
                    destination_ip=getattr(entry, "destination_ip", ""),
                    destination_port=int(getattr(entry, "destination_port", 0)),
                    state=getattr(entry, "state", ""),
                    packets=int(getattr(entry, "packets", 0)),
                    bytes=int(getattr(entry, "bytes", 0)),
                    timeout=int(getattr(entry, "timeout", 0)),
                )
            else:
                continue
            
            # Apply filters
            if protocol_filter and dto.protocol.lower() != protocol_filter.lower():
                continue
            if state_filter and dto.state.upper() != state_filter.upper():
                continue
            
            entries.append(dto)
            by_protocol[dto.protocol] = by_protocol.get(dto.protocol, 0) + 1
            if dto.state:
                by_state[dto.state] = by_state.get(dto.state, 0) + 1
        
        # Apply limit
        if len(entries) > limit:
            entries = entries[:limit]
        
        return ConntrackStatusResult(
            entries=entries,
            total_count=len(entries),
            by_protocol=by_protocol,
            by_state=by_state,
            message=f"{len(entries)} connexion(s) suivie(s) par conntrack.",
        )
    
    except Exception as e:
        return ConntrackStatusResult(
            entries=[],
            total_count=0,
            by_protocol={},
            by_state={},
            message=f"❌ Erreur lors de la récupération des connexions : {e}",
        )

# Points clés :
# - ConntrackEntry : DTO représentant une connexion (proto, src, dst, state, packets, bytes).
# - ConntrackStatusResult : DTO de résultat (entries, compteurs, message).
# - get_conntrack_status() : fonction principale avec monitoring_port optionnel.
# - Support du filtrage par protocole (protocol_filter).
# - Support du filtrage par état (state_filter).
# - Support de la limitation (limit).
# - Gestion d'erreur via message structuré (pas d'exception brute).
# - Fallback propre si le port n'est pas disponible.
# - CORRECTIF (chantier menu 8.2) : format_conntrack_table() a été
#   retirée — elle construisait un rendu de tableau en texte brut
#   directement dans application/, violation de charte que ce fichier
#   documentait lui-même sans jamais la respecter. Le rendu vit
#   désormais dans interfaces/cli/renderers/conntrack_view.py
#   (render_conntrack_summary()/render_conntrack_table(), vraie Table
#   Rich avec theme_registry).
#
# Flux d'exécution :
# interfaces/cli/actions.py : action_8_2_conntrack_status(ctx)
#   ↓
# application/queries/conntrack_status.py : get_conntrack_status(monitoring_port)
#   ↓
# ports/monitoring.py : MonitoringPort.list_connections()
#   ↓
# infrastructure/backends/conntrack/adapter.py : implémentation concrète
#   ↓
# Retourne ConntrackStatusResult → interfaces/cli/renderers/
#   conntrack_view.py (render_conntrack_summary()/render_conntrack_table())
#---------------------------------------------------------------------->
