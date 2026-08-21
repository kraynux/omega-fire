# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Pipeline planner.

This module decomposes a command into execution steps, checks required
capabilities for each step, and returns an optimized execution plan.
It removes steps with missing capabilities and can activate degraded
mode if partial execution is allowed.
"""
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from omega_fire.core.capability_registry import CapabilityRegistry
from omega_fire.core.enums import CapabilityStatus
from omega_fire.application.pipeline.guards.capability_guard import (
    is_capability_available,
    get_unavailable_capabilities,
)


@dataclass
class PipelineStep:
    """A single step in the execution pipeline.
    
    Each step has a name, a function to execute, and optional capabilities
    that must be available for the step to run.
    """
    name: str
    execute: Callable[[], Any]
    requires: list[str] = field(default_factory=list)
    rollback: Optional[Callable[[], Any]] = None
    skip_on_missing_capability: bool = False
    
    def can_execute(self, registry: CapabilityRegistry, allow_degraded: bool = False) -> bool:
        """Check if this step can execute given current capabilities.
        
        Args:
            registry: The capability registry to query
            allow_degraded: If True, allow DEGRADED capabilities
        
        Returns:
            True if all required capabilities are available
        """
        if not self.requires:
            return True
        
        return all(
            is_capability_available(cap, registry, allow_degraded)
            for cap in self.requires
        )
    
    def get_missing_capabilities(self, registry: CapabilityRegistry) -> list[str]:
        """Get the list of missing capabilities for this step.
        
        Args:
            registry: The capability registry to query
        
        Returns:
            List of missing capability identifiers
        """
        if not self.requires:
            return []
        
        return [
            cap for cap in self.requires
            if not is_capability_available(cap, registry)
        ]


@dataclass
class ExecutionPlan:
    """The result of planning a command execution.
    
    Contains the list of steps to execute, steps that were skipped
    due to missing capabilities, and metadata about the plan.
    """
    command_name: str
    steps: list[PipelineStep] = field(default_factory=list)
    skipped_steps: list[tuple[PipelineStep, list[str]]] = field(default_factory=list)
    degraded_mode: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def total_steps(self) -> int:
        """Get the total number of steps (executed + skipped)."""
        return len(self.steps) + len(self.skipped_steps)
    
    def has_steps(self) -> bool:
        """Check if there are any steps to execute."""
        return len(self.steps) > 0
    
    def get_skipped_reasons(self) -> dict[str, list[str]]:
        """Get a mapping of skipped step names to missing capabilities.
        
        Returns:
            Dictionary mapping step name to list of missing capabilities
        """
        return {
            step.name: missing_caps
            for step, missing_caps in self.skipped_steps
        }


class PipelinePlanner:
    """Plans command execution by decomposing into steps.
    
    This class takes a command definition, checks capabilities,
    and produces an ExecutionPlan with the steps that can be executed.
    """
    
    def __init__(
        self,
        registry: CapabilityRegistry,
        allow_degraded: bool = False,
        allow_partial_execution: bool = False,
    ):
        """Initialize the planner.
        
        Args:
            registry: The capability registry to query
            allow_degraded: If True, allow DEGRADED capabilities
            allow_partial_execution: If True, allow execution even if some
                                     steps are skipped (degraded mode)
        """
        self._registry = registry
        self._allow_degraded = allow_degraded
        self._allow_partial_execution = allow_partial_execution
    
    def plan(
        self,
        command_name: str,
        steps: list[PipelineStep],
        metadata: Optional[dict[str, Any]] = None,
    ) -> ExecutionPlan:
        """Plan the execution of a command.
        
        This method analyzes each step, checks required capabilities,
        and separates steps into executable and skipped.
        
        Args:
            command_name: Name of the command being planned
            steps: List of steps to execute
            metadata: Optional metadata to attach to the plan
        
        Returns:
            ExecutionPlan with executable and skipped steps
        
        Raises:
            ValueError: If no steps are provided
        """
        if not steps:
            raise ValueError(f"Command '{command_name}' has no steps defined")
        
        executable_steps: list[PipelineStep] = []
        skipped_steps: list[tuple[PipelineStep, list[str]]] = []
        
        for step in steps:
            missing_caps = step.get_missing_capabilities(self._registry)
            
            if not missing_caps:
                # All capabilities available — step can execute
                executable_steps.append(step)
            elif step.skip_on_missing_capability:
                # Step can be skipped — add to skipped list
                skipped_steps.append((step, missing_caps))
            else:
                # Step cannot be skipped — this is a problem
                # For now, we still skip it but mark the plan as degraded
                skipped_steps.append((step, missing_caps))
        
        # Determine if we're in degraded mode
        degraded_mode = len(skipped_steps) > 0 and self._allow_partial_execution
        
        return ExecutionPlan(
            command_name=command_name,
            steps=executable_steps,
            skipped_steps=skipped_steps,
            degraded_mode=degraded_mode,
            metadata=metadata or {},
        )
    
    def validate_plan(self, plan: ExecutionPlan) -> list[str]:
        """Validate an execution plan.
        
        This method checks if the plan is valid and can be executed.
        It returns a list of validation errors (empty if valid).
        
        Args:
            plan: The execution plan to validate
        
        Returns:
            List of validation error messages
        """
        errors = []
        
        # Check if there are any executable steps
        if not plan.has_steps():
            errors.append(
                f"Command '{plan.command_name}' has no executable steps. "
                f"All steps were skipped due to missing capabilities."
            )
        
        # Check if degraded mode is allowed
        if plan.degraded_mode and not self._allow_partial_execution:
            errors.append(
                f"Command '{plan.command_name}' requires partial execution, "
                f"but partial execution is not allowed."
            )
        
        return errors
    
    def is_plan_valid(self, plan: ExecutionPlan) -> bool:
        """Check if an execution plan is valid.
        
        Args:
            plan: The execution plan to check
        
        Returns:
            True if the plan is valid and can be executed
        """
        return len(self.validate_plan(plan)) == 0
    
    def get_execution_summary(self, plan: ExecutionPlan) -> dict[str, Any]:
        """Get a summary of the execution plan.
        
        Args:
            plan: The execution plan to summarize
        
        Returns:
            Dictionary with plan summary
        """
        return {
            "command": plan.command_name,
            "total_steps": plan.total_steps(),
            "executable_steps": len(plan.steps),
            "skipped_steps": len(plan.skipped_steps),
            "degraded_mode": plan.degraded_mode,
            "skipped_reasons": plan.get_skipped_reasons(),
        }


def create_step(
    name: str,
    execute: Callable[[], Any],
    requires: Optional[list[str]] = None,
    rollback: Optional[Callable[[], Any]] = None,
    skip_on_missing_capability: bool = False,
) -> PipelineStep:
    """Factory function to create a PipelineStep.
    
    This is a convenience function for creating steps with a cleaner syntax.
    
    Args:
        name: Step name
        execute: Function to execute
        requires: List of required capabilities
        rollback: Optional rollback function
        skip_on_missing_capability: If True, skip step if capabilities are missing
    
    Returns:
        PipelineStep object
    """
    return PipelineStep(
        name=name,
        execute=execute,
        requires=requires or [],
        rollback=rollback,
        skip_on_missing_capability=skip_on_missing_capability,
    )


def plan_command(
    command_name: str,
    steps: list[PipelineStep],
    registry: CapabilityRegistry,
    allow_degraded: bool = False,
    allow_partial_execution: bool = False,
    metadata: Optional[dict[str, Any]] = None,
) -> ExecutionPlan:
    """Convenience function to plan a command execution.
    
    This function creates a PipelinePlanner and plans the command in one call.
    
    Args:
        command_name: Name of the command
        steps: List of steps to execute
        registry: The capability registry to query
        allow_degraded: If True, allow DEGRADED capabilities
        allow_partial_execution: If True, allow partial execution
        metadata: Optional metadata to attach to the plan
    
    Returns:
        ExecutionPlan with executable and skipped steps
    """
    planner = PipelinePlanner(
        registry=registry,
        allow_degraded=allow_degraded,
        allow_partial_execution=allow_partial_execution,
    )
    return planner.plan(command_name, steps, metadata)

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Planificateur du pipeline. Ce composant reçoit une commande (ex: BanIPCommand), la décompose en steps d'exécution, vérifie les capacités requises pour chaque step, et retourne un plan d'exécution optimisé. Il retire les steps dont les capacités sont manquantes et peut activer le mode dégradé si nécessaire.
#  Pourquoi dans application/pipeline/ (charte) :
# - C'est la logique d'orchestration du pipeline
# - Dépend de core/capability_registry.py (contrat interne)
# - Utilise les exceptions de application/exceptions.py
# - Ne dépend pas de infrastructure/ (pas d'exécution réelle)
# - Ne dépend pas de domain/ (pas de logique métier)
# - Testable en mémoire pure
# Ce qu'il ne contient PAS (règles projet) :
# ❌ Pas d'import depuis infrastructure/ (pas de backend, pas de probe)
# ❌ Pas d'import depuis interfaces/ (pas de rendu)
# ❌ Pas d'import depuis domain/ (pas de logique métier)
# ❌ Pas de subprocess, sqlite3, rich — aucun I/O
# Points clés :
# - PipelineStep : représente un step avec nom, fonction d'exécution, capacités requises, rollback optionnel
# - ExecutionPlan : résultat du planning avec steps exécutables, steps ignorés, mode dégradé
# - PipelinePlanner : classe principale qui décompose une commande en steps et vérifie les capacités
# - plan() : méthode principale qui analyse chaque step et sépare exécutable/ignoré
# - validate_plan() : vérifie si le plan est valide (au moins un step exécutable)
# - create_step() : factory function pour créer des steps avec une syntaxe plus propre
# - plan_command() : fonction de convenance pour planner en un appel
# - Mode dégradé : activé si des steps sont ignorés et allow_partial_execution=True
# - Aucune dépendance externe : utilise uniquement core/capability_registry.py et application/pipeline/guards/capability_guard.py
# - Aucun I/O : ne lit ni n'écrit aucun fichier, n'exécute rien
# Comment il sera utilisé (aperçu) :
# - application/commands/ban_ip.py définira une liste de PipelineStep (validate, execute, audit)
# - application/pipeline/executor.py recevra l'ExecutionPlan et exécutera les steps
# - interfaces/cli/actions.py affichera le résumé du plan avant exécution
# - Les tests mockeront le CapabilityRegistry pour simuler des capacités manquantes
#---------------------------------------------------------------------->
