# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Logs domain parser.

Pure domain logic for extracting structured data from raw log lines.
This module contains regex patterns and extraction functions that
operate on strings only — it does NOT read files from disk.
"""
import re
from datetime import datetime
from typing import Optional
from omega_fire.domain.logs.models import LogEntry, LogSource, LogLevel


# Regex patterns for common log formats
IPV4_PATTERN = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
IPV6_PATTERN = r'\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b'
IP_PATTERN = rf'(?:{IPV4_PATTERN}|{IPV6_PATTERN})'

# Timestamp patterns
SYSLOG_TIMESTAMP = r'(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})'
ISO_TIMESTAMP = r'(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})'

# Log level patterns
LOG_LEVELS = {
    'debug': LogLevel.DEBUG,
    'info': LogLevel.INFO,
    'information': LogLevel.INFO,
    'notice': LogLevel.INFO,
    'warning': LogLevel.WARNING,
    'warn': LogLevel.WARNING,
    'error': LogLevel.ERROR,
    'err': LogLevel.ERROR,
    'critical': LogLevel.CRITICAL,
    'crit': LogLevel.CRITICAL,
    'fatal': LogLevel.CRITICAL,
    'alert': LogLevel.CRITICAL,
    'emergency': LogLevel.CRITICAL,
    'emerg': LogLevel.CRITICAL,
}


def extract_ip(line: str) -> Optional[str]:
    """Extract the first IP address from a log line.
    
    Args:
        line: Raw log line
    
    Returns:
        First IP address found, or None if no IP
    """
    match = re.search(IP_PATTERN, line)
    return match.group(0) if match else None


def extract_all_ips(line: str) -> list[str]:
    """Extract all IP addresses from a log line.
    
    Args:
        line: Raw log line
    
    Returns:
        List of all IP addresses found
    """
    return re.findall(IP_PATTERN, line)


def extract_timestamp(line: str) -> Optional[datetime]:
    """Extract timestamp from a log line.
    
    Supports syslog format (Jan 1 12:00:00) and ISO format (2024-01-01T12:00:00).
    
    Args:
        line: Raw log line
    
    Returns:
        Parsed datetime, or None if no timestamp found
    """
    # Try ISO format first
    iso_match = re.search(ISO_TIMESTAMP, line)
    if iso_match:
        try:
            timestamp_str = iso_match.group(1)
            # Handle both T and space separators
            timestamp_str = timestamp_str.replace('T', ' ')
            return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            pass
    
    # Try syslog format
    syslog_match = re.search(SYSLOG_TIMESTAMP, line)
    if syslog_match:
        try:
            timestamp_str = syslog_match.group(1)
            # Syslog doesn't include year, use current year
            current_year = datetime.now().year
            timestamp_str = f"{current_year} {timestamp_str}"
            return datetime.strptime(timestamp_str, '%Y %b %d %H:%M:%S')
        except ValueError:
            pass
    
    return None


def extract_log_level(line: str) -> LogLevel:
    """Extract log level from a log line.
    
    Args:
        line: Raw log line
    
    Returns:
        LogLevel enum value (default: INFO if not found)
    """
    line_lower = line.lower()
    
    for level_str, level_enum in LOG_LEVELS.items():
        # Check for level as a word boundary
        pattern = rf'\b{level_str}\b'
        if re.search(pattern, line_lower):
            return level_enum
    
    return LogLevel.INFO


def extract_service(line: str) -> Optional[str]:
    """Extract service name from a syslog-style log line.
    
    Args:
        line: Raw log line
    
    Returns:
        Service name (e.g., 'sshd', 'httpd'), or None
    """
    # Pattern: "hostname service[pid]:" or "hostname service:"
    match = re.search(r'\w+\s+([a-zA-Z0-9_-]+)(?:\[\d+\])?:', line)
    return match.group(1) if match else None


def extract_user(line: str) -> Optional[str]:
    """Extract username from an auth log line.
    
    Args:
        line: Raw log line
    
    Returns:
        Username, or None
    """
    # Pattern: "user <username>" or "for <username>"
    patterns = [
        r'user\s+([a-zA-Z0-9_-]+)',
        r'for\s+([a-zA-Z0-9_-]+)',
        r'Accepted\s+\w+\s+for\s+([a-zA-Z0-9_-]+)',
        r'Failed\s+\w+\s+for\s+([a-zA-Z0-9_-]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, line, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return None


def extract_port(line: str) -> Optional[int]:
    """Extract port number from a log line.
    
    Args:
        line: Raw log line
    
    Returns:
        Port number, or None
    """
    # Pattern: "port <number>" or ":<number>" after IP
    patterns = [
        r'port\s+(\d+)',
        r':(\d+)\b',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, line)
        if match:
            try:
                port = int(match.group(1))
                if 1 <= port <= 65535:
                    return port
            except ValueError:
                pass
    
    return None


def detect_log_source(line: str) -> LogSource:
    """Detect the log source from a log line.
    
    Args:
        line: Raw log line
    
    Returns:
        LogSource enum value
    """
    line_lower = line.lower()
    
    # Auth log indicators
    if any(indicator in line_lower for indicator in [
        'sshd', 'sudo', 'authentication', 'login', 'accepted password',
        'failed password', 'invalid user'
    ]):
        return LogSource.AUTH
    
    # Fail2ban indicators
    if 'fail2ban' in line_lower:
        return LogSource.FAIL2BAN
    
    # HTTP access log indicators
    if any(indicator in line_lower for indicator in [
        'get /', 'post /', 'http/', '404', '500', 'apache', 'nginx'
    ]):
        return LogSource.ACCESS
    
    # Kernel indicators
    if any(indicator in line_lower for indicator in [
        'kernel:', 'iptables', 'nftables', 'netfilter'
    ]):
        return LogSource.KERN
    
    # Default to syslog
    return LogSource.SYSLOG


def parse_log_line(
    line: str,
    line_number: int = 0,
    log_path: Optional[str] = None,
    source: Optional[LogSource] = None,
) -> Optional[LogEntry]:
    """Parse a raw log line into a structured LogEntry.
    
    Args:
        line: Raw log line
        line_number: Line number in the file (for error reporting)
        log_path: Path to the log file (for context)
        source: Override log source detection
    
    Returns:
        LogEntry if parsing succeeds, None if line is empty or unparseable
    """
    # Skip empty lines
    if not line.strip():
        return None
    
    # Extract components
    timestamp = extract_timestamp(line)
    ip = extract_ip(line)
    level = extract_log_level(line)
    service = extract_service(line)
    user = extract_user(line)
    port = extract_port(line)
    
    # Detect source if not provided
    if source is None:
        source = detect_log_source(line)
    
    # Create LogEntry
    return LogEntry(
        timestamp=timestamp or datetime.now(),
        source=source,
        level=level,
        ip=ip,
        message=line.strip(),
        raw_line=line,
        line_number=line_number,
        log_path=log_path,
        user=user,
        port=port,
        service=service,
    )


def parse_log_lines(
    lines: list[str],
    log_path: Optional[str] = None,
    source: Optional[LogSource] = None,
) -> list[LogEntry]:
    """Parse multiple log lines into structured LogEntry objects.
    
    Args:
        lines: List of raw log lines
        log_path: Path to the log file (for context)
        source: Override log source detection
    
    Returns:
        List of successfully parsed LogEntry objects
    """
    entries = []
    
    for i, line in enumerate(lines, start=1):
        entry = parse_log_line(line, line_number=i, log_path=log_path, source=source)
        if entry is not None:
            entries.append(entry)
    
    return entries

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit la logique d'extraction d'informations depuis une ligne de log brute. Ce module contient des regex pures pour extraire des IPs, timestamps, niveaux de log, etc. Il ne lit aucun fichier — il opère uniquement sur des chaînes de caractères.
# Pourquoi dans domain/ (charte) :
# - C'est une règle métier : comment extraire des informations structurées d'un log
# - Aucune dépendance externe (juste re, datetime, typing)
# - Fonctions pures : pas d'I/O, pas de lecture fichier
# - Testable avec des chaînes de caractères en mémoire
# Ce qu'il ne contient PAS (règles projet) :
# ❌ Pas d'import depuis infrastructure/ (pas de lecture fichier)
# ❌ Pas d'import depuis interfaces/ (pas de rendu)
# ❌ Pas d'import depuis application/ (pas de cas d'usage)
# ❌ Pas de open(), Path.read_text() — aucun I/O
# Points clés :
# - Fonctions pures : opèrent uniquement sur des chaînes, pas d'I/O
# - Regex patterns : extraction d'IP (IPv4/IPv6), timestamps, niveaux de log, services, users, ports
# - parse_log_line() : parse une ligne brute en LogEntry structuré
# - parse_log_lines() : parse plusieurs lignes en une liste de LogEntry
# - Détection automatique : detect_log_source() identifie le type de log (auth, access, syslog, etc.)
# - Aucune dépendance externe : utilise uniquement re, datetime, typing
# - Testable en mémoire : peut être testé avec des chaînes de caractères
# Comment il sera utilisé (aperçu) :
# - infrastructure/storage/files/text_store.py lira les fichiers et passera les lignes à parse_log_lines()
# - domain/logs/analytics.py utilisera les LogEntry pour calculer les statistiques
# - domain/logs/service.py orchestrera le parsing et l'analyse
# - interfaces/cli/renderers/logs_live.py affichera les LogEntry en temps réel
#---------------------------------------------------------------------->
