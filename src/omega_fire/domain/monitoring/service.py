# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Monitoring domain service.

Orchestrates business operations for system monitoring.
This service computes metrics about the firewall state: bans, rules,
jails, connections, etc. It does NOT collect data from the system —
that is the responsibility of infrastructure/ via ports.
"""
from datetime import datetime
from typing import Optional
from omega_fire.domain.ip_blacklist.models import BanEntry, BanStatus
from omega_fire.domain.rules.models import FirewallRule, RuleAction
from omega_fire.domain.fail2ban.models import Jail, JailStatus
from omega_fire.domain.monitoring.conntrack import Connection, ConnectionState
from omega_fire.domain.monitoring.counters import (
    PacketCounter,
    BanCounter,
    RuleCounter,
    CounterSet,
)
from omega_fire.domain.monitoring.stats import (
    MonitoringStats,
    BackendStats,
    TimeSeriesPoint,
)


class MonitoringService:
    """Domain service for monitoring operations.
    
    This service orchestrates business logic for computing monitoring
    metrics. It aggregates data from various sources (bans, rules, jails,
    connections) and produces unified statistics.
    """
    
    def compute_global_stats(
        self,
        banned_ips: list[BanEntry],
        rules: list[FirewallRule],
        jails: list[Jail],
        connections: list[Connection],
        counters: CounterSet,
    ) -> MonitoringStats:
        """Compute comprehensive monitoring statistics.
        
        Args:
            banned_ips: List of banned IP entries
            rules: List of firewall rules
            jails: List of fail2ban jails
            connections: List of tracked connections
            counters: Packet and event counters
        
        Returns:
            MonitoringStats with all aggregated metrics
        """
        # Backend stats
        nftables_stats = self._compute_backend_stats(
            banned_ips, rules, jails, connections, "nftables"
        )
        iptables_stats = self._compute_backend_stats(
            banned_ips, rules, jails, connections, "iptables"
        )
        
        # Overall stats
        total_bans = len([b for b in banned_ips if b.status == BanStatus.ACTIVE])
        total_rules = len(rules)
        total_jails = len(jails)
        active_jails = len([j for j in jails if j.status == JailStatus.ACTIVE])
        total_connections = len(connections)
        
        # Connection states
        established = len([c for c in connections if c.state == ConnectionState.ESTABLISHED])
        new_connections = len([c for c in connections if c.state == ConnectionState.NEW])
        
        # Build stats
        stats = MonitoringStats(
            timestamp=datetime.now(),
            total_bans=total_bans,
            total_rules=total_rules,
            total_jails=total_jails,
            active_jails=active_jails,
            total_connections=total_connections,
            established_connections=established,
            new_connections=new_connections,
            nftables=nftables_stats,
            iptables=iptables_stats,
            counters=counters,
        )
        
        return stats
    
    def _compute_backend_stats(
        self,
        banned_ips: list[BanEntry],
        rules: list[FirewallRule],
        jails: list[Jail],
        connections: list[Connection],
        backend: str,
    ) -> BackendStats:
        """Compute statistics for a specific backend.
        
        Args:
            banned_ips: List of banned IP entries
            rules: List of firewall rules
            jails: List of fail2ban jails
            connections: List of tracked connections
            backend: Backend name ('nftables' or 'iptables')
        
        Returns:
            BackendStats for the specified backend
        """
        # Filter by backend
        backend_bans = [b for b in banned_ips if b.backend == backend and b.status == BanStatus.ACTIVE]
        backend_rules = [r for r in rules if r.backend == backend]
        
        # Count actions
        accept_rules = len([r for r in backend_rules if r.action == RuleAction.ACCEPT])
        drop_rules = len([r for r in backend_rules if r.action == RuleAction.DROP])
        reject_rules = len([r for r in backend_rules if r.action == RuleAction.REJECT])
        
        return BackendStats(
            backend=backend,
            active_bans=len(backend_bans),
            total_rules=len(backend_rules),
            accept_rules=accept_rules,
            drop_rules=drop_rules,
            reject_rules=reject_rules,
        )
    
    def compute_health_score(
        self,
        stats: MonitoringStats,
    ) -> int:
        """Compute a health score for the firewall (0-100).
        
        The score is based on:
        - Number of active bans (too many = suspicious)
        - Number of rules (too few = insecure)
        - Number of active jails (should be > 0)
        - Connection count (too many = possible attack)
        
        Args:
            stats: Current monitoring statistics
        
        Returns:
            Health score from 0 (critical) to 100 (healthy)
        """
        score = 100
        
        # Penalize if no rules
        if stats.total_rules == 0:
            score -= 50
        
        # Penalize if no active jails
        if stats.active_jails == 0:
            score -= 20
        
        # Penalize if too many bans (possible attack)
        if stats.total_bans > 100:
            score -= 20
        elif stats.total_bans > 50:
            score -= 10
        
        # Penalize if too many connections (possible DDoS)
        if stats.total_connections > 1000:
            score -= 20
        elif stats.total_connections > 500:
            score -= 10
        
        # Ensure score is in range [0, 100]
        return max(0, min(100, score))
    
    def get_top_banned_ips(
        self,
        banned_ips: list[BanEntry],
        n: int = 10,
    ) -> list[tuple[str, int]]:
        """Get the top N most frequently banned IPs.
        
        Args:
            banned_ips: List of banned IP entries (may contain duplicates)
            n: Number of top IPs to return
        
        Returns:
            List of (ip, count) tuples, sorted by count descending
        """
        # Count occurrences per IP
        ip_counts: dict[str, int] = {}
        for ban in banned_ips:
            ip_counts[ban.ip] = ip_counts.get(ban.ip, 0) + 1
        
        # Sort by count descending
        sorted_ips = sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)
        
        return sorted_ips[:n]
    
    def get_connection_summary(
        self,
        connections: list[Connection],
    ) -> dict[str, int]:
        """Get a summary of connections by state.
        
        Args:
            connections: List of tracked connections
        
        Returns:
            Dictionary mapping state name to count
        """
        summary: dict[str, int] = {}
        
        for conn in connections:
            state_name = conn.state.value
            summary[state_name] = summary.get(state_name, 0) + 1
        
        return summary
    
    def detect_anomalies(
        self,
        stats: MonitoringStats,
        historical_stats: list[MonitoringStats],
    ) -> list[str]:
        """Detect anomalies by comparing current stats with historical data.
        
        Args:
            stats: Current monitoring statistics
            historical_stats: List of previous monitoring statistics
        
        Returns:
            List of anomaly descriptions (empty if no anomalies)
        """
        anomalies = []
        
        if not historical_stats:
            return anomalies
        
        # Calculate averages from historical data
        avg_bans = sum(s.total_bans for s in historical_stats) / len(historical_stats)
        avg_connections = sum(s.total_connections for s in historical_stats) / len(historical_stats)
        
        # Detect sudden spike in bans
        if stats.total_bans > avg_bans * 2 and avg_bans > 0:
            anomalies.append(
                f"Sudden spike in bans: {stats.total_bans} (avg: {avg_bans:.0f})"
            )
        
        # Detect sudden spike in connections
        if stats.total_connections > avg_connections * 2 and avg_connections > 0:
            anomalies.append(
                f"Sudden spike in connections: {stats.total_connections} (avg: {avg_connections:.0f})"
            )
        
        # Detect if all jails are disabled
        if stats.active_jails == 0 and stats.total_jails > 0:
            anomalies.append("All fail2ban jails are disabled")
        
        return anomalies

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Orchestration métier du monitoring système. Ce service calcule des métriques globales sur l'état du firewall : nombre de bans actifs, règles configurées, jails fail2ban, connexions trackées, etc. Il ne fait aucun appel système — les données réelles viennent des ports (infrastructure).
# Pourquoi dans domain/ (charte) :
# - C'est une règle métier : comment agréger et calculer les métriques de monitoring
# - Aucune dépendance externe (opère sur les modèles du domaine)
# - Testable en mémoire pure
# - Utilisé par application/queries/monitoring_status.py
# Ce qu'il ne contient PAS (règles projet) :
# ❌ Pas d'import depuis infrastructure/ (pas d'appel système, pas de lecture fichier)
# ❌ Pas d'import depuis interfaces/ (pas de rendu)
# ❌ Pas d'import depuis application/ (pas de cas d'usage)
# ❌ Pas de subprocess, os.system, open() — aucun I/O
# Points clés :
# - Orchestration métier : agrège des données de plusieurs sources (bans, rules, jails, connections)
# - compute_global_stats() : calcule des statistiques globales avec breakdown par backend
# - compute_health_score() : calcule un score de santé 0-100 basé sur plusieurs critères
# - get_top_banned_ips() : retourne les IPs les plus fréquemment bannies
# - get_connection_summary() : résumé des connexions par état
# - detect_anomalies() : détecte des anomalies en comparant avec l'historique
# - Aucune dépendance externe : opère uniquement sur les modèles du domaine
# - Aucun I/O : ne lit ni n'écrit aucun fichier, n'appelle aucun système
# Comment il sera utilisé (aperçu) :
# - application/queries/monitoring_status.py appellera compute_global_stats() pour le dashboard
# - application/queries/health_check.py appellera compute_health_score() pour vérifier la santé
# - application/queries/anomaly_detection.py appellera detect_anomalies() pour alerter
# - interfaces/cli/actions.py affichera les métriques via les renderers
#---------------------------------------------------------------------->
