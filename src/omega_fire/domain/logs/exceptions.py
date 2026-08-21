# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Logs domain exceptions.

Pure domain exceptions for the logs subdomain.
These express business rule violations, not technical failures
of file reading or log parsing. They are caught by application/
and translated into Results or user-facing messages.
"""


class LogsError(Exception):
    """Base exception for logs domain.
    
    All domain-specific exceptions for logs inherit from this.
    """
    pass


class LogNotFoundError(LogsError):
    """Raised when attempting to analyze a log file that does not exist.
    
    Business rule: a log file must exist before it can be analyzed.
    """
    def __init__(self, log_path: str):
        self.log_path = log_path
        super().__init__(f"Log file not found: {log_path}")


class LogParseError(LogsError):
    """Raised when a log line cannot be parsed according to expected format.
    
    Examples: malformed log line, missing IP, invalid timestamp format,
    unrecognized log structure.
    """
    def __init__(self, log_path: str, line_number: int, reason: str):
        self.log_path = log_path
        self.line_number = line_number
        self.reason = reason
        super().__init__(
            f"Parse error in {log_path} at line {line_number}: {reason}"
        )


class InvalidLogFormatError(LogsError):
    """Raised when the overall log format is invalid or unsupported.
    
    Examples: binary file instead of text, encoding error,
    completely unrecognized structure.
    """
    def __init__(self, log_path: str, reason: str):
        self.log_path = log_path
        self.reason = reason
        super().__init__(f"Invalid log format for {log_path}: {reason}")


class LogAnalysisError(LogsError):
    """Raised when a log analysis operation fails.
    
    Examples: Top N computation failed, statistics generation error,
    invalid analysis parameters.
    """
    def __init__(self, analysis_type: str, reason: str):
        self.analysis_type = analysis_type
        self.reason = reason
        super().__init__(f"Log analysis error ({analysis_type}): {reason}")


class LogRotationError(LogsError):
    """Raised when log rotation fails.
    
    Examples: backup directory not writable, compression failed,
    rotation conflict, insufficient permissions.
    """
    def __init__(self, log_path: str, reason: str):
        self.log_path = log_path
        self.reason = reason
        super().__init__(f"Log rotation error for {log_path}: {reason}")


class LogCleanupError(LogsError):
    """Raised when log cleanup or purge fails.
    
    Examples: retention policy violation, cleanup conflict,
    backup deletion failed.
    """
    def __init__(self, log_path: str, reason: str):
        self.log_path = log_path
        self.reason = reason
        super().__init__(f"Log cleanup error for {log_path}: {reason}")


class BackupNotFoundError(LogsError):
    """Raised when attempting to restore a backup that does not exist.
    
    Business rule: a backup must exist before it can be restored.
    """
    def __init__(self, backup_path: str):
        self.backup_path = backup_path
        super().__init__(f"Backup not found: {backup_path}")


class InvalidRetentionError(LogsError):
    """Raised when retention parameters are invalid.
    
    Examples: negative retention period, invalid line count,
    conflicting retention rules.
    """
    def __init__(self, parameter: str, value, reason: str):
        self.parameter = parameter
        self.value = value
        self.reason = reason
        super().__init__(
            f"Invalid retention parameter '{parameter}' (value={value}): {reason}"
        )
# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit les exceptions métier spécifiques au sous-domaine logs. Ces exceptions expriment des violations de règles métier (log introuvable, format invalide, analyse impossible, rotation échouée), pas des pannes techniques du système de fichiers.
# Pourquoi dans domain/ (charte) :
# - C'est une erreur métier : violation d'un invariant du domaine logs
# - Aucune dépendance externe (hérite juste de Exception)
# - Testable sans aucun accès au système de fichiers
# - Sera capturée par application/ pour être traduite en Result ou message utilisateur
# Ce qu'il ne contient PAS (règles projet) :
# ❌ Pas d'import depuis infrastructure/ (pas d'erreur technique de lecture fichier)
# ❌ Pas d'import depuis interfaces/ (pas de message utilisateur)
# ❌ Pas d'import depuis application/ (pas de logique de cas d'usage)
# Points clés à retenir
# - Hiérarchie claire : toutes les exceptions héritent de LogsError
#  - 8 exceptions ciblées :
#   - LogNotFoundError : fichier log inexistant
#   - LogParseError : ligne de log mal formée
#   - InvalidLogFormatError : format global invalide
#   - LogAnalysisError : échec d'analyse (Top N, stats)
#   - LogRotationError : échec de rotation
#   - LogCleanupError : échec de purge
#   - BackupNotFoundError : backup inexistant
#   - InvalidRetentionError : paramètres de rétention invalides
#  - Contexte riche : chaque exception stocke les données pertinentes (log_path, line_number, analysis_type)
#  - Aucune dépendance : ne sait rien du système de fichiers, de Rich ou de SQLite
# Comment elles seront utilisées (aperçu) :
# domain/logs/service.py les lèvera quand une règle métier est violée
# application/commands/rotate_logs.py les capturera et les traduira en Result.fail()
# interfaces/cli/actions.py affichera le message à l'utilisateur
#---------------------------------------------------------------------->
