# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Degraded mode management for the application pipeline.

This module defines the logic for degraded mode: when a command can be
executed partially (some steps skipped), when it must be blocked entirely,
and how to evaluate the criticality of an action in degraded mode.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from omega_fire.core.capability_registry import CapabilityRegistry
from omega_fire.core.enums import CapabilityStatus
from omega_fire.application.pipeline.planner import ExecutionPlan
from omega_fire.application.exceptions import DegradedModeError


class ActionCriticality(Enum):
    """Criticality level of an action.
    
    Determines whether the action can be executed in degraded mode.
    """
    LOW = "low"           # Can be skipped or delayed
    MEDIUM = "medium"     # Should execute but can be partial
    HIGH = "high"         # Must execute fully or not at all
    CRITICAL = "critical" # Must execute fully, block if degraded


@dataclass
class DegradedModePolicy:
    """Policy for degraded mode execution.
    
    Defines which actions are allowed in degraded mode and under what conditions.
    """
    allow_degraded_by_default: bool = False
    criticality_overrides: dict[str, ActionCriticality] = field(default_factory=dict)
    blocked_capabilities: list[str] = field(default_factory=list)
    warning_threshold: int = 2  # Number of missing capabilities before warning
    
    def get_criticality(self, command_name: str) -> ActionCriticality:
        """Get the criticality level for a command.
        
        Args:
            command_name: Name of the command
        
        Returns:
            ActionCriticality level
        """
        return self.criticality_overrides.get(
            command_name,
            ActionCriticality.MEDIUM if self.allow_degraded_by_default else ActionCriticality.HIGH
        )
    
    def is_capability_blocked(self, capability_id: str) -> bool:
        """Check if a capability is explicitly blocked.
        
        Args:
            capability_id: ID of the capability
        
        Returns:
            True if the capability is blocked
        """
        return capability_id in self.blocked_capabilities


