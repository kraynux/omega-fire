# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Journalisation applicative + audit pour une action executee depuis un
ecran Textual — equivalent TUI du bloc try/finally deja existant dans
interfaces/cli/actions.py::_execute_action_flow() (journal applicatif +
audit.log). Seul l'acteur differe ("tui:admin" au lieu de "cli:admin"),
pour distinguer la provenance dans l'historique (menu 7.3) sans changer
le format des entrees."""
from __future__ import annotations

from typing import Any


def log_action_result(
    container: Any,
    action_title: str,
    *,
    status: str = "success",
    error: str | None = None,
) -> None:
    try:
        app_logger = getattr(container, "app_logger", None) if container else None
        if app_logger:
            if status == "success":
                app_logger.info(f"Action '{action_title}' executee avec succes.")
            else:
                app_logger.error(f"Echec lors de l'execution de l'action '{action_title}' : {error}")
    except Exception:
        pass

    try:
        audit_logger = getattr(container, "audit_logger", None) if container else None
        if audit_logger:
            details: dict[str, Any] = {}
            if error:
                details["error"] = error
            audit_logger.log_event(
                event_type="action_execution",
                actor="tui:admin",
                action=action_title,
                result=status,
                details=details,
            )
    except Exception:
        pass
