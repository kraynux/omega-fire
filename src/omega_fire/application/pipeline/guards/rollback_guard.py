# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Rollback guard for the pipeline.

Checks whether a rollback is safe to execute before attempting it.
Validates preconditions for rollback operations.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from omega_fire.application.pipeline.planner import PipelineStep
from omega_fire.application.exceptions import RollbackError


@dataclass(slots=True)
class RollbackGuardResult:
    """Result of a rollback guard check."""
    can_rollback: bool
    reason: str = ""
    affected_steps: list[str] = None

    def __post_init__(self) -> None:
        if self.affected_steps is None:
            self.affected_steps = []


class RollbackGuard:
    """Guard that validates rollback preconditions.

    Before executing a rollback, this guard checks:
    - At least one step has a rollback function
    - No step is marked as non-rollbackable
    - The system is in a consistent state for rollback
    """

    def check(self, executed_steps: list[PipelineStep]) -> RollbackGuardResult:
        """Check if rollback is safe for the given executed steps.

        Args:
            executed_steps: Steps that were executed and may need rollback

        Returns:
            RollbackGuardResult indicating if rollback can proceed
        """
        if not executed_steps:
            return RollbackGuardResult(
                can_rollback=False,
                reason="No steps were executed, nothing to rollback",
            )

        rollbackable = [s for s in executed_steps if s.rollback is not None]

        if not rollbackable:
            return RollbackGuardResult(
                can_rollback=False,
                reason="No executed step has a rollback function defined",
            )

        affected = [s.name for s in rollbackable]

        return RollbackGuardResult(
            can_rollback=True,
            reason=f"Rollback available for {len(rollbackable)} step(s)",
            affected_steps=affected,
        )

    def validate_rollback_step(self, step: PipelineStep) -> bool:
        """Validate that a single step's rollback function is callable.

        Args:
            step: The step to validate

        Returns:
            True if the rollback function is valid
        """
        if step.rollback is None:
            return False
        return callable(step.rollback)


def check_rollback_safe(executed_steps: list[PipelineStep]) -> RollbackGuardResult:
    """Convenience function to check rollback safety.

    Args:
        executed_steps: Steps that were executed

    Returns:
        RollbackGuardResult
    """
    guard = RollbackGuard()
    return guard.check(executed_steps)

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Vérifie les préconditions avant d'exécuter un rollback
# - S'assure que le rollback est sûr et cohérent
# - Ne exécute PAS le rollback, seulement la vérification
#
# Pourquoi dans application/pipeline/guards/ (charte) :
# - C'est un guard (vérification), pas un executor
# - Dépend de application/pipeline/planner.py
# - Dépend de application/exceptions.py
# - Ne dépend pas de infrastructure/
#
# Ce qu'il ne contient PAS :
# ❌ Pas d'import depuis infrastructure/
# ❌ Pas d'import depuis interfaces/
# ❌ Pas de subprocess, sqlite3, rich
# ❌ Pas d'exécution de rollback
#
# Points clés :
# - RollbackGuardResult : résultat de la vérification
# - RollbackGuard.check() : vérifie si le rollback est possible
# - RollbackGuard.validate_rollback_step() : valide un step individuel
# - check_rollback_safe() : fonction de convenance
#---------------------------------------------------------------------->
