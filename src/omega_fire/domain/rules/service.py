# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Rules domain service.

Orchestrates business operations on firewall rules.
This service coordinates the domain modules (models, policies, presets)
and enforces business rules by raising domain exceptions.
"""
from typing import Optional
from omega_fire.domain.rules.models import (
    FirewallRule,
    RuleAction,
    RuleChain,
    RuleFamily,
    RuleProtocol,
    RuleSet,
)
from omega_fire.domain.rules.exceptions import (
    InvalidRuleError,
    ConflictingRuleError,
    RuleNotFoundError,
    InvalidPolicyError,
    ChainError,
)
from omega_fire.domain.rules.policies import (
    FirewallPolicy,
    PolicyType,
    get_policy,
    list_available_policies,
)
from omega_fire.domain.rules.presets import (
    get_preset,
    list_available_presets,
)


class RulesService:
    """Domain service for firewall rules operations.
    
    This service orchestrates business logic for creating, deleting,
    listing, and applying rules/policies/presets. It enforces business
    rules and raises domain exceptions when rules are violated.
    """
    
    def __init__(self, ruleset: Optional[RuleSet] = None):
        """Initialize the service with an optional ruleset.
        
        Args:
            ruleset: Existing ruleset. If None, creates an empty one.
        """
        self.ruleset = ruleset or RuleSet()
    
    def create_rule(
        self,
        backend: str,
        family: RuleFamily,
        table_name: str,
        chain: RuleChain,
        action: RuleAction,
        protocol: Optional[RuleProtocol] = None,
        port_start: Optional[int] = None,
        port_end: Optional[int] = None,
        source_cidr: Optional[str] = None,
        dest_cidr: Optional[str] = None,
        priority: int = 0,
        comment: Optional[str] = None,
    ) -> FirewallRule:
        """Create a new firewall rule.
        
        Business rules:
        - Port range must be valid (start <= end)
        - Port requires a protocol (TCP or UDP)
        - Rule must not conflict with existing rules
        
        Args:
            backend: Backend label ('nftables' or 'iptables')
            family: Address family (INET, IP, IP6)
            table_name: Netfilter table name
            chain: Chain (INPUT, OUTPUT, FORWARD)
            action: Action (ACCEPT, DROP, REJECT, LOG)
            protocol: Optional protocol (TCP, UDP, ICMP)
            port_start: Optional start port
            port_end: Optional end port
            source_cidr: Optional source CIDR
            dest_cidr: Optional destination CIDR
            priority: Rule priority (default: 0)
            comment: Optional comment
        
        Returns:
            The created FirewallRule
        
        Raises:
            InvalidRuleError: If the rule is structurally invalid
            ConflictingRuleError: If the rule conflicts with an existing one
        """
        # Validate port range
        if port_start is not None and port_end is not None:
            if port_start > port_end:
                raise InvalidRuleError(
                    f"port {port_start}-{port_end}",
                    "Port range is invalid (start > end)"
                )
        
        # Validate port requires protocol
        if port_start is not None and protocol is None:
            raise InvalidRuleError(
                f"port {port_start}",
                "Port specification requires a protocol (TCP or UDP)"
            )
        
        # Validate port range for ICMP
        if protocol == RuleProtocol.ICMP and (port_start is not None or port_end is not None):
            raise InvalidRuleError(
                f"ICMP with ports",
                "ICMP protocol does not support port specification"
            )
        
        # Create the rule
        rule = FirewallRule(
            backend=backend,
            family=family,
            table_name=table_name,
            chain=chain,
            protocol=protocol,
            port_start=port_start,
            port_end=port_end,
            source_cidr=source_cidr,
            dest_cidr=dest_cidr,
            action=action,
            priority=priority,
            comment=comment,
        )
        
        # Check for conflicts
        self._check_conflicts(rule)
        
        # Add to ruleset
        self.ruleset.add(rule)
        return rule
    
    def delete_rule(self, rule_id: int) -> FirewallRule:
        """Delete a rule by ID.
        
        Args:
            rule_id: ID of the rule to delete
        
        Returns:
            The deleted FirewallRule
        
        Raises:
            RuleNotFoundError: If the rule does not exist
        """
        removed = self.ruleset.remove(rule_id)
        if removed is None:
            raise RuleNotFoundError(rule_id)
        return removed
    
    def get_rule(self, rule_id: int) -> Optional[FirewallRule]:
        """Get a rule by ID.
        
        Args:
            rule_id: ID of the rule
        
        Returns:
            FirewallRule if found, None otherwise
        """
        for rule in self.ruleset.rules:
            if rule.rule_id == rule_id:
                return rule
        return None
    
    def list_rules(
        self,
        backend: Optional[str] = None,
        chain: Optional[RuleChain] = None,
        enabled_only: bool = False,
    ) -> list[FirewallRule]:
        """List rules with optional filters.
        
        Args:
            backend: Filter by backend
            chain: Filter by chain
            enabled_only: If True, only return enabled rules
        
        Returns:
            List of FirewallRule matching the filters
        """
        rules = self.ruleset.rules
        
        if backend:
            rules = [r for r in rules if r.backend == backend]
        if chain:
            rules = [r for r in rules if r.chain == chain]
        if enabled_only:
            rules = [r for r in rules if r.enabled]
        
        return rules
    
    def apply_policy(
        self,
        policy_type: PolicyType,
        backend: str = "nftables",
    ) -> FirewallPolicy:
        """Apply a predefined policy.
        
        Business rules:
        - Policy must be a known type
        - Policy rules are added to the ruleset
        
        Args:
            policy_type: Type of policy to apply
            backend: Target backend
        
        Returns:
            The applied FirewallPolicy
        
        Raises:
            InvalidPolicyError: If the policy type is unknown
        """
        try:
            policy = get_policy(policy_type, backend=backend)
        except ValueError as e:
            raise InvalidPolicyError(policy_type.value, str(e)) from e
        
        # Add all policy rules to the ruleset
        for rule in policy.rules:
            self.ruleset.add(rule)
        
        return policy
    
    def apply_preset(
        self,
        preset_name: str,
        backend: str = "nftables",
        **kwargs
    ) -> list[FirewallRule]:
        """Apply a predefined preset.
        
        Args:
            preset_name: Name of the preset
            backend: Target backend
            **kwargs: Additional arguments for the preset
        
        Returns:
            List of applied FirewallRule
        
        Raises:
            ValueError: If the preset name is unknown
        """
        result = get_preset(preset_name, backend=backend, **kwargs)
        
        # Handle single rule or list of rules
        if isinstance(result, FirewallRule):
            rules = [result]
        else:
            rules = result
        
        # Add all preset rules to the ruleset
        for rule in rules:
            self.ruleset.add(rule)
        
        return rules
    
    def list_available_policies(self) -> list[PolicyType]:
        """Return the list of all available policy types."""
        return list_available_policies()
    
    def list_available_presets(self) -> list[str]:
        """Return the list of all available preset names."""
        return list_available_presets()
    
    def count_rules(self) -> int:
        """Count total rules in the ruleset."""
        return len(self.ruleset.rules)
    
    def count_by_backend(self, backend: str) -> int:
        """Count rules for a specific backend."""
        return len(self.ruleset.get_by_backend(backend))
    
    def _check_conflicts(self, new_rule: FirewallRule) -> None:
        """Check if a new rule conflicts with existing rules.
        
        Business rules:
        - No exact duplicate rules (same backend, chain, protocol, ports, action)
        
        Args:
            new_rule: The rule to check
        
        Raises:
            ConflictingRuleError: If a conflict is detected
        """
        for existing in self.ruleset.rules:
            if self._rules_conflict(new_rule, existing):
                raise ConflictingRuleError(
                    self._rule_description(new_rule),
                    self._rule_description(existing),
                    "Duplicate rule detected"
                )
    
    def _rules_conflict(self, rule1: FirewallRule, rule2: FirewallRule) -> bool:
        """Check if two rules are exact duplicates."""
        return (
            rule1.backend == rule2.backend
            and rule1.family == rule2.family
            and rule1.table_name == rule2.table_name
            and rule1.chain == rule2.chain
            and rule1.protocol == rule2.protocol
            and rule1.port_start == rule2.port_start
            and rule1.port_end == rule2.port_end
            and rule1.source_cidr == rule2.source_cidr
            and rule1.dest_cidr == rule2.dest_cidr
            and rule1.action == rule2.action
        )
    
    def _rule_description(self, rule: FirewallRule) -> str:
        """Build a human-readable description of a rule."""
        parts = [
            f"backend={rule.backend}",
            f"chain={rule.chain.value}",
        ]
        if rule.protocol:
            parts.append(f"protocol={rule.protocol.value}")
        if rule.port_start is not None:
            parts.append(f"port={rule.get_port_display()}")
        if rule.source_cidr:
            parts.append(f"source={rule.source_cidr}")
        if rule.dest_cidr:
            parts.append(f"dest={rule.dest_cidr}")
        parts.append(f"action={rule.action.value}")
        return ", ".join(parts)

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Orchestration métier des opérations sur les règles firewall. Ce service coordonne les modules du domaine (models, policies, presets) et applique les règles métier (validation, détection de conflits). Il lève les exceptions métier quand une règle est violée.
# Pourquoi dans domain/ (charte) :
# - C'est la logique métier centrale du sous-domaine règles
# - Utilise uniquement les autres modules du domaine (models, policies, presets, exceptions)
# - Lève les exceptions métier définies dans exceptions.py
# - Aucune dépendance externe (pas de subprocess, sqlite3, rich)
# Ce qu'il ne contient PAS :
# ❌ Pas d'import depuis infrastructure/ (pas d'appel système, pas de DB)
# ❌ Pas d'import depuis application/ (pas de cas d'usage)
# ❌ Pas d'import depuis interfaces/ (pas de rendu)
# ❌ Pas de logique d'exécution (juste l'orchestration métier)
# Points clés :
# - Orchestration métier : coordonne models, policies, presets
# - Validation stricte : vérifie les règles métier (port range valide, port nécessite un protocole, etc.)
# - Détection de conflits : empêche les règles dupliquées
# - Exceptions métier : lève InvalidRuleError, ConflictingRuleError, RuleNotFoundError, InvalidPolicyError
# - Aucune dépendance externe : utilise uniquement les modules du domaine
# - Testable en mémoire : peut être testé sans aucun backend réel
# Comment il sera utilisé (aperçu) :
# - application/commands/create_rule.py instanciera RulesService et appellera create_rule()
# - application/commands/apply_policy.py appellera apply_policy() avec le type de politique
# - application/queries/list_rules.py appellera list_rules() avec les filtres
# - interfaces/cli/actions.py proposera les presets et politiques via list_available_presets() et list_available_policies()
#---------------------------------------------------------------------->
