# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
# Porte d'omega-log (domain/logs/models.py) le 2026-11-09 (OMEGA-FIRE_PLAN_LOGS_NIVEAU_SERV_LOG.md) : garder identique a la source.
"""Logs domain models.

Pure domain logic for log entries and statistics. No external dependencies.
This module defines what a log entry IS, not how it is read from disk
or parsed from raw text.

Porte verbatim depuis omega-fire (domain/logs/models.py) — voir
plan_omega_log.md §2/§6 : module generique, aucune dependance externe,
deja confirme reutilisable tel quel sans adaptation."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class LogSource(Enum):
    """Type of log source."""
    AUTH = "auth"           # /var/log/auth.log (SSH, sudo, etc.)
    ACCESS = "access"       # Apache/Nginx access.log
    SYSLOG = "syslog"       # /var/log/syslog
    KERN = "kern"           # Kernel messages
    FAIL2BAN = "fail2ban"   # Fail2ban log
    CUSTOM = "custom"       # Custom log source


class LogLevel(Enum):
    """Severity level of a log entry."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class LogEntry:
    """A single parsed log entry.

    Pure domain model. Contains only the structured data extracted
    from a raw log line. Does not know how to read or parse files.
    """
    timestamp: datetime
    source: LogSource
    level: LogLevel = LogLevel.INFO
    ip: str | None = None
    message: str = ""
    raw_line: str = ""
    line_number: int = 0
    log_path: str | None = None

    user: str | None = None
    port: int | None = None
    protocol: str | None = None
    http_method: str | None = None
    http_path: str | None = None
    http_status: int | None = None
    latency_ms: int | None = None
    """Duree de traitement de la requete (quand le format du log la
    fournit — ex. "%D"/"%T" Apache, champ "duration"/"latency" JSON).
    AJOUTE 2026-10-04 (retour utilisateur : reprendre la colonne
    "timeout" simplifiee d'omega-fire pour le Viewer 1) — absent de la
    version source omega-fire telle quelle (champ equivalent nomme
    response_time_ms, jamais porte sur LogEntry lui-meme la-bas, calcule
    a la volee par le _LogProvider specifique HTTP)."""
    bytes_sent: int | None = None
    """Taille de la reponse (champ %b du format Combined/Common) - None si "-" ou format sans taille,
    jamais une valeur estimee (porte depuis omega-serv, viewer Simple 2026-11-02)."""
    service: str | None = None

    def has_ip(self) -> bool:
        """Check if this entry contains an IP address."""
        return self.ip is not None and self.ip != ""

    def is_error(self) -> bool:
        """Check if this entry is an error or critical."""
        return self.level in (LogLevel.ERROR, LogLevel.CRITICAL)

    def is_warning_or_above(self) -> bool:
        """Check if this entry is warning, error, or critical."""
        return self.level in (LogLevel.WARNING, LogLevel.ERROR, LogLevel.CRITICAL)

    def is_http_error(self) -> bool:
        """Check if this entry represents an HTTP error (4xx or 5xx)."""
        if self.http_status is None:
            return False
        return self.http_status >= 400

    def matches_ip(self, ip: str) -> bool:
        """Check if this entry matches a specific IP."""
        return self.ip == ip


@dataclass
class TopIP:
    """An entry in the Top N IP ranking."""
    ip: str
    count: int
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    services: list[str] = field(default_factory=list)
    http_errors: int = 0

    def percentage(self, total: int) -> float:
        """Calculate the percentage of this IP relative to total entries."""
        if total == 0:
            return 0.0
        return (self.count / total) * 100.0


@dataclass
class HourlyStats:
    """Statistics for a specific hour."""
    hour: int  # 0-23
    count: int = 0
    error_count: int = 0

    def error_rate(self) -> float:
        """Calculate the error rate for this hour."""
        if self.count == 0:
            return 0.0
        return (self.error_count / self.count) * 100.0


