# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Rules domain policies.

Pure domain logic for predefined firewall policies.
A policy is a named collection of rules applied as a batch
to configure the firewall according to a specific profile.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from omega_fire.domain.rules.models import (
    FirewallRule,
    RuleAction,
    RuleChain,
    RuleFamily,
    RuleProtocol,
    RuleSet,
)


class PolicyType(Enum):
    """Type of predefined firewall policy."""
    LOCAL = "local"
    STRICT = "strict"
    MAINTENANCE = "maintenance"
    MONITORING = "monitoring"


@dataclass
class FirewallPolicy:
    """A predefined firewall policy.
    
    A policy is a named collection of rules that can be applied
    as a batch to configure the firewall according to a profile.
    """
    policy_type: PolicyType
    name: str
    description: str
    rules: list[FirewallRule] = field(default_factory=list)
    backend: str = "nftables"
    
    def count_rules(self) -> int:
        """Return the number of rules in this policy."""
        return len(self.rules)
    
    def is_empty(self) -> bool:
        """Check if the policy has no rules."""
        return len(self.rules) == 0
    
    def to_ruleset(self) -> RuleSet:
        """Convert the policy rules into a RuleSet."""
        return RuleSet(rules=list(self.rules))


def build_local_policy(backend: str = "nftables") -> FirewallPolicy:
    """Build the LOCAL policy.
    
    Profile: Default local workstation.
    - Allow all outgoing traffic
    - Allow established/related incoming connections
    - Allow SSH (port 22) for remote access
    - Drop all other incoming traffic
    """
    rules = [
        FirewallRule(
            backend=backend,
            family=RuleFamily.INET,
            table_name="filter",
            chain=RuleChain.OUTPUT,
            action=RuleAction.ACCEPT,
            priority=0,
            comment="Allow all outgoing traffic",
        ),
        FirewallRule(
            backend=backend,
            family=RuleFamily.INET,
            table_name="filter",
            chain=RuleChain.INPUT,
            action=RuleAction.ACCEPT,
            priority=0,
            comment="Allow established/related connections",
        ),
        FirewallRule(
            backend=backend,
            family=RuleFamily.INET,
            table_name="filter",
            chain=RuleChain.INPUT,
            protocol=RuleProtocol.TCP,
            port_start=22,
            port_end=22,
            action=RuleAction.ACCEPT,
            priority=10,
            comment="Allow SSH",
        ),
        FirewallRule(
            backend=backend,
            family=RuleFamily.INET,
            table_name="filter",
            chain=RuleChain.INPUT,
            action=RuleAction.DROP,
            priority=100,
            comment="Drop all other incoming traffic",
        ),
    ]
    
    return FirewallPolicy(
        policy_type=PolicyType.LOCAL,
        name="Local Workstation",
        description="Allow outgoing, block incoming except SSH",
        rules=rules,
        backend=backend,
    )


def build_strict_policy(backend: str = "nftables") -> FirewallPolicy:
    """Build the STRICT policy.
    
    Profile: Strict firewall for production servers.
    - Allow all outgoing traffic
    - Allow established/related incoming connections
    - Allow SSH (22), HTTP (80), HTTPS (443)
    - Log dropped packets
    - Drop all other incoming traffic
    """
    rules = [
        FirewallRule(
            backend=backend,
            family=RuleFamily.INET,
            table_name="filter",
            chain=RuleChain.OUTPUT,
            action=RuleAction.ACCEPT,
            priority=0,
            comment="Allow all outgoing traffic",
        ),
        FirewallRule(
            backend=backend,
            family=RuleFamily.INET,
            table_name="filter",
            chain=RuleChain.INPUT,
            action=RuleAction.ACCEPT,
            priority=0,
            comment="Allow established/related connections",
        ),
        FirewallRule(
            backend=backend,
            family=RuleFamily.INET,
            table_name="filter",
            chain=RuleChain.INPUT,
            protocol=RuleProtocol.TCP,
            port_start=22,
            port_end=22,
            action=RuleAction.ACCEPT,
            priority=10,
            comment="Allow SSH",
        ),
        FirewallRule(
            backend=backend,
            family=RuleFamily.INET,
            table_name="filter",
            chain=RuleChain.INPUT,
            protocol=RuleProtocol.TCP,
            port_start=80,
            port_end=80,
            action=RuleAction.ACCEPT,
            priority=10,
            comment="Allow HTTP",
        ),
        FirewallRule(
            backend=backend,
            family=RuleFamily.INET,
            table_name="filter",
            chain=RuleChain.INPUT,
            protocol=RuleProtocol.TCP,
            port_start=443,
            port_end=443,
            action=RuleAction.ACCEPT,
            priority=10,
            comment="Allow HTTPS",
        ),
        FirewallRule(
            backend=backend,
            family=RuleFamily.INET,
            table_name="filter",
            chain=RuleChain.INPUT,
            action=RuleAction.LOG,
            priority=90,
            comment="Log dropped packets",
        ),
        FirewallRule(
            backend=backend,
            family=RuleFamily.INET,
            table_name="filter",
            chain=RuleChain.INPUT,
            action=RuleAction.DROP,
            priority=100,
            comment="Drop all other incoming traffic",
        ),
    ]
    
    return FirewallPolicy(
        policy_type=PolicyType.STRICT,
        name="Strict Production",
        description="Allow only SSH/HTTP/HTTPS, log and drop all other incoming",
        rules=rules,
        backend=backend,
    )


