# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
# Porte d'omega-log (domain/logs/analytics.py) le 2026-11-09 (OMEGA-FIRE_PLAN_LOGS_NIVEAU_SERV_LOG.md) : garder identique a la source.
"""Logs domain analytics.

Pure domain logic for analyzing log entries. This module computes
statistics, rankings, and aggregations from LogEntry objects in memory —
it does NOT read files. Porte verbatim depuis omega-fire
(domain/logs/analytics.py)."""
from collections import Counter, defaultdict
from datetime import datetime

from omega_fire.domain.log_stats.models import (
    HourlyStats,
    LogEntry,
    LogLevel,
    LogSource,
    LogStats,
    TopIP,
    TrafficStats,
)


def compute_top_ips(
    entries: list[LogEntry],
    n: int = 10,
    min_count: int = 1,
) -> list[TopIP]:
    """Compute the Top N IP addresses by occurrence count."""
    ip_counts: dict[str, int] = defaultdict(int)
    ip_first_seen: dict[str, datetime] = {}
    ip_last_seen: dict[str, datetime] = {}
    ip_services: dict[str, set[str]] = defaultdict(set)
    ip_http_errors: dict[str, int] = defaultdict(int)

    for entry in entries:
        if not entry.has_ip():
            continue

        ip = entry.ip
        assert ip is not None  # garanti par has_ip() (comme omega-serv)
        ip_counts[ip] += 1

        if ip not in ip_first_seen or entry.timestamp < ip_first_seen[ip]:
            ip_first_seen[ip] = entry.timestamp
        if ip not in ip_last_seen or entry.timestamp > ip_last_seen[ip]:
            ip_last_seen[ip] = entry.timestamp

        if entry.service:
            ip_services[ip].add(entry.service)

        if entry.is_http_error():
            ip_http_errors[ip] += 1

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

    top_ips.sort(key=lambda x: (-x.count, x.ip))

    return top_ips[:n]


def compute_hourly_stats(entries: list[LogEntry]) -> list[HourlyStats]:
    """Compute statistics per hour (0-23)."""
    hourly: dict[int, HourlyStats] = {hour: HourlyStats(hour=hour) for hour in range(24)}

    for entry in entries:
        hour = entry.timestamp.hour
        hourly[hour].count += 1

        if entry.is_error():
            hourly[hour].error_count += 1

    return [hourly[hour] for hour in range(24)]


def compute_level_distribution(entries: list[LogEntry]) -> dict[str, int]:
    """Compute the distribution of log levels."""
    counts: dict[str, int] = defaultdict(int)
    for entry in entries:
        counts[entry.level.value] += 1
    return dict(counts)


def compute_source_distribution(entries: list[LogEntry]) -> dict[str, int]:
    """Compute the distribution of log sources."""
    counts: dict[str, int] = defaultdict(int)
    for entry in entries:
        counts[entry.source.value] += 1
    return dict(counts)


def compute_time_range(entries: list[LogEntry]) -> tuple[datetime | None, datetime | None]:
    """Compute the time range (first and last entry timestamps)."""
    if not entries:
        return None, None

    timestamps = [e.timestamp for e in entries]
    return min(timestamps), max(timestamps)


