# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Pipeline executor.

This module executes the steps of an ExecutionPlan in order, calling
guards, hooks, and managing rollback on failure. It is the central
orchestrator of the application pipeline.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional
from omega_fire.core.capability_registry import CapabilityRegistry
from omega_fire.application.pipeline.planner import ExecutionPlan, PipelineStep
from omega_fire.application.pipeline.guards.capability_guard import check_capabilities
from omega_fire.application.pipeline.guards.permission_guard import PermissionGuard
from omega_fire.application.pipeline.hooks.audit_hook import AuditHook
from omega_fire.application.exceptions import (
    CapabilityUnavailableError,
    PermissionDeniedError,
    StepExecutionError,
    UseCaseExecutionError,
    RollbackError,
)


@dataclass
class ExecutionResult:
    """Result of a pipeline execution.
    
    Contains the outcome of the execution: success/failure, executed steps,
    failed steps, and any error information.
    """
    success: bool
    command_name: str
    executed_steps: list[str] = field(default_factory=list)
    failed_step: Optional[str] = None
    skipped_steps: list[str] = field(default_factory=list)
    error_message: Optional[str] = None
    error_details: dict[str, Any] = field(default_factory=dict)
    duration_seconds: float = 0.0
    degraded_mode: bool = False
    
    def to_dict(self) -> dict[str, Any]:
        """Convert the result to a dictionary.
        
        Returns:
            Dictionary representation of the result
        """
        return {
            "success": self.success,
            "command_name": self.command_name,
            "executed_steps": self.executed_steps,
            "failed_step": self.failed_step,
            "skipped_steps": self.skipped_steps,
            "error_message": self.error_message,
            "error_details": self.error_details,
            "duration_seconds": self.duration_seconds,
            "degraded_mode": self.degraded_mode,
        }


