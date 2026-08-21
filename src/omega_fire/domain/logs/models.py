# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Logs domain models.

Pure domain logic for log entries and statistics. No external dependencies.
This module defines what a log entry IS, not how it is read from disk
or parsed from raw text.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


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
    ip: Optional[str] = None
    message: str = ""
    raw_line: str = ""
    line_number: int = 0
    log_path: Optional[str] = None
    
    # Optional fields for specific log types
    user: Optional[str] = None          # For auth logs
    port: Optional[int] = None          # For network logs
    protocol: Optional[str] = None      # tcp/udp
    http_method: Optional[str] = None   # GET/POST/etc.
    http_path: Optional[str] = None     # URL path
    http_status: Optional[int] = None   # HTTP status code
    service: Optional[str] = None       # Service name (sshd, httpd, etc.)
    
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
    """An entry in the Top N IP ranking.
    
    Represents an IP address with its occurrence count and optional
    additional statistics.
    """
    ip: str
    count: int
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
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
    """Aggregated statistics for a log file or analysis.
    
    Contains summary data about a log file: total entries, IP counts,
    time distribution, error rates, etc.
    """
    log_path: Optional[str] = None
    total_lines: int = 0
    parsed_lines: int = 0
    failed_lines: int = 0
    
    # IP statistics
    unique_ips: int = 0
    total_ips: int = 0
    
    # Level distribution
    level_counts: dict[str, int] = field(default_factory=dict)
    
    # Time distribution
    hourly_stats: list[HourlyStats] = field(default_factory=list)
    
    # Top IPs (pre-computed for convenience)
    top_ips: list[TopIP] = field(default_factory=list)
    
    # Time range
    first_entry: Optional[datetime] = None
    last_entry: Optional[datetime] = None
    
    # Source distribution
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
    
    def get_hourly_stats(self, hour: int) -> Optional[HourlyStats]:
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
    """Result of a complete log analysis operation.
    
    Combines raw entries with computed statistics for a full analysis.
    """
    entries: list[LogEntry] = field(default_factory=list)
    stats: Optional[LogStats] = None
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
# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit les modèles métier pour les logs. Ce sont des dataclasses pures qui représentent une entrée de log parsée (LogEntry), des statistiques agrégées (LogStats), une entrée de classement Top N (TopIP), et les concepts associés (source de log, niveau de sévérité).
# Pourquoi dans domain/ (charte) :
# - C'est une règle métier : qu'est-ce qu'une entrée de log, comment la structurer, comment agréger des statistiques
# - Aucune dépendance externe (juste dataclasses, enum, datetime, typing)
# - Testable sans aucun accès au système de fichiers
# - Utilisé par domain/logs/parser.py, analytics.py, service.py
# Ce qu'il ne contient PAS (règles projet) :
# ❌ Pas d'import depuis infrastructure/ (pas de lecture fichier)
# ❌ Pas d'import depuis interfaces/ (pas de rendu)
# ❌ Pas d'import depuis application/ (pas de cas d'usage)
# ❌ Pas de regex (ça va dans parser.py)
# ❌  Pas de logique d'extraction (juste la structure de données)
#Points clés :
# - LogEntry : modèle pur d'une entrée de log parsée, avec champs optionnels pour différents types de logs (auth, HTTP, syslog)
# - TopIP : entrée du classement Top N avec count, first/last seen, services, erreurs HTTP
# - HourlyStats : statistiques par heure (count, error_count, error_rate)
# - LogStats : statistiques agrégées complètes (total lignes, IPs uniques, distribution par niveau/source/heure)
# - LogAnalysis : résultat complet d'une analyse (entries + stats + top_ips)
# - Méthodes utilitaires : has_ip(), is_error(), is_http_error(), percentage(), parse_rate(), etc.
# - Aucune dépendance externe : testable en mémoire pure
# Comment il sera utilisé (aperçu) :
# - domain/logs/parser.py créera des LogEntry à partir de lignes brutes
# - domain/logs/analytics.py calculera des LogStats et TopIP à partir de LogEntry
# - domain/logs/service.py orchestrera les analyses et retournera des LogAnalysis
# - application/queries/log_top_ips.py utilisera LogAnalysis.top_ips pour afficher le classement
# - interfaces/cli/renderers/logs_live.py affichera les LogEntry en temps réel
#---------------------------------------------------------------------->
