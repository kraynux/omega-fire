# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Monitoring domain stats.

Pure domain logic for aggregated monitoring statistics.
This module defines what monitoring stats ARE, not how they are
collected from the system. Stats aggregate metrics from counters,
connections, bans, and rules.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from omega_fire.domain.monitoring.counters import CounterSet


@dataclass
class BackendStats:
    """Statistics for a specific firewall backend.
    
    Contains metrics about bans, rules, and activity for a single
    backend (nftables or iptables).
    """
    backend: str
    active_bans: int = 0
    total_rules: int = 0
    accept_rules: int = 0
    drop_rules: int = 0
    reject_rules: int = 0
    log_rules: int = 0
    
    def rule_distribution(self) -> dict[str, float]:
        """Calculate the distribution of rules by action.
        
        Returns:
            Dictionary mapping action to percentage (0.0 to 100.0)
        """
        if self.total_rules == 0:
            return {}
        
        return {
            "accept": (self.accept_rules / self.total_rules) * 100.0,
            "drop": (self.drop_rules / self.total_rules) * 100.0,
            "reject": (self.reject_rules / self.total_rules) * 100.0,
            "log": (self.log_rules / self.total_rules) * 100.0,
        }
    
    def is_empty(self) -> bool:
        """Check if the backend has no activity.
        
        Returns:
            True if no bans and no rules
        """
        return self.active_bans == 0 and self.total_rules == 0
    
    def get_summary(self) -> dict[str, int]:
        """Get a summary of backend statistics.
        
        Returns:
            Dictionary with key metrics
        """
        return {
            "backend": self.backend,
            "active_bans": self.active_bans,
            "total_rules": self.total_rules,
            "accept_rules": self.accept_rules,
            "drop_rules": self.drop_rules,
            "reject_rules": self.reject_rules,
        }


@dataclass
class TimeSeriesPoint:
    """A single point in a time series.
    
    Used for tracking metrics over time (e.g., bans per minute,
    connections per hour).
    """
    timestamp: datetime
    value: float
    label: Optional[str] = None
    
    def is_recent(self, threshold_seconds: int = 300) -> bool:
        """Check if this point is recent (within threshold).
        
        Args:
            threshold_seconds: Time threshold in seconds (default: 5 minutes)
        
        Returns:
            True if the point is within the threshold
        """
        now = datetime.now()
        delta = (now - self.timestamp).total_seconds()
        return delta <= threshold_seconds