class PipelineExecutor:
    """Executes pipeline steps with guards, hooks, and rollback.
    
    This class takes an ExecutionPlan and executes each step in order,
    checking capabilities and permissions before execution, recording
    events via hooks, and triggering rollback on failure.
    """
    
    def __init__(
        self,
        registry: CapabilityRegistry,
        audit_hook: Optional[AuditHook] = None,
        permission_guard: Optional[PermissionGuard] = None,
        allow_degraded: bool = False,
    ):
        """Initialize the executor.
        
        Args:
            registry: The capability registry to query
            audit_hook: Optional audit hook for recording events
            permission_guard: Optional permission guard for checking rights
            allow_degraded: If True, allow execution in degraded mode
        """
        self._registry = registry
        self._audit_hook = audit_hook
        self._permission_guard = permission_guard
        self._allow_degraded = allow_degraded
    
    def execute(
        self,
        plan: ExecutionPlan,
        required_permissions: Optional[list[str]] = None,
    ) -> ExecutionResult:
        """Execute the pipeline plan.
        
        This method executes each step in order, checking guards before
        each step, recording events via hooks, and triggering rollback
        on failure.
        
        Args:
            plan: The execution plan to execute
            required_permissions: Optional list of required permissions
        
        Returns:
            ExecutionResult with the outcome
        """
        start_time = datetime.now()
        executed_steps: list[str] = []
        skipped_steps = [step.name for step, _ in plan.skipped_steps]
        
        # Record command started
        if self._audit_hook:
            self._audit_hook.record_command_started(
                command_name=plan.command_name,
                details={"total_steps": len(plan.steps), "skipped_steps": len(plan.skipped_steps)},
            )
        
        # Check permissions (if guard provided)
        if self._permission_guard and required_permissions:
            try:
                self._permission_guard.guard(
                    required_permissions=required_permissions,
                    action_name=plan.command_name,
                )
            except PermissionDeniedError as e:
                if self._audit_hook:
                    self._audit_hook.record_permission_denied(
                        command_name=plan.command_name,
                        required_permission=str(e.required_permission),
                        reason=str(e.reason),
                    )
                return ExecutionResult(
                    success=False,
                    command_name=plan.command_name,
                    executed_steps=executed_steps,
                    skipped_steps=skipped_steps,
                    error_message=str(e),
                    error_details={"type": "permission_denied"},
                    duration_seconds=(datetime.now() - start_time).total_seconds(),
                    degraded_mode=plan.degraded_mode,
                )
        
        # Check if we're in degraded mode
        if plan.degraded_mode and not self._allow_degraded:
            error_msg = f"Command '{plan.command_name}' requires degraded mode, but it's not allowed"
            if self._audit_hook:
                self._audit_hook.record_command_failed(
                    command_name=plan.command_name,
                    error_message=error_msg,
                )
            return ExecutionResult(
                success=False,
                command_name=plan.command_name,
                executed_steps=executed_steps,
                skipped_steps=skipped_steps,
                error_message=error_msg,
                error_details={"type": "degraded_mode_not_allowed"},
                duration_seconds=(datetime.now() - start_time).total_seconds(),
                degraded_mode=plan.degraded_mode,
            )
        
        # Record degraded mode activation
        if plan.degraded_mode and self._audit_hook:
            skipped_caps = []
            for step, missing in plan.skipped_steps:
                skipped_caps.extend(missing)
            self._audit_hook.record_degraded_mode_activated(
                command_name=plan.command_name,
                skipped_capabilities=list(set(skipped_caps)),
            )
        
        # Execute steps
        for step in plan.steps:
            # Check capabilities for this step
            try:
                check_capabilities(
                    capability_ids=step.requires,
                    registry=self._registry,
                    allow_degraded=self._allow_degraded,
                )
            except CapabilityUnavailableError as e:
                if self._audit_hook:
                    self._audit_hook.record_capability_missing(
                        command_name=plan.command_name,
                        capability_id=e.capability_id,
                        status=e.status,
                        reason=e.reason,
                    )
                    self._audit_hook.record_step_skipped(
                        command_name=plan.command_name,
                        step_name=step.name,
                        reason=str(e),
                    )
                
                # If step can be skipped, continue; otherwise fail
                if step.skip_on_missing_capability:
                    skipped_steps.append(step.name)
                    continue
                else:
                    return ExecutionResult(
                        success=False,
                        command_name=plan.command_name,
                        executed_steps=executed_steps,
                        failed_step=step.name,
                        skipped_steps=skipped_steps,
                        error_message=str(e),
                        error_details={"type": "capability_unavailable", "step": step.name},
                        duration_seconds=(datetime.now() - start_time).total_seconds(),
                        degraded_mode=plan.degraded_mode,
                    )
            
            # Execute the step
            try:
                step.execute()
                executed_steps.append(step.name)
                
                if self._audit_hook:
                    self._audit_hook.record_step_executed(
                        command_name=plan.command_name,
                        step_name=step.name,
                    )
            except Exception as e:
                # Step failed — trigger rollback
                error_msg = f"Step '{step.name}' failed: {e}"
                
                if self._audit_hook:
                    self._audit_hook.record_step_failed(
                        command_name=plan.command_name,
                        step_name=step.name,
                        error_message=error_msg,
                    )
                    self._audit_hook.record_rollback_triggered(
                        command_name=plan.command_name,
                        step_name=step.name,
                        reason=error_msg,
                    )
                
                # Attempt rollback
                rollback_success = self._rollback(plan, executed_steps)
                
                if rollback_success and self._audit_hook:
                    self._audit_hook.record_rollback_completed(
                        command_name=plan.command_name,
                    )
                elif not rollback_success and self._audit_hook:
                    self._audit_hook.record_rollback_failed(
                        command_name=plan.command_name,
                        error_message="Rollback failed for one or more steps",
                    )
                
                return ExecutionResult(
                    success=False,
                    command_name=plan.command_name,
                    executed_steps=executed_steps,
                    failed_step=step.name,
                    skipped_steps=skipped_steps,
                    error_message=error_msg,
                    error_details={"type": "step_execution_failed", "step": step.name, "rollback_success": rollback_success},
                    duration_seconds=(datetime.now() - start_time).total_seconds(),
                    degraded_mode=plan.degraded_mode,
                )
        
        # All steps succeeded
        if self._audit_hook:
            self._audit_hook.record_command_completed(
                command_name=plan.command_name,
                details={"executed_steps": len(executed_steps)},
            )
        
        return ExecutionResult(
            success=True,
            command_name=plan.command_name,
            executed_steps=executed_steps,
            skipped_steps=skipped_steps,
            duration_seconds=(datetime.now() - start_time).total_seconds(),
            degraded_mode=plan.degraded_mode,
        )
    
    def _rollback(self, plan: ExecutionPlan, executed_steps: list[str]) -> bool:
        """Attempt to rollback executed steps in reverse order.
        
        Args:
            plan: The execution plan
            executed_steps: List of step names that were executed
        
        Returns:
            True if all rollbacks succeeded, False otherwise
        """
        # Build a map of step name to step object
        step_map = {step.name: step for step in plan.steps}
        
        # Rollback in reverse order
        for step_name in reversed(executed_steps):
            step = step_map.get(step_name)
            if step and step.rollback:
                try:
                    step.rollback()
                except Exception as e:
                    # Rollback failed — log but continue
                    if self._audit_hook:
                        self._audit_hook.record_rollback_failed(
                            command_name=plan.command_name,
                            error_message=f"Rollback for step '{step_name}' failed: {e}",
                        )
                    return False
        
        return True


