# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Application logger.

Provides a high-level interface for application logging. Wraps the
Python logging module with convenience methods for different log levels
and contexts.

This module performs file I/O to write logs and is therefore in infrastructure/.
"""
import logging
from pathlib import Path
from typing import Any, Optional
from omega_fire.infrastructure.config.paths import APP_LOG_PATH, LOGS_DIR

class AppLogger:
    """High-level application logger.
    
    Provides convenience methods for logging at different levels
    with optional context information.
    """
    
    def __init__(self, name: str = "omega_fire", log_dir: Optional[Path] = None):
        """Initialize the application logger.
        
        Args:
            name: Logger name (default: omega_fire)
            log_dir: Optional directory path for log files
        """
        self._logger = logging.getLogger(name)
        self.log_dir = log_dir or LOGS_DIR
        self.log_file = APP_LOG_PATH

        # Configuration de l'écriture automatique dans var/logs/app.log
        self._setup_file_handler()

    def _setup_file_handler(self) -> None:
        """Initialise le dossier et le FileHandler pour l'écriture sur le disque."""
        self._logger.setLevel(logging.INFO)

        # Vérifie si le FileHandler est déjà présent pour éviter les doublons d'écriture
        has_file_handler = any(isinstance(h, logging.FileHandler) for h in self._logger.handlers)

        if not has_file_handler:
            try:
                # 1. Création automatique du dossier de destination (ex: var/logs)
                self.log_dir.mkdir(parents=True, exist_ok=True)

                # 2. Création du handler d'écriture sur le fichier app.log
                file_handler = logging.FileHandler(self.log_file, encoding="utf-8")
                
                # Format d'entrée technique lisible
                formatter = logging.Formatter(
                    "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S"
                )
                file_handler.setFormatter(formatter)

                self._logger.addHandler(file_handler)
            except Exception:
                # Fallback silencieux en cas de problème de permission
                pass

    def _flush_handlers(self) -> None:
        """Forcer l'écriture disque immédiate."""
        for handler in self._logger.handlers:
            handler.flush()

    def _parse_line_timestamp(self, line: str) -> Optional["datetime"]:
        """Extract the timestamp from a line formatted as
        '[YYYY-MM-DD HH:MM:SS] [LEVEL] [name]: message' (see
        _setup_file_handler()'s formatter). Returns None if the line
        doesn't match the expected format.
        """
        from datetime import datetime
        if not line.startswith("["):
            return None
        end = line.find("]")
        if end == -1:
            return None
        try:
            return datetime.strptime(line[1:end], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None

    def clear(self, older_than: Optional[Any] = None) -> int:
        """Purge les entrées du journal applicatif.

        If older_than is provided (a datetime), only entries strictly
        BEFORE that date are removed — entries from older_than onward
        are kept and rewritten to the file. If older_than is None, the
        file is wiped entirely.

        Lines that don't match the expected timestamp format (rare —
        e.g. a multi-line traceback from exception()) are kept,
        attached to the most recently parsed timestamped line above
        them, never counted as removable on their own.

        Returns:
            Number of top-level log entries actually removed.
        """
        if not self.log_file.exists():
            return 0

        if older_than is None:
            try:
                self._flush_handlers()
                self.log_file.write_text("")
                return 1
            except Exception:
                return 0

        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception:
            return 0

        kept_lines: list[str] = []
        removed_count = 0
        current_entry_removed = False

        for line in lines:
            ts = self._parse_line_timestamp(line)
            if ts is not None:
                current_entry_removed = ts < older_than
                if current_entry_removed:
                    removed_count += 1
                else:
                    kept_lines.append(line)
            else:
                # Ligne de continuation (ex: traceback) : suit le sort
                # de l'entrée horodatée la précédant.
                if not current_entry_removed:
                    kept_lines.append(line)

        try:
            self._flush_handlers()
            with open(self.log_file, "w", encoding="utf-8") as f:
                f.writelines(kept_lines)
        except Exception:
            return 0

        return removed_count

    def delete_oldest(self, count: int) -> int:
        """Supprime les N entrées les plus anciennes du journal
        applicatif (par entrée horodatée, continuations incluses avec
        leur ligne parente), conserve le reste.

        Returns:
            Number of top-level log entries actually removed.
        """
        if count <= 0 or not self.log_file.exists():
            return 0

        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception:
            return 0

        # Regroupe chaque ligne horodatée avec ses éventuelles lignes
        # de continuation (tracebacks) en une seule "entrée".
        entries: list[tuple[Optional[Any], list[str]]] = []
        for line in lines:
            ts = self._parse_line_timestamp(line)
            if ts is not None or not entries:
                entries.append((ts, [line]))
            else:
                entries[-1][1].append(line)

        timestamped = [e for e in entries if e[0] is not None]
        timestamped.sort(key=lambda e: e[0])

        to_remove_ts = {id(e) for e in timestamped[:min(count, len(timestamped))]}
        removed_count = len(to_remove_ts)

        kept_lines: list[str] = []
        for entry in entries:
            if id(entry) in to_remove_ts:
                continue
            kept_lines.extend(entry[1])

        try:
            self._flush_handlers()
            with open(self.log_file, "w", encoding="utf-8") as f:
                f.writelines(kept_lines)
        except Exception:
            return 0

        return removed_count

    def debug(self, message: str, **context: Any) -> None:
        """Log a debug message.
        
        Args:
            message: Log message
            context: Optional context information
        """
        self._logger.debug(self._format_message(message, context))
    
    def info(self, message: str, **context: Any) -> None:
        """Log an info message.
        
        Args:
            message: Log message
            context: Optional context information
        """
        self._logger.info(self._format_message(message, context))
    
    def warning(self, message: str, **context: Any) -> None:
        """Log a warning message.
        
        Args:
            message: Log message
            context: Optional context information
        """
        self._logger.warning(self._format_message(message, context))
    
    def error(self, message: str, exc_info: bool = False, **context: Any) -> None:
        """Log an error message.
        
        Args:
            message: Log message
            exc_info: If True, include exception information
            context: Optional context information
        """
        self._logger.error(self._format_message(message, context), exc_info=exc_info)
    
    def critical(self, message: str, exc_info: bool = False, **context: Any) -> None:
        """Log a critical message.
        
        Args:
            message: Log message
            exc_info: If True, include exception information
            context: Optional context information
        """
        self._logger.critical(self._format_message(message, context), exc_info=exc_info)
    
    def exception(self, message: str, **context: Any) -> None:
        """Log an exception with traceback.
        
        Args:
            message: Log message
            context: Optional context information
        """
        self._logger.exception(self._format_message(message, context))
    
    def _format_message(self, message: str, context: dict[str, Any]) -> str:
        """Format a log message with context.
        
        Args:
            message: Base message
            context: Context information
        
        Returns:
            Formatted message string
        """
        if not context:
            return message
        
        context_str = ", ".join(f"{k}={v}" for k, v in context.items())
        return f"{message} [{context_str}]"
    
    def get_logger(self) -> logging.Logger:
        """Get the underlying Python logger.
        
        Returns:
            Logger instance
        """
        return self._logger


def get_app_logger(name: str = "omega_fire") -> AppLogger:
    """Convenience function to get an application logger.
    
    Args:
        name: Logger name
    
    Returns:
        AppLogger instance
    """
    return AppLogger(name)


# --- Alias de compatibilité pour l'initialisation au démarrage ---

def init_logging() -> AppLogger:
    """Initialise et retourne le logger principal applicatif."""
    return get_app_logger()


def setup_logging() -> AppLogger:
    """Alias pour l'initialisation du logger."""
    return get_app_logger()


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Fournit une interface haut-niveau pour le logging applicatif
# - Wraps le module logging Python avec des méthodes de convenance
# - Supporte le contexte additionnel dans les messages
# Pourquoi dans infrastructure/logging/ (charte) :
# - C'est de l'infrastructure technique (logging)
# - Le domaine ne doit pas connaître le système de logging
# - L'application/ utilise AppLogger via injection
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier (pas de règles de blacklist, politiques)
# ❌ Pas de dépendance vers domain/, application/ ou interfaces/
# ❌ Pas de décision de quoi logger (c'est le rôle des composants)
# Points clés :
# - AppLogger : classe principale avec méthodes debug/info/warning/error/critical
# - clear(older_than=...) / delete_oldest(count) : purge du journal
#   applicatif, symétrique à AuditLogger — parsing du timestamp entre
#   crochets en tête de ligne (format texte, pas JSON), lignes de
#   continuation (tracebacks) rattachées à l'entrée horodatée précédente
# - Support du contexte : **context ajouté aux messages
# - exception() : log avec traceback automatique
# - _format_message() : formate "message [key=value, ...]"
# - get_logger() : retourne le logger Python sous-jacent
# - Fonction de convenance : get_app_logger()
# Comment il sera utilisé (aperçu) :
# - Tous les composants recevront AppLogger via injection
# - Les tests mockeront AppLogger pour vérifier les appels
# - infrastructure/logging/audit_logger.py utilisera un logger séparé pour l'audit
#---------------------------------------------------------------------->
