# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Core enums.

Transversal enumerations used across all layers of the application.
These enums define the common vocabulary of the system.
"""
from enum import Enum


class CapabilityStatus(Enum):
    """Status of a system capability.
    
    Used by the capability registry to track what is available,
    degraded, missing, or disqualified on the current system.
    """
    AVAILABLE = "available"         # Fully functional
    DEGRADED = "degraded"           # Partially functional
    MISSING = "missing"             # Not installed or not detected
    DISQUALIFIED = "disqualified"   # Detected but unusable (version, config, etc.)


class BackendType(Enum):
    """Type of firewall backend.
    
    Identifies the concrete backend implementation.
    """
    NFTABLES = "nftables"
    IPTABLES = "iptables"
    FAIL2BAN = "fail2ban"
    CONNTRACK = "conntrack"


class LogLevel(Enum):
    """Log severity level.
    
    Used by the logging infrastructure to categorize messages.
    """
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ServiceManagerType(Enum):
    """Type of service manager detected on the system.
    
    Used by infrastructure/backends/service_manager/ to select
    the appropriate adapter.
    """
    SYSTEMD = "systemd"
    OPENRC = "openrc"
    RUNIT = "runit"
    UNKNOWN = "unknown"
    NONE = "none"  # No service manager detected


class ExportFormat(Enum):
    """Format for exports and reports.
    
    Used by infrastructure/exporters/ to select the serializer.
    """
    JSON = "json"
    TXT = "txt"
    HTML = "html"
    CSV = "csv"


class RuleAction(Enum):
    """Action of a firewall rule.
    
    Note: This is a duplicate of domain/rules/models.py RuleAction.
    It is defined here for transversal use (e.g., in DTOs, policies).
    The domain version should be preferred for business logic.
    """
    ACCEPT = "accept"
    DROP = "drop"
    REJECT = "reject"
    LOG = "log"

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit les enums transverses du système : statuts de capacités, types de backend, niveaux de log. C'est le langage commun utilisé par toutes les couches.
# Points clés :
# - CapabilityStatus : AVAILABLE, DEGRADED, MISSING, DISQUALIFIED
# - BackendType : NFTABLES, IPTABLES, FAIL2BAN, CONNTRACK
# - LogLevel : DEBUG, INFO, WARNING, ERROR, CRITICAL
# - ServiceManagerType : SYSTEMD, OPENRC, RUNIT, UNKNOWN, NONE
# - ExportFormat : JSON, TXT, HTML, CSV
# - Aucune dépendance externe : utilise uniquement enum
# - Aucun I/O : définitions pures
#---------------------------------------------------------------------->
