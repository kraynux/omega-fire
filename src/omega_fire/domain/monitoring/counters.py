# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)

"""Monitoring domain counters.

Pure domain logic for metric counters.
This module defines what counters ARE, not how they are collected
from the system. Counters aggregate metrics in memory.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class PacketCounter:
    """Counter for network packets and bytes.
    
    Tracks packet counts and byte volumes for a specific entity
    (rule, connection, interface, etc.).
    """
    packets_in: int = 0
    packets_out: int = 0
    bytes_in: int = 0
    bytes_out: int = 0
    last_updated: Optional[datetime] = None
    
    def total_packets(self) -> int:
        """Get total packet count (in + out)."""
        return self.packets_in + self.packets_out
    
    def total_bytes(self) -> int:
        """Get total byte count (in + out)."""
        return self.bytes_in + self.bytes_out
    
    def update(
        self,
        packets_in: int = 0,
        packets_out: int = 0,
        bytes_in: int = 0,
        bytes_out: int = 0,
    ) -> None:
        """Update counters with new absolute values.
        
        Args:
            packets_in: New incoming packet count
            packets_out: New outgoing packet count
            bytes_in: New incoming byte count
            bytes_out: New outgoing byte count
        """
        self.packets_in = packets_in
        self.packets_out = packets_out
        self.bytes_in = bytes_in
        self.bytes_out = bytes_out
        self.last_updated = datetime.now()
    
    def increment(
        self,
        packets_in: int = 0,
        packets_out: int = 0,
        bytes_in: int = 0,
        bytes_out: int = 0,
    ) -> None:
        """Increment counters by the given amounts.
        
        Args:
            packets_in: Packets to add to incoming count
            packets_out: Packets to add to outgoing count
            bytes_in: Bytes to add to incoming count
            bytes_out: Bytes to add to outgoing count
        """
        self.packets_in += packets_in
        self.packets_out += packets_out
        self.bytes_in += bytes_in
        self.bytes_out += bytes_out
        self.last_updated = datetime.now()
    
    def reset(self) -> None:
        """Reset all counters to zero."""
        self.packets_in = 0
        self.packets_out = 0
        self.bytes_in = 0
        self.bytes_out = 0
        self.last_updated = datetime.now()
    
    def rate_per_second(self, elapsed_seconds: float) -> dict[str, float]:
        """Calculate rates per second.
        
        Args:
            elapsed_seconds: Time elapsed since last measurement
        
        Returns:
            Dictionary with rates for each counter
        """
        if elapsed_seconds <= 0:
            return {
                "packets_in_per_sec": 0.0,
                "packets_out_per_sec": 0.0,
                "bytes_in_per_sec": 0.0,
                "bytes_out_per_sec": 0.0,
            }
        
        return {
            "packets_in_per_sec": self.packets_in / elapsed_seconds,
            "packets_out_per_sec": self.packets_out / elapsed_seconds,
            "bytes_in_per_sec": self.bytes_in / elapsed_seconds,
            "bytes_out_per_sec": self.bytes_out / elapsed_seconds,
        }


@dataclass
class BanCounter:
    """Counter for ban events.
    
    Tracks the number of ban/unban events, currently banned IPs,
    and ban statistics per backend.
    """
    total_bans: int = 0
    total_unbans: int = 0
    currently_banned: int = 0
    peak_banned: int = 0
    last_updated: Optional[datetime] = None
    
    # Per-backend counters
    bans_by_backend: dict[str, int] = field(default_factory=dict)
    unbans_by_backend: dict[str, int] = field(default_factory=dict)
    
    def record_ban(self, backend: str = "unknown") -> None:
        """Record a new ban event.
        
        Args:
            backend: Backend name where the ban occurred
        """
        self.total_bans += 1
        self.currently_banned += 1
        self.bans_by_backend[backend] = self.bans_by_backend.get(backend, 0) + 1
        
        # Update peak if necessary
        if self.currently_banned > self.peak_banned:
            self.peak_banned = self.currently_banned
        
        self.last_updated = datetime.now()
    
    def record_unban(self, backend: str = "unknown") -> None:
        """Record an unban event.
        
        Args:
            backend: Backend name where the unban occurred
        """
        self.total_unbans += 1
        self.currently_banned = max(0, self.currently_banned - 1)
        self.unbans_by_backend[backend] = self.unbans_by_backend.get(backend, 0) + 1
        self.last_updated = datetime.now()
    
    def reset(self) -> None:
        """Reset all counters to zero."""
        self.total_bans = 0
        self.total_unbans = 0
        self.currently_banned = 0
        self.peak_banned = 0
        self.bans_by_backend.clear()
        self.unbans_by_backend.clear()
        self.last_updated = datetime.now()
    
    def ban_rate(self) -> float:
        """Calculate the ban rate (bans / (bans + unbans)).
        
        Returns:
            Rate between 0.0 and 1.0, or 0.0 if no events
        """
        total_events = self.total_bans + self.total_unbans
        if total_events == 0:
            return 0.0
        return self.total_bans / total_events
    
    def get_backend_stats(self, backend: str) -> dict[str, int]:
        """Get ban/unban statistics for a specific backend.
        
        Args:
            backend: Backend name
        
        Returns:
            Dictionary with bans and unbans count
        """
        return {
            "bans": self.bans_by_backend.get(backend, 0),
            "unbans": self.unbans_by_backend.get(backend, 0),
        }


@dataclass
class RuleCounter:
    """Counter for firewall rule matches.
    
    Tracks how many times each rule has been matched,
    and aggregates statistics by action and chain.
    """
    total_matches: int = 0
    matches_by_action: dict[str, int] = field(default_factory=dict)
    matches_by_chain: dict[str, int] = field(default_factory=dict)
    matches_by_rule_id: dict[int, int] = field(default_factory=dict)
    last_updated: Optional[datetime] = None
    
    def record_match(
        self,
        action: str,
        chain: str,
        rule_id: Optional[int] = None,
    ) -> None:
        """Record a rule match.
        
        Args:
            action: Rule action (accept, drop, reject, log)
            chain: Rule chain (input, output, forward)
            rule_id: Optional rule identifier
        """
        self.total_matches += 1
        self.matches_by_action[action] = self.matches_by_action.get(action, 0) + 1
        self.matches_by_chain[chain] = self.matches_by_chain.get(chain, 0) + 1
        
        if rule_id is not None:
            self.matches_by_rule_id[rule_id] = self.matches_by_rule_id.get(rule_id, 0) + 1
        
        self.last_updated = datetime.now()
    
    def reset(self) -> None:
        """Reset all counters to zero."""
        self.total_matches = 0
        self.matches_by_action.clear()
        self.matches_by_chain.clear()
        self.matches_by_rule_id.clear()
        self.last_updated = datetime.now()
    
    def get_top_rules(self, n: int = 10) -> list[tuple[int, int]]:
        """Get the top N most matched rules.
        
        Args:
            n: Number of top rules to return
        
        Returns:
            List of (rule_id, match_count) tuples, sorted by count descending
        """
        sorted_rules = sorted(
            self.matches_by_rule_id.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_rules[:n]
    
    def get_action_distribution(self) -> dict[str, float]:
        """Get the distribution of matches by action.
        
        Returns:
            Dictionary mapping action to percentage (0.0 to 100.0)
        """
        if self.total_matches == 0:
            return {}
        
        return {
            action: (count / self.total_matches) * 100.0
            for action, count in self.matches_by_action.items()
        }


@dataclass
class CounterSet:
    """Aggregated set of all monitoring counters.
    
    Combines packet, ban, and rule counters into a single
    cohesive monitoring snapshot.
    """
    packets: PacketCounter = field(default_factory=PacketCounter)
    bans: BanCounter = field(default_factory=BanCounter)
    rules: RuleCounter = field(default_factory=RuleCounter)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def update_timestamp(self) -> None:
        """Update the timestamp to current time."""
        self.timestamp = datetime.now()
    
    def reset_all(self) -> None:
        """Reset all counters to zero."""
        self.packets.reset()
        self.bans.reset()
        self.rules.reset()
        self.timestamp = datetime.now()
    
    def get_summary(self) -> dict[str, int]:
        """Get a summary of all counters.
        
        Returns:
            Dictionary with key metrics
        """
        return {
            "total_packets": self.packets.total_packets(),
            "total_bytes": self.packets.total_bytes(),
            "total_bans": self.bans.total_bans,
            "total_unbans": self.bans.total_unbans,
            "currently_banned": self.bans.currently_banned,
            "peak_banned": self.bans.peak_banned,
            "total_rule_matches": self.rules.total_matches,
        }
    
    def is_active(self) -> bool:
        """Check if there has been any activity.
        
        Returns:
            True if any counter has recorded events
        """
        return (
            self.packets.total_packets() > 0
            or self.bans.total_bans > 0
            or self.rules.total_matches > 0
        )


def merge_packet_counters(
    counters: list[PacketCounter],
) -> PacketCounter:
    """Merge multiple packet counters into one.
    
    Args:
        counters: List of packet counters to merge
    
    Returns:
        Single PacketCounter with aggregated values
    """
    merged = PacketCounter()
    
    for counter in counters:
        merged.packets_in += counter.packets_in
        merged.packets_out += counter.packets_out
        merged.bytes_in += counter.bytes_in
        merged.bytes_out += counter.bytes_out
        
        # Keep the most recent update time
        if counter.last_updated:
            if merged.last_updated is None or counter.last_updated > merged.last_updated:
                merged.last_updated = counter.last_updated
    
    return merged


def merge_ban_counters(
    counters: list[BanCounter],
) -> BanCounter:
    """Merge multiple ban counters into one.
    
    Args:
        counters: List of ban counters to merge
    
    Returns:
        Single BanCounter with aggregated values
    """
    merged = BanCounter()
    
    for counter in counters:
        merged.total_bans += counter.total_bans
        merged.total_unbans += counter.total_unbans
        merged.currently_banned += counter.currently_banned
        
        if counter.peak_banned > merged.peak_banned:
            merged.peak_banned = counter.peak_banned
        
        # Merge per-backend counters
        for backend, count in counter.bans_by_backend.items():
            merged.bans_by_backend[backend] = merged.bans_by_backend.get(backend, 0) + count
        
        for backend, count in counter.unbans_by_backend.items():
            merged.unbans_by_backend[backend] = merged.unbans_by_backend.get(backend, 0) + count
        
        # Keep the most recent update time
        if counter.last_updated:
            if merged.last_updated is None or counter.last_updated > merged.last_updated:
                merged.last_updated = counter.last_updated
    
    return merged


def merge_rule_counters(
    counters: list[RuleCounter],
) -> RuleCounter:
    """Merge multiple rule counters into one.
    
    Args:
        counters: List of rule counters to merge
    
    Returns:
        Single RuleCounter with aggregated values
    """
    merged = RuleCounter()
    
    for counter in counters:
        merged.total_matches += counter.total_matches
        
        # Merge by action
        for action, count in counter.matches_by_action.items():
            merged.matches_by_action[action] = merged.matches_by_action.get(action, 0) + count
        
        # Merge by chain
        for chain, count in counter.matches_by_chain.items():
            merged.matches_by_chain[chain] = merged.matches_by_chain.get(chain, 0) + count
        
        # Merge by rule ID
        for rule_id, count in counter.matches_by_rule_id.items():
            merged.matches_by_rule_id[rule_id] = merged.matches_by_rule_id.get(rule_id, 0) + count
        
        # Keep the most recent update time
        if counter.last_updated:
            if merged.last_updated is None or counter.last_updated > merged.last_updated:
                merged.last_updated = counter.last_updated
    
    return merged


def merge_counter_sets(
    counter_sets: list[CounterSet],
) -> CounterSet:
    """Merge multiple counter sets into one.
    
    Args:
        counter_sets: List of counter sets to merge
    
    Returns:
        Single CounterSet with aggregated values
    """
    merged = CounterSet()
    
    # Merge each type of counter
    merged.packets = merge_packet_counters([cs.packets for cs in counter_sets])
    merged.bans = merge_ban_counters([cs.bans for cs in counter_sets])
    merged.rules = merge_rule_counters([cs.rules for cs in counter_sets])
    
    # Keep the most recent timestamp
    for cs in counter_sets:
        if cs.timestamp > merged.timestamp:
            merged.timestamp = cs.timestamp
    
    return merged

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit les modèles de compteurs pour le monitoring : compteurs de paquets, compteurs de bans, compteurs de règles. Ce sont des dataclasses pures qui agrègent des métriques en mémoire.
# Pourquoi dans domain/ (charte) :
# - C'est une règle métier : qu'est-ce qu'un compteur, comment l'agréger
# - Aucune dépendance externe (juste dataclasses, datetime, typing)
# - Testable en mémoire pure
# - Utilisé par domain/monitoring/service.py pour agréger les statistiques
# Ce qu'il ne contient PAS (règles projet) :
# ❌ Pas d'import depuis infrastructure/ (pas de lecture système)
# ❌ Pas d'import depuis interfaces/ (pas de rendu)
# ❌ Pas d'import depuis application/ (pas de cas d'usage)
# ❌ Pas de subprocess, open(), sqlite3 — aucun I/O
# Points clés:
# - PacketCounter : compteurs de paquets/bytes (in/out), avec update(), increment(), reset(), rate_per_second()
# - BanCounter : compteurs de bans/unbans, avec record_ban(), record_unban(), tracking par backend, peak_banned
# - RuleCounter : compteurs de matches de règles, avec record_match(), tracking par action/chain/rule_id, get_top_rules()
# - CounterSet : agrège les 3 types de compteurs en un snapshot cohérent
# - Fonctions de merge : merge_packet_counters(), merge_ban_counters(), merge_rule_counters(), merge_counter_sets()
# - Aucune dépendance externe : utilise uniquement dataclasses, datetime, typing
# - Aucun I/O : ne lit ni n'écrit aucun fichier, n'appelle aucun système
# Comment il sera utilisé (aperçu) :
# - infrastructure/backends/nftables/adapter.py mettra à jour les PacketCounter à chaque règle matchée
# - infrastructure/backends/fail2ban/adapter.py appellera record_ban() / record_unban()
# - domain/monitoring/service.py utilisera CounterSet pour agréger les statistiques globales
# - application/queries/monitoring_status.py affichera le résumé via get_summary()
#---------------------------------------------------------------------->