def compute_stats(
    entries: list[LogEntry],
    total_lines: int = 0,
    log_path: str | None = None,
    top_n: int = 10,
) -> LogStats:
    """Compute comprehensive statistics for a list of log entries."""
    unique_ips = len({e.ip for e in entries if e.has_ip()})
    total_ips = len([e for e in entries if e.has_ip()])

    level_counts = compute_level_distribution(entries)
    source_counts = compute_source_distribution(entries)

    hourly_stats = compute_hourly_stats(entries)

    top_ips = compute_top_ips(entries, n=top_n)

    first_entry, last_entry = compute_time_range(entries)

    return LogStats(
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


def filter_entries_by_ip(entries: list[LogEntry], ip: str) -> list[LogEntry]:
    """Filter entries by IP address."""
    return [e for e in entries if e.matches_ip(ip)]


def filter_entries_by_level(entries: list[LogEntry], level: LogLevel) -> list[LogEntry]:
    """Filter entries by log level."""
    return [e for e in entries if e.level == level]


def filter_entries_by_source(entries: list[LogEntry], source: LogSource) -> list[LogEntry]:
    """Filter entries by log source."""
    return [e for e in entries if e.source == source]


def filter_entries_by_time_range(
    entries: list[LogEntry],
    start: datetime | None = None,
    end: datetime | None = None,
) -> list[LogEntry]:
    """Filter entries by time range."""
    filtered = entries

    if start:
        filtered = [e for e in filtered if e.timestamp >= start]
    if end:
        filtered = [e for e in filtered if e.timestamp <= end]

    return filtered


def filter_error_entries(entries: list[LogEntry]) -> list[LogEntry]:
    """Filter to keep only error and critical entries."""
    return [e for e in entries if e.is_error()]


def get_entries_for_ip(entries: list[LogEntry], ip: str) -> list[LogEntry]:
    """Get all entries for a specific IP (alias for filter_entries_by_ip)."""
    return filter_entries_by_ip(entries, ip)


TRAFFIC_TOP_SIZE = 5
"""Lignes des tops du viewer Simple (meme valeur qu'omega-serv, 2026-11-06)."""


def compute_traffic_stats(entries: list[LogEntry]) -> TrafficStats:
    """Barre de statut du viewer Simple. Debits rapportes a la duree couverte par les lignes (horodatages
    du log), jamais au temps passe devant l'ecran : un tampon charge d'un coup a l'ouverture donne le
    meme debit que si on l'avait regarde arriver."""
    stats = TrafficStats(total=len(entries))
    if not entries:
        return stats
    statuses = [e.http_status for e in entries if e.http_status is not None]
    stats.http_total = len(statuses)
    stats.status_2xx = sum(1 for s in statuses if 200 <= s < 300)
    stats.status_3xx = sum(1 for s in statuses if 300 <= s < 400)
    stats.status_4xx = sum(1 for s in statuses if 400 <= s < 500)
    stats.status_5xx = sum(1 for s in statuses if 500 <= s < 600)

    first, last = compute_time_range(entries)
    if first is not None and last is not None:
        span = (last - first).total_seconds()
        if span >= 1:
            stats.span_seconds = span
            stats.requests_per_second = len(entries) / span

    latencies = [e.latency_ms for e in entries if e.latency_ms is not None]
    if latencies:
        stats.avg_latency_ms = sum(latencies) / len(latencies)
    sizes = [e.bytes_sent for e in entries if e.bytes_sent is not None]
    if sizes:
        stats.bytes_total = sum(sizes)
        stats.avg_size = stats.bytes_total / len(sizes)
        if stats.span_seconds is not None:
            stats.bytes_per_second = stats.bytes_total / stats.span_seconds

    stats.status_403 = sum(1 for s in statuses if s == 403)
    stats.status_429 = sum(1 for s in statuses if s == 429)
    stats.top_ips = [(t.ip, t.count) for t in compute_top_ips(entries, n=TRAFFIC_TOP_SIZE)]
    paths = [(e.http_path.split("?", 1)[0], e.http_status) for e in entries if e.http_path]
    stats.top_paths = Counter(path for path, _status in paths).most_common(TRAFFIC_TOP_SIZE)
    stats.top_not_found = Counter(path for path, status in paths if status == 404).most_common(TRAFFIC_TOP_SIZE)

    top = compute_top_ips(entries, n=1)
    stats.unique_ips = len({e.ip for e in entries if e.has_ip()})
    if top:
        stats.top_ip, stats.top_ip_count = top[0].ip, top[0].count

    if stats.http_total:
        stats.error_rate = (stats.status_4xx + stats.status_5xx) / stats.http_total * 100
    else:
        stats.error_rate = sum(1 for e in entries if e.is_error()) / len(entries) * 100
    return stats