@dataclass
class MonitoringStats:
    """Comprehensive monitoring statistics for the firewall.
    
    Aggregates all metrics: bans, rules, jails, connections, counters.
    This is the main data structure returned by monitoring queries.
    """
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Global counts
    total_bans: int = 0
    total_rules: int = 0
    total_jails: int = 0
    active_jails: int = 0
    total_connections: int = 0
    established_connections: int = 0
    new_connections: int = 0
    
    # Per-backend stats
    nftables: BackendStats = field(default_factory=lambda: BackendStats(backend="nftables"))
    iptables: BackendStats = field(default_factory=lambda: BackendStats(backend="iptables"))
    
    # Counters
    counters: CounterSet = field(default_factory=CounterSet)
    
    # Time series (optional, for trend analysis)
    bans_per_minute: list[TimeSeriesPoint] = field(default_factory=list)
    connections_per_minute: list[TimeSeriesPoint] = field(default_factory=list)
    
    def get_total_active_bans(self) -> int:
        """Get the total number of active bans across all backends.
        
        Returns:
            Sum of active bans from nftables and iptables
        """
        return self.nftables.active_bans + self.iptables.active_bans
    
    def get_total_rules(self) -> int:
        """Get the total number of rules across all backends.
        
        Returns:
            Sum of rules from nftables and iptables
        """
        return self.nftables.total_rules + self.iptables.total_rules
    
    def get_backend_stats(self, backend: str) -> Optional[BackendStats]:
        """Get statistics for a specific backend.
        
        Args:
            backend: Backend name ('nftables' or 'iptables')
        
        Returns:
            BackendStats for the backend, or None if unknown
        """
        if backend == "nftables":
            return self.nftables
        elif backend == "iptables":
            return self.iptables
        return None
    
    def get_connection_rate(self) -> float:
        """Calculate the ratio of established to total connections.
        
        Returns:
            Ratio between 0.0 and 1.0, or 0.0 if no connections
        """
        if self.total_connections == 0:
            return 0.0
        return self.established_connections / self.total_connections
    
    def get_jail_utilization(self) -> float:
        """Calculate the ratio of active jails to total jails.
        
        Returns:
            Ratio between 0.0 and 1.0, or 0.0 if no jails
        """
        if self.total_jails == 0:
            return 0.0
        return self.active_jails / self.total_jails
    
    def is_healthy(self) -> bool:
        """Check if the firewall is in a healthy state.
        
        A firewall is considered healthy if:
        - It has at least one rule configured
        - At least one jail is active (if jails exist)
        - Connection count is reasonable (< 1000)
        
        Returns:
            True if the firewall appears healthy
        """
        if self.total_rules == 0:
            return False
        
        if self.total_jails > 0 and self.active_jails == 0:
            return False
        
        if self.total_connections > 1000:
            return False
        
        return True
    
    def get_summary(self) -> dict[str, any]:
        """Get a summary of all monitoring statistics.
        
        Returns:
            Dictionary with key metrics
        """
        return {
            "timestamp": self.timestamp.isoformat(),
            "total_bans": self.total_bans,
            "total_rules": self.total_rules,
            "total_jails": self.total_jails,
            "active_jails": self.active_jails,
            "total_connections": self.total_connections,
            "established_connections": self.established_connections,
            "new_connections": self.new_connections,
            "nftables": self.nftables.get_summary(),
            "iptables": self.iptables.get_summary(),
            "is_healthy": self.is_healthy(),
        }
    
    def add_bans_per_minute(self, value: float, timestamp: Optional[datetime] = None) -> None:
        """Add a data point to the bans-per-minute time series.
        
        Args:
            value: Number of bans in the last minute
            timestamp: Timestamp for the data point (default: now)
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        self.bans_per_minute.append(TimeSeriesPoint(
            timestamp=timestamp,
            value=value,
            label="bans_per_minute"
        ))
        
        # Keep only the last 60 points (1 hour of data)
        if len(self.bans_per_minute) > 60:
            self.bans_per_minute = self.bans_per_minute[-60:]
    
    def add_connections_per_minute(self, value: float, timestamp: Optional[datetime] = None) -> None:
        """Add a data point to the connections-per-minute time series.
        
        Args:
            value: Number of connections in the last minute
            timestamp: Timestamp for the data point (default: now)
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        self.connections_per_minute.append(TimeSeriesPoint(
            timestamp=timestamp,
            value=value,
            label="connections_per_minute"
        ))
        
        # Keep only the last 60 points (1 hour of data)
        if len(self.connections_per_minute) > 60:
            self.connections_per_minute = self.connections_per_minute[-60:]
    
    def get_recent_bans_trend(self, minutes: int = 10) -> list[TimeSeriesPoint]:
        """Get the bans-per-minute trend for the last N minutes.
        
        Args:
            minutes: Number of minutes to look back (default: 10)
        
        Returns:
            List of TimeSeriesPoint objects
        """
        now = datetime.now()
        cutoff = now.timestamp() - (minutes * 60)
        
        return [
            point for point in self.bans_per_minute
            if point.timestamp.timestamp() >= cutoff
        ]
    
    def get_recent_connections_trend(self, minutes: int = 10) -> list[TimeSeriesPoint]:
        """Get the connections-per-minute trend for the last N minutes.
        
        Args:
            minutes: Number of minutes to look back (default: 10)
        
        Returns:
            List of TimeSeriesPoint objects
        """
        now = datetime.now()
        cutoff = now.timestamp() - (minutes * 60)
        
        return [
            point for point in self.connections_per_minute
            if point.timestamp.timestamp() >= cutoff
        ]