@dataclass
class DegradedModeAssessment:
    """Assessment of whether a command can run in degraded mode.
    
    Contains the decision (allowed/blocked), the reason, and metadata
    about missing capabilities.
    """
    allowed: bool
    command_name: str
    criticality: ActionCriticality
    missing_capabilities: list[str] = field(default_factory=list)
    reason: Optional[str] = None
    warnings: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert the assessment to a dictionary.
        
        Returns:
            Dictionary representation
        """
        return {
            "allowed": self.allowed,
            "command_name": self.command_name,
            "criticality": self.criticality.value,
            "missing_capabilities": self.missing_capabilities,
            "reason": self.reason,
            "warnings": self.warnings,
        }


class DegradedModeManager:
    """Manages degraded mode decisions for the pipeline.
    
    This class evaluates whether a command can be executed in degraded mode
    based on the policy, criticality, and missing capabilities.
    """
    
    def __init__(
        self,
        registry: CapabilityRegistry,
        policy: Optional[DegradedModePolicy] = None,
    ):
        """Initialize the degraded mode manager.
        
        Args:
            registry: The capability registry to query
            policy: Optional policy for degraded mode (uses default if None)
        """
        self._registry = registry
        self._policy = policy or DegradedModePolicy()
    
    def assess(
        self,
        plan: ExecutionPlan,
    ) -> DegradedModeAssessment:
        """Assess whether a command can run in degraded mode.
        
        This method evaluates the execution plan, checks missing capabilities,
        and determines if the command can proceed in degraded mode.
        
        Args:
            plan: The execution plan to assess
        
        Returns:
            DegradedModeAssessment with the decision
        """
        # Get criticality
        criticality = self._policy.get_criticality(plan.command_name)
        
        # Collect missing capabilities
        missing_caps = []
        for step, caps in plan.skipped_steps:
            missing_caps.extend(caps)
        missing_caps = list(set(missing_caps))  # Deduplicate
        
        # Check for blocked capabilities
        blocked_caps = [cap for cap in missing_caps if self._policy.is_capability_blocked(cap)]
        
        # Build warnings
        warnings = []
        if len(missing_caps) >= self._policy.warning_threshold:
            warnings.append(
                f"Multiple capabilities missing ({len(missing_caps)}): {', '.join(missing_caps)}"
            )
        
        # Decision logic
        if not missing_caps:
            # No missing capabilities — not in degraded mode
            return DegradedModeAssessment(
                allowed=True,
                command_name=plan.command_name,
                criticality=criticality,
                missing_capabilities=[],
                reason="All capabilities available",
                warnings=warnings,
            )
        
        if blocked_caps:
            # Blocked capabilities — cannot proceed
            return DegradedModeAssessment(
                allowed=False,
                command_name=plan.command_name,
                criticality=criticality,
                missing_capabilities=missing_caps,
                reason=f"Blocked capabilities: {', '.join(blocked_caps)}",
                warnings=warnings,
            )
        
        if criticality == ActionCriticality.CRITICAL:
            # Critical actions cannot run in degraded mode
            return DegradedModeAssessment(
                allowed=False,
                command_name=plan.command_name,
                criticality=criticality,
                missing_capabilities=missing_caps,
                reason=f"Command '{plan.command_name}' is critical and cannot run in degraded mode",
                warnings=warnings,
            )
        
        if criticality == ActionCriticality.HIGH and not self._policy.allow_degraded_by_default:
            # High criticality with no degraded mode allowed
            return DegradedModeAssessment(
                allowed=False,
                command_name=plan.command_name,
                criticality=criticality,
                missing_capabilities=missing_caps,
                reason=f"Command '{plan.command_name}' requires all capabilities",
                warnings=warnings,
            )
        
        # Medium or Low criticality, or degraded mode allowed — can proceed
        return DegradedModeAssessment(
            allowed=True,
            command_name=plan.command_name,
            criticality=criticality,
            missing_capabilities=missing_caps,
            reason="Partial execution allowed",
            warnings=warnings,
        )
    
    def can_execute(
        self,
        plan: ExecutionPlan,
    ) -> bool:
        """Check if a command can execute (possibly in degraded mode).
        
        Args:
            plan: The execution plan to check
        
        Returns:
            True if the command can execute
        """
        assessment = self.assess(plan)
        return assessment.allowed
    
    def must_block(
        self,
        plan: ExecutionPlan,
    ) -> bool:
        """Check if a command must be blocked (cannot run even in degraded mode).
        
        Args:
            plan: The execution plan to check
        
        Returns:
            True if the command must be blocked
        """
        assessment = self.assess(plan)
        return not assessment.allowed
    
    def get_warnings(
        self,
        plan: ExecutionPlan,
    ) -> list[str]:
        """Get warnings for a command execution.
        
        Args:
            plan: The execution plan to assess
        
        Returns:
            List of warning messages
        """
        assessment = self.assess(plan)
        return assessment.warnings
    
    def validate_and_raise(
        self,
        plan: ExecutionPlan,
    ) -> None:
        """Validate the plan and raise DegradedModeError if blocked.
        
        Args:
            plan: The execution plan to validate
        
        Raises:
            DegradedModeError: If the command cannot execute
        """
        assessment = self.assess(plan)
        if not assessment.allowed:
            raise DegradedModeError(
                action_name=plan.command_name,
                reason=assessment.reason or "Command blocked in degraded mode",
            )


def create_default_policy() -> DegradedModePolicy:
    """Create a default degraded mode policy.
    
    Returns:
        DegradedModePolicy with sensible defaults
    """
    return DegradedModePolicy(
        allow_degraded_by_default=False,
        criticality_overrides={
            "ban_ip": ActionCriticality.HIGH,
            "unban_ip": ActionCriticality.MEDIUM,
            "sync_backends": ActionCriticality.CRITICAL,
            "export_report": ActionCriticality.LOW,
        },
        blocked_capabilities=[],
        warning_threshold=2,
    )


def assess_degraded_mode(
    plan: ExecutionPlan,
    registry: CapabilityRegistry,
    policy: Optional[DegradedModePolicy] = None,
) -> DegradedModeAssessment:
    """Convenience function to assess degraded mode.
    
    This function creates a DegradedModeManager and assesses the plan in one call.
    
    Args:
        plan: The execution plan to assess
        registry: The capability registry to query
        policy: Optional policy for degraded mode
    
    Returns:
        DegradedModeAssessment with the decision
    """
    manager = DegradedModeManager(registry, policy)
    return manager.assess(plan)

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Gestion du mode dégradé. Ce composant définit la logique de décision pour le mode dégradé : quand une commande peut être exécutée partiellement (certains steps ignorés), quand elle doit être bloquée complètement, et comment évaluer la criticité d'une action en mode dégradé.
# Pourquoi dans application/pipeline/ (charte) :
# - C'est une logique d'orchestration qui influence l'exécution du pipeline
# - Dépend de core/capability_registry.py (contrat interne)
# - Utilise les exceptions de application/exceptions.py
# - Ne dépend pas de infrastructure/ (pas d'exécution système)
# -  Ne dépend pas de domain/ (pas de logique métier)
# - Testable en mémoire pure
# Ce qu'il ne contient PAS (règles projet) :
# ❌ Pas d'import depuis infrastructure/ (pas de backend, pas de probe)
# ❌ Pas d'import depuis interfaces/ (pas de rendu)
# ❌ Pas d'import depuis domain/ (pas de logique métier)
# ❌ Pas de subprocess, sqlite3, rich — aucun I/O
# Points clés :
# - ActionCriticality : enum des niveaux de criticité (LOW, MEDIUM, HIGH, CRITICAL)
# - DegradedModePolicy : politique de mode dégradé (allow_degraded_by_default, overrides, blocked_capabilities)
# - DegradedModeAssessment : résultat de l'évaluation (allowed/blocked, reason, warnings)
# - DegradedModeManager : classe principale qui évalue si une commande peut s'exécuter en mode dégradé
# - assess() : méthode principale qui prend la décision basée sur la criticité et les capacités manquantes
# -Logique de décision :
#   - Pas de capacités manquantes → allowed
#   - Capacités bloquées → blocked
#   - Criticité CRITICAL → blocked
#   - Criticité HIGH sans allow_degraded → blocked
#   - Criticité MEDIUM/LOW ou allow_degraded → allowed
# - create_default_policy() : factory pour une politique par défaut avec des overrides pour les commandes courantes
# - assess_degraded_mode() : fonction de convenance pour évaluer en un appel
# - Aucune dépendance externe : utilise uniquement core/capability_registry.py et application/exceptions.py
# - Aucun I/O : ne lit ni n'écrit aucun fichier
# Comment il sera utilisé (aperçu) :
# - application/pipeline/executor.py appellera DegradedModeManager.validate_and_raise() avant l'exécution
# - application/commands/ban_ip.py définira sa criticité via la politique
# - interfaces/cli/actions.py affichera les warnings via get_warnings()
# - Les tests mockeront le CapabilityRegistry pour simuler différents scénarios de mode dégradé
#---------------------------------------------------------------------->
