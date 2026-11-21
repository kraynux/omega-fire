# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Core audit service."""

from datetime import datetime
from enum import Enum
from typing import Any


class AuditLevel(Enum):
    """Audit event severity level."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditService:
    """Centralized audit event recording service."""

    def __init__(self, max_events: int = 10000):
        self._events: list[dict[str, Any]] = []
        self._max_events = max_events

    def record(
        self,
        level: AuditLevel,
        action: str,
        user: str = "system",
        details: dict[str, Any] | None = None,
    ) -> None:
        event = {
            "timestamp": datetime.now().isoformat(),
            "level": level.value,
            "action": action,
            "user": user,
            "details": details or {},
        }
        self._events.append(event)
        if len(self._events) > self._max_events:
            self._events = self._events[-self._max_events :]

    def record_info(
        self, action: str, user: str = "system", details: dict[str, Any] | None = None
    ) -> None:
        self.record(AuditLevel.INFO, action, user, details)

    def record_warning(
        self, action: str, user: str = "system", details: dict[str, Any] | None = None
    ) -> None:
        self.record(AuditLevel.WARNING, action, user, details)

    def record_error(
        self, action: str, user: str = "system", details: dict[str, Any] | None = None
    ) -> None:
        self.record(AuditLevel.ERROR, action, user, details)

    def record_critical(
        self, action: str, user: str = "system", details: dict[str, Any] | None = None
    ) -> None:
        self.record(AuditLevel.CRITICAL, action, user, details)

    def get_events(self, limit: int | None = None) -> list[dict[str, Any]]:
        if limit is None:
            return list(self._events)
        return self._events[-limit:]

    def get_events_by_level(self, level: AuditLevel) -> list[dict[str, Any]]:
        return [e for e in self._events if e["level"] == level.value]

    def get_events_by_action(self, action: str) -> list[dict[str, Any]]:
        return [e for e in self._events if e["action"] == action]

    def count(self) -> int:
        return len(self._events)

    def clear(self) -> None:
        self._events.clear()


def create_audit_service(max_events: int = 10000) -> AuditService:
    return AuditService(max_events)