def execute_command(
    plan: ExecutionPlan,
    registry: CapabilityRegistry,
    audit_hook: Optional[AuditHook] = None,
    permission_guard: Optional[PermissionGuard] = None,
    required_permissions: Optional[list[str]] = None,
    allow_degraded: bool = False,
) -> ExecutionResult:
    """Convenience function to execute a command plan.
    
    This function creates a PipelineExecutor and executes the plan in one call.
    
    Args:
        plan: The execution plan to execute
        registry: The capability registry to query
        audit_hook: Optional audit hook for recording events
        permission_guard: Optional permission guard for checking rights
        required_permissions: Optional list of required permissions
        allow_degraded: If True, allow execution in degraded mode
    
    Returns:
        ExecutionResult with the outcome
    """
    executor = PipelineExecutor(
        registry=registry,
        audit_hook=audit_hook,
        permission_guard=permission_guard,
        allow_degraded=allow_degraded,
    )
    return executor.execute(plan, required_permissions)

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Exécuteur du pipeline. Ce composant prend un ExecutionPlan (généré par le planner), exécute les steps dans l'ordre, appelle les guards (capacité, permission), déclenche les hooks (audit), et gère le rollback en cas d'erreur. C'est le cœur de l'orchestration applicative.
# Pourquoi dans application/pipeline/ (charte) :
# - C'est l'orchestrateur central du pipeline
# - Utilise les guards, hooks, et exceptions de application/
# - Dépend de core/capability_registry.py (contrat interne)
# - Ne dépend pas de infrastructure/ (pas d'exécution système directe)
# - Ne dépend pas de domain/ (pas de logique métier)
# - Testable en mockant les steps et les capacités
# Ce qu'il ne contient PAS (règles projet) :
# ❌ Pas d'import depuis infrastructure/ (pas de backend, pas de subprocess)
# ❌ Pas d'import depuis interfaces/ (pas de rendu)
# ❌ Pas d'import depuis domain/ (pas de logique métier)
# ❌ Pas de subprocess, sqlite3, rich — aucun I/O
# Points clés :
# - ExecutionResult : résultat de l'exécution avec succès/échec, steps exécutés, step échoué, message d'erreur
# - PipelineExecutor : classe principale qui exécute les steps dans l'ordre
# - execute() : méthode principale qui orchestre l'exécution complète
# - Vérification des permissions : appelle PermissionGuard avant l'exécution
# - Vérification des capacités : appelle check_capabilities() avant chaque step
# - Exécution des steps : appelle step.execute() pour chaque step
# - Gestion du rollback : en cas d'échec, appelle step.rollback() dans l'ordre inverse
# - Hooks d'audit : enregistre tous les événements (command_started, step_executed, rollback_triggered, etc.)
# - Mode dégradé : activé si des steps sont ignorés et allow_degraded=True
# - execute_command() : fonction de convenance pour exécuter en un appel
# - Aucune dépendance externe : utilise uniquement les modules de application/pipeline/ et core/
# - Aucun I/O : ne lit ni n'écrit aucun fichier, n'appelle aucun système
# Comment il sera utilisé (aperçu) :
# - application/commands/ban_ip.py construira un ExecutionPlan avec les steps (validate, execute, audit)
# - interfaces/cli/actions.py appellera execute_command() pour exécuter la commande
# - Les tests mockeront les steps et le CapabilityRegistry pour simuler différents scénarios
#---------------------------------------------------------------------->
