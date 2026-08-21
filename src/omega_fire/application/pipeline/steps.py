# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Pipeline step definitions and utilities.

Provides reusable step factories and step composition utilities
for building ExecutionPlans. This module does NOT execute steps —
it only defines and composes them.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from omega_fire.application.pipeline.planner import PipelineStep, create_step


def make_validation_step(
    name: str,
    validate_fn: Callable[[], list[str]],
) -> PipelineStep:
    """Create a validation step that raises on errors.

    Args:
        name: Step name for logging/debugging
        validate_fn: Function returning list of error strings (empty = valid)

    Returns:
        PipelineStep configured for validation
    """
    def _execute() -> None:
        errors = validate_fn()
        if errors:
            raise ValueError(f"Validation failed: {'; '.join(errors)}")

    return create_step(
        name=name,
        execute=_execute,
        requires=[],
        skip_on_missing_capability=False,
    )


def make_backend_step(
    name: str,
    execute_fn: Callable[[], Any],
    backend: str,
    rollback_fn: Optional[Callable[[], Any]] = None,
) -> PipelineStep:
    """Create a step that requires a specific backend capability.

    Args:
        name: Step name
        execute_fn: Function to execute
        backend: Required backend capability ID
        rollback_fn: Optional rollback function

    Returns:
        PipelineStep configured for backend execution
    """
    return create_step(
        name=name,
        execute=execute_fn,
        requires=[backend],
        rollback=rollback_fn,
        skip_on_missing_capability=False,
    )


def make_audit_step(
    name: str,
    audit_fn: Callable[[], None],
) -> PipelineStep:
    """Create an audit step that can be skipped if unavailable.

    Args:
        name: Step name
        audit_fn: Function to call for auditing

    Returns:
        PipelineStep configured for optional audit
    """
    return create_step(
        name=name,
        execute=audit_fn,
        requires=[],
        skip_on_missing_capability=True,
    )


def make_notification_step(
    name: str,
    notify_fn: Callable[[], None],
) -> PipelineStep:
    """Create a notification step that can be skipped if unavailable.

    Args:
        name: Step name
        notify_fn: Function to call for notification

    Returns:
        PipelineStep configured for optional notification
    """
    return create_step(
        name=name,
        execute=notify_fn,
        requires=[],
        skip_on_missing_capability=True,
    )


def compose_steps(
    validation: Optional[PipelineStep] = None,
    execution: Optional[PipelineStep] = None,
    audit: Optional[PipelineStep] = None,
    notification: Optional[PipelineStep] = None,
) -> list[PipelineStep]:
    """Compose a standard step sequence, omitting None entries.

    Args:
        validation: Optional validation step
        execution: Optional execution step
        audit: Optional audit step
        notification: Optional notification step

    Returns:
        Ordered list of non-None steps
    """
    steps: list[PipelineStep] = []
    if validation is not None:
        steps.append(validation)
    if execution is not None:
        steps.append(execution)
    if audit is not None:
        steps.append(audit)
    if notification is not None:
        steps.append(notification)
    return steps

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Fournit des factories de steps réutilisables pour les ExecutionPlans
# - Centralise la création de steps standards (validation, backend, audit)
# - Ne exécute PAS les steps, seulement les construit
#
# Pourquoi dans application/pipeline/ (charte) :
# - C'est de l'orchestration applicative
# - Dépend de application/pipeline/planner.py pour PipelineStep
# - Ne dépend pas de infrastructure/
# - Ne dépend pas de interfaces/
#
# Ce qu'il ne contient PAS :
# ❌ Pas d'import depuis infrastructure/
# ❌ Pas d'import depuis interfaces/
# ❌ Pas de subprocess, sqlite3, rich
# ❌ Pas d'exécution réelle
#
# Points clés :
# - make_validation_step() : crée un step de validation
# - make_backend_step() : crée un step nécessitant un backend
# - make_audit_step() : crée un step d'audit (skippable)
# - make_notification_step() : crée un step de notification (skippable)
# - compose_steps() : assemble une séquence standard de steps
#---------------------------------------------------------------------->
