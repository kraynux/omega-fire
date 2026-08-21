# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Query: List firewall rules.

Provides read-only access to the firewall rules across backends.
Used by menu 3.3 (Lister les règles).

Conforms to Omega-Fire architecture charter:
- Read-only query, no side effects
- Consumes ports/firewall.py contract (not infrastructure directly)
- Returns formatted string for UI display
- No dependency on interfaces/ or infrastructure/ directly
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional


@dataclass
class FirewallRuleEntry:
    """DTO representing a firewall rule entry.
    
    Attributes:
        id: Rule identifier (backend-specific).
        backend: Backend that owns the rule (nftables, iptables).
        family: IP family (inet, ip, ip6).
        table: Table name.
        chain: Chain name (input, output, forward).
        protocol: Protocol (tcp, udp, icmp, etc.).
        port: Port or port range.
        source: Source address/CIDR.
        destination: Destination address/CIDR.
        action: Rule action (accept, drop, reject, log).
        packets: Packet counter.
        bytes: Byte counter.
    """
    id: str
    backend: str
    family: str = ""
    table: str = ""
    chain: str = ""
    protocol: str = ""
    port: str = ""
    source: str = ""
    destination: str = ""
    action: str = ""
    packets: int = 0
    bytes: int = 0


@dataclass
class FirewallRulesResult:
    """Result of the list rules query.
    
    Attributes:
        entries: List of firewall rule entries.
        total_count: Total number of rules.
        by_backend: Count per backend.
        message: Human-readable summary.
    """
    entries: List[FirewallRuleEntry]
    total_count: int
    by_backend: dict
    message: str


def list_rules(
    firewall_port: Optional[Any] = None,
    backend_filter: str = "",
) -> FirewallRulesResult:
    """3.3: List all firewall rules across backends.
    
    Args:
        firewall_port: FirewallPort implementation. If None, returns empty result.
        backend_filter: Optional filter by backend name ("nftables", "iptables").
    
    Returns:
        FirewallRulesResult with entries and counts.
    """
    if firewall_port is None:
        return FirewallRulesResult(
            entries=[],
            total_count=0,
            by_backend={},
            message="⚠️ Port FirewallPort non disponible. Les adapters infrastructure/ ne sont pas encore câblés.",
        )
    
    try:
        if hasattr(firewall_port, 'list_rules'):
            raw_entries = firewall_port.list_rules()
        else:
            return FirewallRulesResult(
                entries=[],
                total_count=0,
                by_backend={},
                message="⚠️ Le port ne supporte pas list_rules().",
            )
        
        entries = []
        by_backend: dict = {}
        
        for entry in raw_entries:
            if isinstance(entry, dict):
                dto = FirewallRuleEntry(
                    id=str(entry.get("id", "")),
                    backend=entry.get("backend", "unknown"),
                    family=entry.get("family", ""),
                    table=entry.get("table", ""),
                    chain=entry.get("chain", ""),
                    protocol=entry.get("protocol", ""),
                    port=str(entry.get("port", "")),
                    source=entry.get("source", ""),
                    destination=entry.get("destination", ""),
                    action=entry.get("action", ""),
                    packets=int(entry.get("packets", 0)),
                    bytes=int(entry.get("bytes", 0)),
                )
            elif hasattr(entry, "id"):
                dto = FirewallRuleEntry(
                    id=str(entry.id),
                    backend=getattr(entry, "backend", "unknown"),
                    family=getattr(entry, "family", ""),
                    table=getattr(entry, "table", ""),
                    chain=getattr(entry, "chain", ""),
                    protocol=getattr(entry, "protocol", ""),
                    port=str(getattr(entry, "port", "")),
                    source=getattr(entry, "source", ""),
                    destination=getattr(entry, "destination", ""),
                    action=getattr(entry, "action", ""),
                    packets=int(getattr(entry, "packets", 0)),
                    bytes=int(getattr(entry, "bytes", 0)),
                )
            else:
                continue
            
            if backend_filter and dto.backend != backend_filter:
                continue
            
            entries.append(dto)
            by_backend[dto.backend] = by_backend.get(dto.backend, 0) + 1
        
        return FirewallRulesResult(
            entries=entries,
            total_count=len(entries),
            by_backend=by_backend,
            message=f"{len(entries)} règle(s) trouvée(s).",
        )
    
    except Exception as e:
        return FirewallRulesResult(
            entries=[],
            total_count=0,
            by_backend={},
            message=f"❌ Erreur lors de la récupération des règles : {e}",
        )


