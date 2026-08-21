# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Logs domain service.

Orchestrates business operations on logs.
This service coordinates the domain modules (parser, analytics, rotation, cleanup)
and enforces business rules by raising domain exceptions.
"""
from datetime import datetime
from typing import Optional
from omega_fire.domain.logs.models import (
    LogEntry,
    LogSource,
    LogLevel,
    LogStats,
    LogAnalysis,
    TopIP,
)
from omega_fire.domain.logs.exceptions import (
    LogParseError,
    LogAnalysisError,
    LogRotationError,
    LogCleanupError,
    InvalidRetentionError,
)
from omega_fire.domain.logs.parser import parse_log_lines
from omega_fire.domain.logs.analytics import (
    compute_stats,
    compute_top_ips,
    filter_entries_by_ip,
    filter_entries_by_level,
    filter_entries_by_source,
    filter_entries_by_time_range,
    filter_error_entries,
)
from omega_fire.domain.logs.rotation import (
    RotationPolicy,
    RotationPlan,
    plan_rotation,
)
from omega_fire.domain.logs.cleanup import (
    RetentionPolicy,
    CleanupPlan,
    FileInfo,
    plan_cleanup,
    validate_retention_parameters,
)


class LogsService:
    """Domain service for log operations."""
    
    def parse_lines(
        self,
        lines: list[str],
        log_path: Optional[str] = None,
        source: Optional[LogSource] = None,
    ) -> list[LogEntry]:
        """Parse raw log lines into structured LogEntry objects."""
        try:
            return parse_log_lines(lines, log_path=log_path, source=source)
        except Exception as e:
            raise LogParseError(
                log_path or "unknown",
                0,
                f"Parsing failed: {e}"
            ) from e
    
    def analyze_entries(
        self,
        entries: list[LogEntry],
        total_lines: int = 0,
        log_path: Optional[str] = None,
        top_n: int = 10,
    ) -> LogStats:
        """Analyze log entries and compute statistics."""
        try:
            return compute_stats(
                entries=entries,
                total_lines=total_lines,
                log_path=log_path,
                top_n=top_n,
            )
        except Exception as e:
            raise LogAnalysisError(
                "stats_computation",
                f"Analysis failed: {e}"
            ) from e
    
    def get_top_ips(
        self,
        entries: list[LogEntry],
        n: int = 10,
        min_count: int = 1,
    ) -> list[TopIP]:
        """Get the Top N IP addresses by occurrence count."""
        return compute_top_ips(entries, n=n, min_count=min_count)
    
    def filter_entries(
        self,
        entries: list[LogEntry],
        ip: Optional[str] = None,
        level: Optional[LogLevel] = None,
        source: Optional[LogSource] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        errors_only: bool = False,
    ) -> list[LogEntry]:
        """Filter log entries by various criteria."""
        filtered = entries
        
        if ip:
            filtered = filter_entries_by_ip(filtered, ip)
        if level:
            filtered = filter_entries_by_level(filtered, level)
        if source:
            filtered = filter_entries_by_source(filtered, source)
        if start_time or end_time:
            filtered = filter_entries_by_time_range(filtered, start_time, end_time)
        if errors_only:
            filtered = filter_error_entries(filtered)
        
        return filtered
    
    def plan_rotation(
        self,
        log_path: str,
        policy: RotationPolicy,
        file_size_bytes: Optional[int] = None,
        file_mtime: Optional[datetime] = None,
        line_count: Optional[int] = None,
        last_rotation: Optional[datetime] = None,
        existing_rotations: Optional[list[str]] = None,
        rotation_number: int = 1,
    ) -> RotationPlan:
        """Plan a log rotation operation."""
        errors = policy.validate()
        if errors:
            raise LogRotationError(
                log_path,
                f"Invalid rotation policy: {'; '.join(errors)}"
            )
        
        try:
            return plan_rotation(
                log_path=log_path,
                policy=policy,
                file_size_bytes=file_size_bytes,
                file_mtime=file_mtime,
                line_count=line_count,
                last_rotation=last_rotation,
                existing_rotations=existing_rotations,
                rotation_number=rotation_number,
            )
        except Exception as e:
            raise LogRotationError(
                log_path,
                f"Rotation planning failed: {e}"
            ) from e
    
    def plan_cleanup(
        self,
        files: list[FileInfo],
        policy: RetentionPolicy,
        now: Optional[datetime] = None,
    ) -> CleanupPlan:
        """Plan a cleanup operation based on retention policy.
        
        Args:
            files: List of all log and archive files
            policy: Retention policy to apply
            now: Current time for age calculation (default: datetime.now())
        
        Returns:
            CleanupPlan describing what needs to be deleted
        
        Raises:
            LogCleanupError: If the policy is invalid
            InvalidRetentionError: If retention parameters are invalid
        """
        errors = policy.validate()
        if errors:
            raise InvalidRetentionError(
                "retention_policy",
                policy,
                f"Invalid retention policy: {'; '.join(errors)}"
            )
        
        try:
            return plan_cleanup(files=files, policy=policy, now=now)
        except Exception as e:
            raise LogCleanupError(
                "multiple files",
                f"Cleanup planning failed: {e}"
            ) from e
    
    def validate_retention_parameters(
        self,
        max_age_days: Optional[int] = None,
        max_archive_age_days: Optional[int] = None,
        max_total_size_bytes: Optional[int] = None,
    ) -> list[str]:
        """Validate retention parameters."""
        return validate_retention_parameters(
            max_age_days=max_age_days,
            max_archive_age_days=max_archive_age_days,
            max_total_size_bytes=max_total_size_bytes,
        )
    
    def create_full_analysis(
        self,
        entries: list[LogEntry],
        total_lines: int = 0,
        log_path: Optional[str] = None,
        top_n: int = 10,
    ) -> LogAnalysis:
        """Create a complete log analysis with entries and statistics."""
        stats = self.analyze_entries(
            entries=entries,
            total_lines=total_lines,
            log_path=log_path,
            top_n=top_n,
        )
        
        return LogAnalysis(
            entries=entries,
            stats=stats,
            top_ips=stats.top_ips,
        )

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Orchestration métier des opérations sur les logs. Ce service coordonne les modules du domaine (parser, analytics, rotation, cleanup) et applique les règles métier (validation, planification). Il lève les exceptions métier quand une règle est violée.
# Pourquoi dans domain/ (charte) :
# - C'est la logique métier centrale du sous-domaine logs
# - Utilise uniquement les autres modules du domaine (models, parser, analytics, rotation, cleanup, exceptions)
# - Lève les exceptions métier définies dans exceptions.py
# - Aucune dépendance externe (pas de subprocess, sqlite3, rich)
# Ce qu'il ne contient PAS (règles projet) :
# ❌ Pas d'import depuis infrastructure/ (pas de lecture fichier, pas de DB)
# ❌ Pas d'import depuis application/ (pas de cas d'usage)
# ❌ Pas d'import depuis interfaces/ (pas de rendu)
# ❌ Pas de logique d'exécution (juste l'orchestration métier)
# Points clés :
# - Orchestration métier : coordonne parser, analytics, rotation, cleanup
# - Validation stricte : vérifie les politiques de rotation et de rétention avant de planifier
# - Exceptions métier : lève LogParseError, LogAnalysisError, LogRotationError, LogCleanupError, InvalidRetentionError
# - Aucune dépendance externe : utilise uniquement les modules du domaine
# - Testable en mémoire : peut être testé avec des LogEntry et FileInfo construits manuellement
# - Méthodes utilitaires : filter_entries(), get_top_ips(), create_full_analysis()
# Comment il sera utilisé (aperçu) :
# - application/queries/log_top_ips.py instanciera LogsService et appellera get_top_ips()
# - application/commands/rotate_logs.py appellera plan_rotation() pour calculer le plan
# - application/queries/dashboard_summary.py appellera create_full_analysis() pour le tableau de bord
# - interfaces/cli/actions.py proposera les options de filtrage via filter_entries()
#---------------------------------------------------------------------->