def merge_backend_stats(
    stats_list: list[BackendStats],
) -> BackendStats:
    """Merge multiple backend stats into one.
    
    Args:
        stats_list: List of BackendStats to merge
    
    Returns:
        Single BackendStats with aggregated values
    """
    if not stats_list:
        return BackendStats(backend="unknown")
    
    merged = BackendStats(backend=stats_list[0].backend)
    
    for stats in stats_list:
        merged.active_bans += stats.active_bans
        merged.total_rules += stats.total_rules
        merged.accept_rules += stats.accept_rules
        merged.drop_rules += stats.drop_rules
        merged.reject_rules += stats.reject_rules
        merged.log_rules += stats.log_rules
    
    return merged


def merge_monitoring_stats(
    stats_list: list[MonitoringStats],
) -> MonitoringStats:
    """Merge multiple monitoring stats into one.
    
    Args:
        stats_list: List of MonitoringStats to merge
    
    Returns:
        Single MonitoringStats with aggregated values
    """
    if not stats_list:
        return MonitoringStats()
    
    merged = MonitoringStats()
    
    for stats in stats_list:
        merged.total_bans += stats.total_bans
        merged.total_rules += stats.total_rules
        merged.total_jails += stats.total_jails
        merged.active_jails += stats.active_jails
        merged.total_connections += stats.total_connections
        merged.established_connections += stats.established_connections
        merged.new_connections += stats.new_connections
        
        # Merge backend stats
        merged.nftables = merge_backend_stats([merged.nftables, stats.nftables])
        merged.iptables = merge_backend_stats([merged.iptables, stats.iptables])
        
        # Keep the most recent timestamp
        if stats.timestamp > merged.timestamp:
            merged.timestamp = stats.timestamp
    
    return merged

# <-- INFO DEV ---------------------------------------------------------
# Rôle
# - Définit les modèles de statistiques agrégées pour le monitoring : statistiques globales du firewall, statistiques par backend, points de série temporelle pour les graphiques. Ce module ne collecte aucune donnée — il structure les métriques calculées par service.py.
# Pourquoi dans domain/ (charte) :
# - C'est une règle métier : comment structurer les statistiques de monitoring
# - Aucune dépendance externe (juste dataclasses, datetime, typing)
# - Testable en mémoire pure
# - Utilisé par domain/monitoring/service.py pour agréger les métriques
# Ce qu'il ne contient PAS (règles projet) :
# ❌ Pas d'import depuis infrastructure/ (pas de collecte système)
# ❌ Pas d'import depuis interfaces/ (pas de rendu graphique)
# ❌ Pas d'import depuis application/ (pas de cas d'usage)
# ❌ Pas de subprocess, open(), sqlite3 — aucun I/O
# Points clés
# - BackendStats : statistiques par backend (bans, règles par action, distribution)
# - TimeSeriesPoint : point de série temporelle pour les graphiques (timestamp, value, label)
# - MonitoringStats : statistiques globales agrégeant tout (bans, règles, jails, connexions, compteurs, séries temporelles)
# - Méthodes utilitaires :
#   - get_total_active_bans(), get_total_rules() : totaux globaux
#   - get_connection_rate(), get_jail_utilization() : ratios
#   - is_healthy() : vérification de l'état de santé
#   - add_bans_per_minute(), add_connections_per_minute() : ajout de points de série temporelle
#   - get_recent_bans_trend(), get_recent_connections_trend() : tendances récentes
#   - Fonctions de merge : merge_backend_stats(), merge_monitoring_stats()
#   - Aucune dépendance externe : utilise uniquement dataclasses, datetime, typing
#   - Aucun I/O : ne collecte aucune donnée système
# Comment il sera utilisé (aperçu)
# - domain/monitoring/service.py construira des MonitoringStats à partir des données collectées
# - application/queries/monitoring_status.py retournera MonitoringStats pour le dashboard
# - interfaces/cli/renderers/monitoring_live.py utilisera les séries temporelles pour les graphiques
# - infrastructure/backends/nftables/adapter.py alimentera les BackendStats
#---------------------------------------------------------------------->
