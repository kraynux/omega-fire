# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Pipeline rollback logic.

Handles the rollback of executed steps when a pipeline fails.
Executes rollback functions in reverse order of execution.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from omega_fire.application.pipeline.planner import PipelineStep
from omega_fire.application.exceptions import RollbackError


@dataclass
class RollbackResult:
    """Result of a rollback operation."""
    success: bool
    rolled_back_steps: list[str] = field(default_factory=list)
    failed_step: Optional[str] = None
    error_message: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "rolled_back_steps": list(self.rolled_back_steps),
            "failed_step": self.failed_step,
            "error_message": self.error_message,
        }


class RollbackManager:
    """Manages rollback of pipeline steps in reverse order.

    When a pipeline step fails, this manager executes the rollback
    functions of all previously executed steps, in reverse order.
    """

    def __init__(self) -> None:
        self._executed_steps: list[PipelineStep] = []

    def record_execution(self, step: PipelineStep) -> None:
        """Record that a step was successfully executed.

        Args:
            step: The step that was executed
        """
        self._executed_steps.append(step)

    def rollback(self) -> RollbackResult:
        """Execute rollback for all recorded steps in reverse order.

        Returns:
            RollbackResult with success/failure details
        """
        result = RollbackResult(success=True)

        for step in reversed(self._executed_steps):
            if step.rollback is None:
                continue
            try:
                step.rollback()
                result.rolled_back_steps.append(step.name)
            except Exception as exc:
                result.success = False
                result.failed_step = step.name
                result.error_message = str(exc)
                break

        return result

    def has_rollback_available(self) -> bool:
        """Check if any executed step has a rollback function.

        Returns:
            True if at least one step has a rollback
        """
        return any(s.rollback is not None for s in self._executed_steps)

    def reset(self) -> None:
        """Clear all recorded steps."""
        self._executed_steps.clear()

    @property
    def executed_count(self) -> int:
        """Number of steps recorded for potential rollback."""
        return len(self._executed_steps)


def execute_rollback(steps: list[PipelineStep]) -> RollbackResult:
    """Convenience function to rollback a list of steps.

    Args:
        steps: Steps to rollback (will be reversed internally)

    Returns:
        RollbackResult with details
    """
    manager = RollbackManager()
    for step in steps:
        manager.record_execution(step)
    return manager.rollback()

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Gère le rollback des steps exécutés quand un pipeline échoue
# - Exécute les fonctions de rollback en ordre inverse
# - Fournit un résultat structuré du rollback
#
# Pourquoi dans application/pipeline/ (charte) :
# - C'est de l'orchestration applicative
# - Dépend de application/pipeline/planner.py pour PipelineStep
# - Dépend de application/exceptions.py pour RollbackError
# - Ne dépend pas de infrastructure/
#
# Ce qu'il ne contient PAS :
# ❌ Pas d'import depuis infrastructure/
# ❌ Pas d'import depuis interfaces/
# ❌ Pas de subprocess, sqlite3, rich
#
# Points clés :
# - RollbackResult : résultat structuré du rollback
# - RollbackManager : enregistre les steps et exécute le rollback
# - record_execution() : enregistre un step exécuté
# - rollback() : exécute les rollbacks en ordre inverse
# - has_rollback_available() : vérifie si un rollback est possible
# - execute_rollback() : fonction de convenance
#---------------------------------------------------------------------->
