# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Rules domain models.

Pure domain logic for firewall rules. No external dependencies.
This module defines what a firewall rule IS, not how it is applied
by nftables or iptables.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class RuleAction(Enum):
    """Action to take when a rule matches."""
    ACCEPT = "accept"
    DROP = "drop"
    REJECT = "reject"
    LOG = "log"


class RuleChain(Enum):
    """Netfilter chain where the rule applies."""
    INPUT = "input"
    OUTPUT = "output"
    FORWARD = "forward"


class RuleProtocol(Enum):
    """Network protocol for the rule."""
    TCP = "tcp"
    UDP = "udp"
    ICMP = "icmp"


class RuleFamily(Enum):
    """Address family for the rule."""
    INET = "inet"  # IPv4 + IPv6
    IP = "ip"      # IPv4 only
    IP6 = "ip6"    # IPv6 only


@dataclass
class FirewallRule:
    """A single firewall rule.
    
    Pure domain model. The 'backend' field is a label only
    ('nftables', 'iptables'), not a dependency.
    """
    backend: str  # label: 'nftables' | 'iptables'
    family: RuleFamily
    table_name: str
    chain: RuleChain
    protocol: Optional[RuleProtocol] = None
    port_start: Optional[int] = None
    port_end: Optional[int] = None
    source_cidr: Optional[str] = None
    dest_cidr: Optional[str] = None
    action: RuleAction = RuleAction.ACCEPT
    priority: int = 0
    comment: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    enabled: bool = True
    rule_id: Optional[int] = None  # Set by infrastructure when persisted
    external_ref: Optional[str] = None  # Technical backend identifier (nft handle, iptables line number) — NOT the DB id
    origin: str = "imported"  # "managed" (created by Omega-Fire) or "imported" (detected via backend sync)
    interface: Optional[str] = None  # Network interface name (e.g. "eth0"); None = ANY
    def is_port_range(self) -> bool:
        """Check if this rule specifies a port range."""
        return self.port_start is not None and self.port_end is not None
    
    def is_single_port(self) -> bool:
        """Check if this rule specifies a single port."""
        return (
            self.port_start is not None
            and self.port_end is not None
            and self.port_start == self.port_end
        )
    
    def get_port_display(self) -> str:
        """Get a human-readable port representation."""
        if self.is_single_port():
            return str(self.port_start)
        elif self.is_port_range():
            return f"{self.port_start}-{self.port_end}"
        return "*"
    
    def matches_traffic(
        self,
        protocol: str,
        port: int,
        source: str,
        destination: str
    ) -> bool:
        """Check if this rule matches the given traffic parameters.
        
        This is a simplified match logic for domain-level filtering.
        Real matching is done by nftables/iptables kernels.
        """
        # Protocol match
        if self.protocol and self.protocol.value != protocol:
            return False
        
        # Port match
        if self.port_start is not None and self.port_end is not None:
            if not (self.port_start <= port <= self.port_end):
                return False
        
        # Source match (simplified — real CIDR matching is in infrastructure)
        if self.source_cidr and self.source_cidr != source:
            return False
        
        # Destination match
        if self.dest_cidr and self.dest_cidr != destination:
            return False
        
        return True


@dataclass
class RuleSet:
    """Collection of firewall rules with query helpers."""
    rules: list[FirewallRule] = field(default_factory=list)
    
    def add(self, rule: FirewallRule) -> None:
        """Add a rule to the set."""
        self.rules.append(rule)
    
    def remove(self, rule_id: int) -> Optional[FirewallRule]:
        """Remove a rule by ID. Returns the removed rule or None."""
        for i, rule in enumerate(self.rules):
            if rule.rule_id == rule_id:
                return self.rules.pop(i)
        return None
    
    def get_by_backend(self, backend: str) -> list[FirewallRule]:
        """Get rules filtered by backend."""
        return [r for r in self.rules if r.backend == backend]
    
    def get_by_chain(self, chain: RuleChain) -> list[FirewallRule]:
        """Get rules filtered by chain."""
        return [r for r in self.rules if r.chain == chain]
    
    def get_enabled(self) -> list[FirewallRule]:
        """Get only enabled rules."""
        return [r for r in self.rules if r.enabled]
    
    def get_by_priority(self) -> list[FirewallRule]:
        """Get rules sorted by priority (ascending)."""
        return sorted(self.rules, key=lambda r: r.priority)

# <-- INFO DEV ----------------------------------------------------------
# Rôle :
# - Définit les modèles métier pour les règles firewall. Ce sont des dataclasses pures qui représentent une règle de filtrage (protocole, port, source, destination, action), un ensemble de règles (RuleSet), et les concepts associés (chaîne, action, famille).
# Pourquoi dans domain/ (charte) :
# - C'est une règle métier : qu'est-ce qu'une règle firewall, quels sont ses composants
# - Aucune dépendance externe (juste dataclasses, enum, typing)
# - Testable sans aucun backend réel (nftables, iptables)
# - Utilisé par application/commands/create_rule.py et domain/rules/service.py
# Ce qu'il ne contient PAS (règles projet) :
# ❌ Pas d'import depuis infrastructure/ (pas de parsing nft/iptables)
# ❌ Pas d'import depuis interfaces/ (pas de rendu)
# ❌ Pas d'import depuis application/ (pas de cas d'usage)
# ❌ Pas de logique d'exécution (juste la structure de données)
# Points clés :
# - FirewallRule : modèle pur d'une règle firewall, indépendant de nftables/iptables
#   - external_ref : identifiant technique backend (handle nft, ligne iptables brute),
#     distinct de rule_id (ID de persistance SQLite)
#   - origin : "managed" (créée via Omega-Fire, ex. 3.1/3.4) ou "imported"
#     (détectée lors d'une synchronisation backend)
#   - interface : nom de l'interface réseau associée (ex. "eth0"), None = ANY
# - RuleSet : conteneur avec des requêtes métier (par backend, chaîne, priorité)
# - backend est une chaîne label, pas une référence à un adaptateur
# - matches_traffic() : logique de correspondance simplifiée pour le domaine (le vrai matching est dans le noyau via nftables/iptables)
# - Aucune dépendance externe : testable en mémoire pure
# Comment il sera utilisé (aperçu) :
# - domain/rules/service.py utilisera ces modèles pour orchestrer les opérations sur les règles
# - application/commands/create_rule.py construira un FirewallRule et le passera au service
# - infrastructure/backends/nftables/adapter.py transformera un FirewallRule en commande nft (via un mapper)
#---------------------------------------------------------------------->
