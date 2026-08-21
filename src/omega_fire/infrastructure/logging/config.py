# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Logging configuration.

Configures the Python logging system for the application. Sets up
handlers, formatters, and log levels for both application logs and
audit logs. Uses RotatingFileHandler for log rotation.

This module performs file I/O to write logs and is therefore in infrastructure/.
"""
import logging
import logging.handlers
from pathlib import Path
from typing import Optional


def configure_logging(
    app_log_path: Path,
    audit_log_path: Path,
    level: str = "INFO",
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
    format_str: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
) -> None:
    """Configure the logging system for the application.
    
    Sets up:
    - Root logger with console and file handlers
    - Application logger (omega_fire) with rotating file handler
    - Audit logger (omega_fire.audit) with separate rotating file handler
    
    Args:
        app_log_path: Path to the application log file
        audit_log_path: Path to the audit log file
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        max_bytes: Maximum log file size before rotation
        backup_count: Number of backup files to keep
        format_str: Log message format
    """
    # Ensure parent directories exist
    app_log_path.parent.mkdir(parents=True, exist_ok=True)
    audit_log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Parse log level
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(format_str)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Application file handler (rotating)
    app_file_handler = logging.handlers.RotatingFileHandler(
        filename=str(app_log_path),
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    app_file_handler.setLevel(log_level)
    app_file_handler.setFormatter(formatter)
    root_logger.addHandler(app_file_handler)
    
    # Configure audit logger (separate file)
    audit_logger = logging.getLogger("omega_fire.audit")
    audit_logger.setLevel(logging.INFO)
    audit_logger.propagate = False  # Don't propagate to root
    
    # Clear existing audit handlers
    audit_logger.handlers.clear()
    
    # Audit file handler (rotating)
    audit_file_handler = logging.handlers.RotatingFileHandler(
        filename=str(audit_log_path),
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    audit_file_handler.setLevel(logging.INFO)
    audit_file_handler.setFormatter(formatter)
    audit_logger.addHandler(audit_file_handler)
    
    # Suppress noisy loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)


def get_app_logger(name: str = "omega_fire") -> logging.Logger:
    """Get the application logger.
    
    Args:
        name: Logger name (default: omega_fire)
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def get_audit_logger() -> logging.Logger:
    """Get the audit logger.
    
    Returns:
        Logger instance for audit events
    """
    return logging.getLogger("omega_fire.audit")


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Configure le système de logging Python pour l'application
# - Met en place les handlers, formatters et niveaux de log
# - Gère deux fichiers de log séparés : application et audit
# - Utilise RotatingFileHandler pour la rotation automatique
# Pourquoi dans infrastructure/logging/ (charte) :
# - C'est de la configuration technique (logging)
# - Le domaine ne doit pas connaître le système de logging
# - L'application/ utilise les loggers via injection
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier (pas de règles de blacklist, politiques)
# ❌ Pas de dépendance vers domain/, application/ ou interfaces/
# ❌ Pas de décision de quoi logger (c'est le rôle des composants)
# Points clés :
# - configure_logging() : configure root + app + audit loggers
#   - Console handler pour le debug
#   - RotatingFileHandler pour l'app (omega-fire.log)
#   - RotatingFileHandler séparé pour l'audit (audit.log)
# - get_app_logger() : retourne le logger applicatif
# - get_audit_logger() : retourne le logger d'audit
# - Rotation : max_bytes (défaut 10MB) + backup_count (défaut 5)
# - Supprime les loggers bruyants (urllib3, requests)
# - Format : timestamp - nom - niveau - message
# Comment il sera utilisé (aperçu) :
# - app/bootstrap.py appellera configure_logging() au démarrage
# - infrastructure/logging/app_logger.py utilisera get_app_logger()
# - infrastructure/logging/audit_logger.py utilisera get_audit_logger()
# - Les tests mockeront les loggers pour vérifier les appels
#---------------------------------------------------------------------->
