# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Audit hook for the application pipeline.

This hook records execution events from the pipeline: commands executed,
steps succeeded/failed, rollbacks triggered, capabilities skipped.
It stores events in memory only — actual persistence (file writing,
database) is delegated to infrastructure/logging/.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class AuditEventType(Enum):
    """Type of audit event."""
    COMMAND_STARTED = "command_started"
    COMMAND_COMPLETED = "command_completed"
    COMMAND_FAILED = "command_failed"
    STEP_EXECUTED = "step_executed"
    STEP_FAILED = "step_failed"
    STEP_SKIPPED = "step_skipped"
    ROLLBACK_TRIGGERED = "rollback_triggered"
    ROLLBACK_COMPLETED = "rollback_completed"
    ROLLBACK_FAILED = "rollback_failed"
    CAPABILITY_MISSING = "capability_missing"
    PERMISSION_DENIED = "permission_denied"
    DEGRADED_MODE_ACTIVATED = "degraded_mode_activated"


@dataclass
class AuditEvent:
    """A single audit event.
    
    Represents an occurrence during pipeline execution that should
    be recorded for audit purposes.
    """
    event_type: AuditEventType
    timestamp: datetime = field(default_factory=datetime.now)
    command_name: Optional[str] = None
    step_name: Optional[str] = None
    details: dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error_message: Optional[str] = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert the event to a dictionary.
        
        Returns:
            Dictionary representation of the event
        """
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "command_name": self.command_name,
            "step_name": self.step_name,
            "details": self.details,
            "success": self.success,
            "error_message": self.error_message,
        }


class AuditHook:
    """Hook that records pipeline execution events.
    
    This hook maintains an in-memory list of audit events. It does NOT
    persist events to disk or database — that is the responsibility
    of infrastructure/logging/ which can consume these events.
    """
    
    def __init__(self, max_events: int = 1000):
        """Initialize the audit hook.
        
        Args:
            max_events: Maximum number of events to keep in memory.
                       Older events are discarded when this limit is reached.
        """
        self._events: list[AuditEvent] = []
        self._max_events = max_events
    
    def record_event(self, event: AuditEvent) -> None:
        """Record an audit event.
        
        Args:
            event: The audit event to record
        """
        self._events.append(event)
        
        # Trim old events if we exceed the limit
        if len(self._events) > self._max_events:
            self._events = self._events[-self._max_events:]
    
    def record_command_started(
        self,
        command_name: str,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Record that a command has started.
        
        Args:
            command_name: Name of the command
            details: Optional additional details
        """
        event = AuditEvent(
            event_type=AuditEventType.COMMAND_STARTED,
            command_name=command_name,
            details=details or {},
        )
        self.record_event(event)
    
    def record_command_completed(
        self,
        command_name: str,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Record that a command has completed successfully.
        
        Args:
            command_name: Name of the command
            details: Optional additional details
        """
        event = AuditEvent(
            event_type=AuditEventType.COMMAND_COMPLETED,
            command_name=command_name,
            details=details or {},
            success=True,
        )
        self.record_event(event)
    
    def record_command_failed(
        self,
        command_name: str,
        error_message: str,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Record that a command has failed.
        
        Args:
            command_name: Name of the command
            error_message: Error message
            details: Optional additional details
        """
        event = AuditEvent(
            event_type=AuditEventType.COMMAND_FAILED,
            command_name=command_name,
            details=details or {},
            success=False,
            error_message=error_message,
        )
        self.record_event(event)
    
    def record_step_executed(
        self,
        command_name: str,
        step_name: str,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Record that a step has been executed successfully.
        
        Args:
            command_name: Name of the command
            step_name: Name of the step
            details: Optional additional details
        """
        event = AuditEvent(
            event_type=AuditEventType.STEP_EXECUTED,
            command_name=command_name,
            step_name=step_name,
            details=details or {},
            success=True,
        )
        self.record_event(event)
    
    def record_step_failed(
        self,
        command_name: str,
        step_name: str,
        error_message: str,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Record that a step has failed.
        
        Args:
            command_name: Name of the command
            step_name: Name of the step
            error_message: Error message
            details: Optional additional details
        """
        event = AuditEvent(
            event_type=AuditEventType.STEP_FAILED,
            command_name=command_name,
            step_name=step_name,
            details=details or {},
            success=False,
            error_message=error_message,
        )
        self.record_event(event)
    
    def record_step_skipped(
        self,
        command_name: str,
        step_name: str,
        reason: str,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Record that a step has been skipped.
        
        Args:
            command_name: Name of the command
            step_name: Name of the step
            reason: Reason for skipping
            details: Optional additional details
        """
        event = AuditEvent(
            event_type=AuditEventType.STEP_SKIPPED,
            command_name=command_name,
            step_name=step_name,
            details={**(details or {}), "reason": reason},
            success=True,
        )
        self.record_event(event)
    
    def record_rollback_triggered(
        self,
        command_name: str,
        step_name: str,
        reason: str,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Record that a rollback has been triggered.
        
        Args:
            command_name: Name of the command
            step_name: Name of the step that failed
            reason: Reason for rollback
            details: Optional additional details
        """
        event = AuditEvent(
            event_type=AuditEventType.ROLLBACK_TRIGGERED,
            command_name=command_name,
            step_name=step_name,
            details={**(details or {}), "reason": reason},
            success=False,
            error_message=reason,
        )
        self.record_event(event)
    
    def record_rollback_completed(
        self,
        command_name: str,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Record that a rollback has completed successfully.
        
        Args:
            command_name: Name of the command
            details: Optional additional details
        """
        event = AuditEvent(
            event_type=AuditEventType.ROLLBACK_COMPLETED,
            command_name=command_name,
            details=details or {},
            success=True,
        )
        self.record_event(event)
    
    def record_rollback_failed(
        self,
        command_name: str,
        error_message: str,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Record that a rollback has failed.
        
        Args:
            command_name: Name of the command
            error_message: Error message
            details: Optional additional details
        """
        event = AuditEvent(
            event_type=AuditEventType.ROLLBACK_FAILED,
            command_name=command_name,
            details=details or {},
            success=False,
            error_message=error_message,
        )
        self.record_event(event)
    
    def record_capability_missing(
        self,
        command_name: str,
        capability_id: str,
        status: str,
        reason: str,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Record that a required capability is missing.
        
        Args:
            command_name: Name of the command
            capability_id: ID of the missing capability
            status: Status of the capability (MISSING, DEGRADED, DISQUALIFIED)
            reason: Reason for unavailability
            details: Optional additional details
        """
        event = AuditEvent(
            event_type=AuditEventType.CAPABILITY_MISSING,
            command_name=command_name,
            details={
                **(details or {}),
                "capability_id": capability_id,
                "status": status,
                "reason": reason,
            },
            success=False,
            error_message=f"Capability '{capability_id}' is {status}: {reason}",
        )
        self.record_event(event)
    
    def record_permission_denied(
        self,
        command_name: str,
        required_permission: str,
        reason: str,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Record that a permission check failed.
        
        Args:
            command_name: Name of the command
            required_permission: Required permission
            reason: Reason for denial
            details: Optional additional details
        """
        event = AuditEvent(
            event_type=AuditEventType.PERMISSION_DENIED,
            command_name=command_name,
            details={
                **(details or {}),
                "required_permission": required_permission,
                "reason": reason,
            },
            success=False,
            error_message=f"Permission denied: {required_permission} required",
        )
        self.record_event(event)
    
    def record_degraded_mode_activated(
        self,
        command_name: str,
        skipped_capabilities: list[str],
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Record that degraded mode has been activated.
        
        Args:
            command_name: Name of the command
            skipped_capabilities: List of capabilities that were skipped
            details: Optional additional details
        """
        event = AuditEvent(
            event_type=AuditEventType.DEGRADED_MODE_ACTIVATED,
            command_name=command_name,
            details={
                **(details or {}),
                "skipped_capabilities": skipped_capabilities,
            },
            success=True,
        )
        self.record_event(event)
    
    def get_events(self) -> list[AuditEvent]:
        """Get all recorded events.
        
        Returns:
            List of audit events
        """
        return list(self._events)
    
    def get_events_by_type(self, event_type: AuditEventType) -> list[AuditEvent]:
        """Get events filtered by type.
        
        Args:
            event_type: Type of events to retrieve
        
        Returns:
            List of events matching the type
        """
        return [e for e in self._events if e.event_type == event_type]
    
    def get_events_by_command(self, command_name: str) -> list[AuditEvent]:
        """Get events filtered by command name.
        
        Args:
            command_name: Name of the command
        
        Returns:
            List of events for the specified command
        """
        return [e for e in self._events if e.command_name == command_name]
    
    def get_recent_events(self, count: int = 10) -> list[AuditEvent]:
        """Get the most recent events.
        
        Args:
            count: Number of events to retrieve
        
        Returns:
            List of the most recent events
        """
        return self._events[-count:]
    
    def get_failed_events(self) -> list[AuditEvent]:
        """Get all failed events.
        
        Returns:
            List of events where success=False
        """
        return [e for e in self._events if not e.success]
    
    def get_successful_events(self) -> list[AuditEvent]:
        """Get all successful events.
        
        Returns:
            List of events where success=True
        """
        return [e for e in self._events if e.success]
    
    def clear(self) -> None:
        """Clear all recorded events."""
        self._events.clear()
    
    def count(self) -> int:
        """Get the total number of recorded events.
        
        Returns:
            Number of events
        """
        return len(self._events)
    
    def to_dicts(self) -> list[dict[str, Any]]:
        """Convert all events to dictionaries.
        
        Returns:
            List of event dictionaries
        """
        return [e.to_dict() for e in self._events]

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Hook d'audit du pipeline. Ce composant enregistre les événements d'exécution des commandes et des steps (succès, échec, rollback, skip). Il stocke les événements en mémoire uniquement — la persistance réelle (écriture fichier, base de données) est déléguée à infrastructure/logging/. Ce hook est purement logique et testable sans I/O.
# Pourquoi dans application/pipeline/hooks/ (charte) :
# - C'est un hook du pipeline qui capture les événements d'exécution
# - Ne dépend pas de infrastructure/ (pas de logger concret, pas d'écriture fichier)
# - Utilise les exceptions de application/exceptions.py
# - Testable en mémoire pure
# - Sera consommé par infrastructure/logging/ pour la persistance réelle
# Ce qu'il ne contient PAS (règles projet) :
# ❌ Pas d'import depuis infrastructure/ (pas de logger, pas de fichier)
# ❌ Pas d'import depuis interfaces/ (pas de rendu)
# ❌ Pas d'import depuis domain/ (pas de logique métier)
# ❌ Pas de open(), sqlite3, logging — aucun I/O
# Points clés :
# - AuditEvent : représente un événement avec type, timestamp, commande, step, détails, succès/échec
# - AuditHook : classe principale qui maintient une liste d'événements en mémoire
# - Méthodes d'enregistrement : une méthode par type d'événement (command_started, step_failed, rollback_triggered, etc.)
# - Méthodes de requête : get_events(), get_events_by_type(), get_events_by_command(), get_recent_events(), get_failed_events()
# - Limite de mémoire : max_events pour éviter la croissance infinie (défaut: 1000)
# - Aucune dépendance externe : utilise uniquement dataclasses, datetime, enum
# - Aucun I/O : ne lit ni n'écrit aucun fichier, n'utilise pas de logger
# Comment il sera utilisé (aperçu) :
# - application/pipeline/executor.py instanciera AuditHook et appellera les méthodes d'enregistrement à chaque étape
# - infrastructure/logging/audit_logger.py consommera les événements via get_events() et les persistera
# - interfaces/cli/actions.py affichera les événements récents via get_recent_events()
# - Les tests vérifieront que les événements sont correctement enregistrés
#---------------------------------------------------------------------->