def format_rules_table(result: FirewallRulesResult) -> str:
    """Format the rules result as a readable string table.
    
    Args:
        result: The query result.
    
    Returns:
        Formatted string for UI display.
    """
    lines = ["═══ RÈGLES FIREWALL ═══", ""]
    
    if not result.entries:
        lines.append(result.message)
        return "\n".join(lines)
    
    lines.append(f"Total : {result.total_count} règle(s)")
    if result.by_backend:
        backend_summary = " | ".join(f"{k}: {v}" for k, v in result.by_backend.items())
        lines.append(f"Par backend : {backend_summary}")
    lines.append("")
    
    lines.append(f"{'ID':<8} {'Backend':<10} {'Proto':<6} {'Port':<8} {'Source':<18} {'Dest':<18} {'Action':<8} {'Packets':<10} {'Bytes'}")
    lines.append("─" * 110)
    
    for entry in result.entries:
        source = entry.source[:18] if entry.source else "any"
        dest = entry.destination[:18] if entry.destination else "any"
        lines.append(
            f"{entry.id:<8} {entry.backend:<10} {entry.protocol:<6} {entry.port:<8} "
            f"{source:<18} {dest:<18} {entry.action:<8} {entry.packets:<10} {entry.bytes}"
        )
    
    lines.append("")
    lines.append(result.message)
    
    return "\n".join(lines)


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Query read-only pour lister les règles firewall dans tous les backends.
# - Utilisée par le menu 3.3 (Lister les règles).
# - Consomme le port FirewallPort (ports/firewall.py).
# - Retourne un DTO structuré (FirewallRulesResult) + formatage pour l'UI.
#
# Pourquoi dans application/queries/ (charte) :
# - C'est une query (lecture seule), pas une command (modification).
# - Consomme un port (FirewallPort), pas une implémentation concrète.
# - Retourne des DTOs, pas des objets d'infrastructure.
# - Ne dépend pas de infrastructure/ ni interfaces/.
#
# Ce qu'il ne contient PAS :
# ❌ Pas d'import de infrastructure/backends/ (nftables, iptables).
# ❌ Pas d'appel système direct (subprocess, nft list, iptables -L).
# ❌ Pas de logique métier de filtrage complexe (c'est le rôle de domain/).
# ❌ Pas de rendu UI (c'est le rôle de interfaces/).
# ❌ Pas de modification des règles (c'est le rôle des commands).
#
# Points clés :
# - FirewallRuleEntry : DTO représentant une règle (id, backend, proto, port, source, dest, action, counters).
# - FirewallRulesResult : DTO de résultat (entries, total_count, by_backend, message).
# - list_rules() : fonction principale avec firewall_port optionnel.
# - format_rules_table() : formatage pour affichage UI avec compteurs.
# - Support du filtrage par backend (backend_filter).
# - Gestion d'erreur via Result structuré (pas d'exception brute).
# - Fallback propre si le port n'est pas disponible (message informatif).
#
# Flux d'exécution :
# interfaces/cli/actions.py : action_3_3_list_rules(ctx)
#   ↓
# application/queries/list_rules.py : list_rules(firewall_port)
#   ↓
# ports/firewall.py : FirewallPort.list_rules()
#   ↓
# infrastructure/backends/*/adapter.py : implémentation concrète
#   ↓
# Retourne FirewallRulesResult → format_rules_table() → affichage UI
#---------------------------------------------------------------------->
