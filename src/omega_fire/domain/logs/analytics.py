# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Logs domain analytics.

Pure domain logic for analyzing log entries.
This module computes statistics, rankings, and aggregations
from LogEntry objects in memory — it does NOT read files.
"""
from collections import defaultdict
from datetime import datetime
from typing import Optional
from omega_fire.domain.logs.models import (
    LogEntry,
    LogLevel,
    LogSource,
    LogStats,
    TopIP,
    HourlyStats,
)


def compute_top_ips(
    entries: list[LogEntry],
    n: int = 10,
    min_count: int = 1,
) -> list[TopIP]:
    """Compute the Top N IP addresses by occurrence count.
    
    Args:
        entries: List of log entries to analyze
        n: Number of top IPs to return (default: 10)
        min_count: Minimum occurrence count to include (default: 1)
    
    Returns:
        List of TopIP objects, sorted by count descending
    """
    # Count occurrences per IP
    ip_counts: dict[str, int] = defaultdict(int)
    ip_first_seen: dict[str, datetime] = {}
    ip_last_seen: dict[str, datetime] = {}
    ip_services: dict[str, set[str]] = defaultdict(set)
    ip_http_errors: dict[str, int] = defaultdict(int)
    
    for entry in entries:
        if not entry.has_ip():
            continue
        
        ip = entry.ip
        ip_counts[ip] += 1
        
        # Track first/last seen
        if ip not in ip_first_seen or entry.timestamp < ip_first_seen[ip]:
            ip_first_seen[ip] = entry.timestamp
        if ip not in ip_last_seen or entry.timestamp > ip_last_seen[ip]:
            ip_last_seen[ip] = entry.timestamp
        
        # Track services
        if entry.service:
            ip_services[ip].add(entry.service)
        
        # Track HTTP errors
        if entry.is_http_error():
            ip_http_errors[ip] += 1
    
    # Build TopIP objects
    top_ips = []
    for ip, count in ip_counts.items():
        if count < min_count:
            continue
        
        top_ips.append(TopIP(
            ip=ip,
            count=count,
            first_seen=ip_first_seen.get(ip),
            last_seen=ip_last_seen.get(ip),
            services=sorted(ip_services.get(ip, [])),
            http_errors=ip_http_errors.get(ip, 0),
        ))
    
    # Sort by count descending, then by IP for stability
    top_ips.sort(key=lambda x: (-x.count, x.ip))
    
    return top_ips[:n]


def compute_hourly_stats(entries: list[LogEntry]) -> list[HourlyStats]:
    """Compute statistics per hour (0-23).
    
    Args:
        entries: List of log entries to analyze
    
    Returns:
        List of HourlyStats for each hour (0-23), sorted by hour
    """
    # Initialize all hours
    hourly: dict[int, HourlyStats] = {
        hour: HourlyStats(hour=hour) for hour in range(24)
    }
    
    # Count entries per hour
    for entry in entries:
        hour = entry.timestamp.hour
        hourly[hour].count += 1
        
        if entry.is_error():
            hourly[hour].error_count += 1
    
    # Return sorted by hour
    return [hourly[hour] for hour in range(24)]


def compute_level_distribution(entries: list[LogEntry]) -> dict[str, int]:
    """Compute the distribution of log levels.
    
    Args:
        entries: List of log entries to analyze
    
    Returns:
        Dictionary mapping level name to count
    """
    counts: dict[str, int] = defaultdict(int)
    
    for entry in entries:
        counts[entry.level.value] += 1
    
    return dict(counts)


def compute_source_distribution(entries: list[LogEntry]) -> dict[str, int]:
    """Compute the distribution of log sources.
    
    Args:
        entries: List of log entries to analyze
    
    Returns:
        Dictionary mapping source name to count
    """
    counts: dict[str, int] = defaultdict(int)
    
    for entry in entries:
        counts[entry.source.value] += 1
    
    return dict(counts)


def compute_time_range(entries: list[LogEntry]) -> tuple[Optional[datetime], Optional[datetime]]:
    """Compute the time range (first and last entry timestamps).
    
    Args:
        entries: List of log entries to analyze
    
    Returns:
        Tuple of (first_entry, last_entry), or (None, None) if empty
    """
    if not entries:
        return None, None
    
    timestamps = [e.timestamp for e in entries]
    return min(timestamps), max(timestamps)


def compute_stats(
    entries: list[LogEntry],
    total_lines: int = 0,
    log_path: Optional[str] = None,
    top_n: int = 10,
) -> LogStats:
    """Compute comprehensive statistics for a list of log entries.
    
    This is the main entry point for log analysis. It aggregates
    all statistics into a single LogStats object.
    
    Args:
        entries: List of log entries to analyze
        total_lines: Total number of lines in the source file (including unparsed)
        log_path: Path to the log file (for context)
        top_n: Number of top IPs to include (default: 10)
    
    Returns:
        LogStats object with all computed statistics
    """
    # Count unique IPs
    unique_ips = len({e.ip for e in entries if e.has_ip()})
    total_ips = len([e for e in entries if e.has_ip()])
    
    # Compute distributions
    level_counts = compute_level_distribution(entries)
    source_counts = compute_source_distribution(entries)
    
    # Compute hourly stats
    hourly_stats = compute_hourly_stats(entries)
    
    # Compute top IPs
    top_ips = compute_top_ips(entries, n=top_n)
    
    # Compute time range
    first_entry, last_entry = compute_time_range(entries)
    
    # Build LogStats
    stats = LogStats(
        log_path=log_path,
        total_lines=total_lines if total_lines > 0 else len(entries),
        parsed_lines=len(entries),
        failed_lines=total_lines - len(entries) if total_lines > 0 else 0,
        unique_ips=unique_ips,
        total_ips=total_ips,
        level_counts=level_counts,
        hourly_stats=hourly_stats,
        top_ips=top_ips,
        first_entry=first_entry,
        last_entry=last_entry,
        source_counts=source_counts,
    )
    
    return stats


def filter_entries_by_ip(entries: list[LogEntry], ip: str) -> list[LogEntry]:
    """Filter entries by IP address.
    
    Args:
        entries: List of log entries to filter
        ip: IP address to match
    
    Returns:
        List of entries matching the IP
    """
    return [e for e in entries if e.matches_ip(ip)]


def filter_entries_by_level(entries: list[LogEntry], level: LogLevel) -> list[LogEntry]:
    """Filter entries by log level.
    
    Args:
        entries: List of log entries to filter
        level: Log level to match
    
    Returns:
        List of entries with the specified level
    """
    return [e for e in entries if e.level == level]


def filter_entries_by_source(entries: list[LogEntry], source: LogSource) -> list[LogEntry]:
    """Filter entries by log source.
    
    Args:
        entries: List of log entries to filter
        source: Log source to match
    
    Returns:
        List of entries from the specified source
    """
    return [e for e in entries if e.source == source]


def filter_entries_by_time_range(
    entries: list[LogEntry],
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
) -> list[LogEntry]:
    """Filter entries by time range.
    
    Args:
        entries: List of log entries to filter
        start: Start time (inclusive). None = no lower bound
        end: End time (inclusive). None = no upper bound
    
    Returns:
        List of entries within the time range
    """
    filtered = entries
    
    if start:
        filtered = [e for e in filtered if e.timestamp >= start]
    if end:
        filtered = [e for e in filtered if e.timestamp <= end]
    
    return filtered


def filter_error_entries(entries: list[LogEntry]) -> list[LogEntry]:
    """Filter to keep only error and critical entries.
    
    Args:
        entries: List of log entries to filter
    
    Returns:
        List of error and critical entries
    """
    return [e for e in entries if e.is_error()]


def get_entries_for_ip(entries: list[LogEntry], ip: str) -> list[LogEntry]:
    """Get all entries for a specific IP (alias for filter_entries_by_ip).
    
    Args:
        entries: List of log entries
        ip: IP address
    
    Returns:
        List of entries matching the IP
    """
    return filter_entries_by_ip(entries, ip)

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit la logique d'analyse des logs : calcul de Top N IPs, statistiques horaires, agrégation par niveau/source, taux d'erreur, etc. Ce module opère uniquement sur des LogEntry en mémoire — il ne lit aucun fichier.
# Pourquoi dans domain/ (charte) :
# - C'est une règle métier : comment analyser des logs, calculer des statistiques
# - Aucune dépendance externe (opère sur les modèles du domaine)
# - Fonctions pures : pas d'I/O, pas de lecture fichier
# - Testable avec des LogEntry construits manuellement
# Ce qu'il ne contient PAS (règles projet) :
# ❌ Pas d'import depuis infrastructure/ (pas de lecture fichier)
# ❌ Pas d'import depuis interfaces/ (pas de rendu)
# ❌ Pas d'import depuis application/ (pas de cas d'usage)
# ❌ Pas de open(), Path.read_text() — aucun I/O
# Points clés :
# - compute_top_ips() : calcule le Top N IPs avec count, first/last seen, services, erreurs HTTP
# - compute_hourly_stats() : calcule les statistiques par heure (0-23)
# - compute_level_distribution() : distribution par niveau de log
# - compute_source_distribution() : distribution par source de log
# - compute_time_range() : première et dernière entrée
# - compute_stats() : point d'entrée principal qui agrège toutes les statistiques dans un LogStats
# - Fonctions de filtrage : filter_entries_by_ip(), filter_entries_by_level(), filter_entries_by_source(), filter_entries_by_time_range(), filter_error_entries()
# - Aucune dépendance externe : opère uniquement sur les modèles du domaine
# - Testable en mémoire : peut être testé avec des LogEntry construits manuellement
# Comment il sera utilisé (aperçu) :
# - domain/logs/service.py appellera compute_stats() pour analyser un fichier de log
# - application/queries/log_top_ips.py utilisera compute_top_ips() pour afficher le classement
# - application/queries/dashboard_summary.py utilisera compute_stats() pour le tableau de bord
# - interfaces/cli/renderers/logs_live.py affichera les statistiques en temps réel
#---------------------------------------------------------------------->