@dataclass
class LogStats:
    """Aggregated statistics for a log file or analysis."""
    log_path: str | None = None
    total_lines: int = 0
    parsed_lines: int = 0
    failed_lines: int = 0

    unique_ips: int = 0
    total_ips: int = 0

    level_counts: dict[str, int] = field(default_factory=dict)

    hourly_stats: list[HourlyStats] = field(default_factory=list)

    top_ips: list[TopIP] = field(default_factory=list)

    first_entry: datetime | None = None
    last_entry: datetime | None = None

    source_counts: dict[str, int] = field(default_factory=dict)

    def parse_rate(self) -> float:
        """Calculate the percentage of successfully parsed lines."""
        if self.total_lines == 0:
            return 0.0
        return (self.parsed_lines / self.total_lines) * 100.0

    def error_rate(self) -> float:
        """Calculate the overall error rate."""
        error_count = self.level_counts.get("error", 0) + self.level_counts.get("critical", 0)
        if self.parsed_lines == 0:
            return 0.0
        return (error_count / self.parsed_lines) * 100.0

    def get_level_count(self, level: LogLevel) -> int:
        """Get the count for a specific log level."""
        return self.level_counts.get(level.value, 0)

    def get_source_count(self, source: LogSource) -> int:
        """Get the count for a specific log source."""
        return self.source_counts.get(source.value, 0)

    def get_hourly_stats(self, hour: int) -> HourlyStats | None:
        """Get statistics for a specific hour (0-23)."""
        for stats in self.hourly_stats:
            if stats.hour == hour:
                return stats
        return None

    def time_span_hours(self) -> float:
        """Calculate the time span in hours between first and last entry."""
        if self.first_entry is None or self.last_entry is None:
            return 0.0
        delta = self.last_entry - self.first_entry
        return delta.total_seconds() / 3600.0


@dataclass
class LogAnalysis:
    """Result of a complete log analysis operation."""
    entries: list[LogEntry] = field(default_factory=list)
    stats: LogStats | None = None
    top_ips: list[TopIP] = field(default_factory=list)

    def count(self) -> int:
        """Return the number of log entries."""
        return len(self.entries)

    def get_entries_by_ip(self, ip: str) -> list[LogEntry]:
        """Get all entries matching a specific IP."""
        return [e for e in self.entries if e.matches_ip(ip)]

    def get_entries_by_level(self, level: LogLevel) -> list[LogEntry]:
        """Get all entries with a specific log level."""
        return [e for e in self.entries if e.level == level]

    def get_entries_by_source(self, source: LogSource) -> list[LogEntry]:
        """Get all entries from a specific log source."""
        return [e for e in self.entries if e.source == source]

    def get_error_entries(self) -> list[LogEntry]:
        """Get all error and critical entries."""
        return [e for e in self.entries if e.is_error()]


@dataclass
class TrafficStats:
    """Barre d'etat du viewer Simple - IDENTIQUE a omega-serv (viewer de reference, 2026-11-02) :
    rendement, bande passante, statuts HTTP, clients, sante - calculee sur le tampon, UNIQUEMENT a partir
    de valeurs reellement lues dans le log (None sinon, jamais 350 octets ou 25 ms supposes)."""
    total: int = 0
    http_total: int = 0
    status_2xx: int = 0
    status_3xx: int = 0
    status_4xx: int = 0
    status_5xx: int = 0
    span_seconds: float | None = None
    requests_per_second: float | None = None
    avg_latency_ms: float | None = None
    bytes_total: int | None = None
    bytes_per_second: float | None = None
    avg_size: float | None = None
    unique_ips: int = 0
    top_ip: str | None = None
    top_ip_count: int = 0
    error_rate: float = 0.0
    """% de 4xx/5xx parmi les lignes HTTP ; a defaut, % de lignes de niveau erreur."""
    status_403: int = 0
    status_429: int = 0
    top_ips: list[tuple[str, int]] = field(default_factory=list)
    """Repris d'omega-serv (2026-11-06) : top 5 (IP, requetes), puis chemins (sans la partie `?...`) les plus
    demandes et ceux en 404 - vides si le log n'a pas de champs HTTP."""
    top_paths: list[tuple[str, int]] = field(default_factory=list)
    top_not_found: list[tuple[str, int]] = field(default_factory=list)