def build_maintenance_policy(backend: str = "nftables") -> FirewallPolicy:
    """Build the MAINTENANCE policy.
    
    Profile: Emergency maintenance mode.
    - Allow all outgoing traffic
    - Allow only SSH to maintain access
    - Drop all other incoming traffic
    - No logging (minimal overhead)
    """
    rules = [
        FirewallRule(
            backend=backend,
            family=RuleFamily.INET,
            table_name="filter",
            chain=RuleChain.OUTPUT,
            action=RuleAction.ACCEPT,
            priority=0,
            comment="Allow all outgoing traffic",
        ),
        FirewallRule(
            backend=backend,
            family=RuleFamily.INET,
            table_name="filter",
            chain=RuleChain.INPUT,
            protocol=RuleProtocol.TCP,
            port_start=22,
            port_end=22,
            action=RuleAction.ACCEPT,
            priority=10,
            comment="Allow SSH only",
        ),
        FirewallRule(
            backend=backend,
            family=RuleFamily.INET,
            table_name="filter",
            chain=RuleChain.INPUT,
            action=RuleAction.DROP,
            priority=100,
            comment="Drop all other incoming traffic",
        ),
    ]
    
    return FirewallPolicy(
        policy_type=PolicyType.MAINTENANCE,
        name="Maintenance Mode",
        description="Allow only SSH, drop all other incoming",
        rules=rules,
        backend=backend,
    )


def build_monitoring_policy(backend: str = "nftables") -> FirewallPolicy:
    """Build the MONITORING policy.
    
    Profile: Monitoring mode — observe only, no blocking.
    - Allow all traffic
    - Log everything for analysis
    - No drop or reject actions
    """
    rules = [
        FirewallRule(
            backend=backend,
            family=RuleFamily.INET,
            table_name="filter",
            chain=RuleChain.INPUT,
            action=RuleAction.LOG,
            priority=0,
            comment="Log all incoming traffic",
        ),
        FirewallRule(
            backend=backend,
            family=RuleFamily.INET,
            table_name="filter",
            chain=RuleChain.OUTPUT,
            action=RuleAction.LOG,
            priority=0,
            comment="Log all outgoing traffic",
        ),
        FirewallRule(
            backend=backend,
            family=RuleFamily.INET,
            table_name="filter",
            chain=RuleChain.INPUT,
            action=RuleAction.ACCEPT,
            priority=100,
            comment="Allow all incoming (monitoring only)",
        ),
        FirewallRule(
            backend=backend,
            family=RuleFamily.INET,
            table_name="filter",
            chain=RuleChain.OUTPUT,
            action=RuleAction.ACCEPT,
            priority=100,
            comment="Allow all outgoing (monitoring only)",
        ),
    ]
    
    return FirewallPolicy(
        policy_type=PolicyType.MONITORING,
        name="Monitoring Mode",
        description="Log all traffic, no blocking",
        rules=rules,
        backend=backend,
    )


def get_policy(policy_type: PolicyType, backend: str = "nftables") -> FirewallPolicy:
    """Get a predefined policy by type.
    
    Args:
        policy_type: The type of policy to retrieve
        backend: Target backend ('nftables' or 'iptables')
    
    Returns:
        The corresponding FirewallPolicy
    
    Raises:
        ValueError: If the policy type is unknown
    """
    builders = {
        PolicyType.LOCAL: build_local_policy,
        PolicyType.STRICT: build_strict_policy,
        PolicyType.MAINTENANCE: build_maintenance_policy,
        PolicyType.MONITORING: build_monitoring_policy,
    }
    
    builder = builders.get(policy_type)
    if builder is None:
        raise ValueError(f"Unknown policy type: {policy_type}")
    
    return builder(backend=backend)


def list_available_policies() -> list[PolicyType]:
    """Return the list of all available policy types."""
    return list(PolicyType)

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit les politiques firewall prédéfinies (Local, Strict, Maintenance, Monitoring) et la logique de sélection. Une politique est un ensemble nommé de règles appliquées en bloc.
# Pourquoi dans domain/ (charte) :
# - C'est une règle métier : quelles règles composent chaque profil
# - Aucune dépendance externe (utilise uniquement domain/rules/models.py)
# - Testable sans aucun backend réel
# - Utilisé par application/commands/apply_policy.py
# Ce qu'il ne contient PAS
# ❌ Pas d'import depuis infrastructure/, interfaces/, application/
# ❌ Pas d'exécution de règles (juste la définition)
# ❌ Pas de logique d'application (ça, c'est dans service.py)
# Points clés :
# - 4 politiques prédéfinies : Local, Strict, Maintenance, Monitoring
# - get_policy() : point d'entrée unique pour récupérer une politique par type
# - FirewallPolicy.to_ruleset() : convertit la politique en RuleSet pour l'orchestration
# - Aucune dépendance externe : utilise uniquement domain/rules/models.py
# - Testable en mémoire : on peut construire une politique et compter ses règles sans backend
# Comment il sera utilisé (aperçu) :
# - application/commands/apply_policy.py appellera get_policy() pour récupérer la politique
# - domain/rules/service.py orchestrera l'application de la politique
# - interfaces/cli/actions.py proposera le choix de politique à l'utilisateur via list_available_policies()
#---------------------------------------------------------------------->
