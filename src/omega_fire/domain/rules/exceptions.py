# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Rules domain exceptions.

Pure domain exceptions for the firewall rules subdomain.
These express business rule violations, not technical failures.
They are caught by application/ and translated into Results
or user-facing messages.
"""


class RulesError(Exception):
    """Base exception for rules domain.
    
    All domain-specific exceptions for firewall rules inherit from this.
    """
    pass


class InvalidRuleError(RulesError):
    """Raised when a firewall rule is structurally invalid.
    
    Examples: invalid protocol, invalid port range, invalid CIDR,
    missing required field, action incompatible with chain.
    """
    def __init__(self, rule_description: str, reason: str):
        self.rule_description = rule_description
        self.reason = reason
        super().__init__(f"Invalid rule ({rule_description}): {reason}")


class ConflictingRuleError(RulesError):
    """Raised when a new rule conflicts with an existing one.
    
    Examples: duplicate rule, overlapping port ranges with same
    priority, contradictory actions on the same traffic.
    """
    def __init__(self, new_rule: str, existing_rule: str, reason: str):
        self.new_rule = new_rule
        self.existing_rule = existing_rule
        self.reason = reason
        super().__init__(
            f"Rule conflict: {new_rule} conflicts with {existing_rule} — {reason}"
        )


class RuleNotFoundError(RulesError):
    """Raised when attempting to delete or modify a non-existent rule."""
    def __init__(self, rule_id: int):
        self.rule_id = rule_id
        super().__init__(f"Rule with ID {rule_id} not found")


class InvalidPolicyError(RulesError):
    """Raised when a firewall policy cannot be applied.

    Examples: policy requires a backend that is missing,
    policy parameters are incompatible with current state.
    """
    def __init__(self, policy_name: str, reason: str):
        self.policy_name = policy_name
        self.reason = reason
        super().__init__(f"Invalid policy '{policy_name}': {reason}")


class PolicyNotFoundError(RulesError):
    """Raised when apply_policy() is given a name matching no known preset.

    Distinct from InvalidPolicyError: this is "no policy by that name
    exists", not "the policy exists but can't be applied right now".
    """
    def __init__(self, policy_name: str, reason: str):
        self.policy_name = policy_name
        self.reason = reason
        super().__init__(f"Policy '{policy_name}' not found: {reason}")


class ChainError(RulesError):
    """Raised when a chain operation is invalid.
    
    Examples: creating a rule in a non-existent chain,
    invalid chain name, chain type mismatch.
    """
    def __init__(self, chain_name: str, reason: str):
        self.chain_name = chain_name
        self.reason = reason
        super().__init__(f"Chain error on '{chain_name}': {reason}")

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit les exceptions métier spécifiques au sous-domaine règles firewall. Ces exceptions expriment des violations de règles métier (règle invalide, conflit entre règles, politique inapplicable), pas des pannes techniques.
# Pourquoi dans domain/ (charte) :
# - C'est une erreur métier : violation d'un invariant du domaine (ex: règle incohérente)
# - Aucune dépendance externe (hérite juste de Exception)
# - Testable sans aucun backend réel
# - Sera capturée par application/ pour être traduite en Result ou message utilisateur
# Ce qu'il ne contient PAS (règles projet)
# ❌ Pas d'import depuis infrastructure/ (pas d'erreur technique)
# ❌ Pas d'import depuis interfaces/ (pas de message utilisateur)
# ❌ Pas d'import depuis application/ (pas de logique de cas d'usage)
# Points clés :
# - Hiérarchie claire : toutes les exceptions héritent de RulesError
# - Contexte riche : chaque exception stocke les données pertinentes (règle, policy, chain)
# - 6 exceptions ciblées :
#   - InvalidRuleError : règle mal formée
#   - ConflictingRuleError : conflit avec une règle existante
#   - RuleNotFoundError : règle inexistante
#   - InvalidPolicyError : politique inapplicable
#   - PolicyNotFoundError : apply_policy() sur un nom sans correspondance (FirewallPort.apply_policy)
#   - ChainError : problème de chaîne (input/output/forward)
# - Aucune dépendance : ces exceptions ne savent rien de nftables, iptables, SQLite ou Rich
# Comment elles seront utilisées (aperçu) :
# domain/rules/service.py les lèvera quand une règle métier est violée
# application/commands/create_rule.py les capturera et les traduira en Result.fail()
# interfaces/cli/actions.py affichera le message à l'utilisateur
#---------------------------------------------------------------------->
