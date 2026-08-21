# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Create rule on multiple backends use case.

Orchestrates creating a single user-defined firewall rule (menu 3.1)
across every TARGETED backend (by default, every backend detected on
the system — nftables and/or iptables; a single-backend diagnostic
target remains possible, chosen explicitly by the user in
interfaces/cli/actions.py).

Mirrors application/commands/apply_preset_all_backends.py: each backend
is handled by its own independent call to CreateRuleCommand (unchanged),
persisting one distinct FirewallRule row per backend (each with its own
external_ref) rather than attempting to represent one logical rule as a
single merged database row. A failure on one backend never rolls back a
success already achieved on another; the outcome is always reported per
backend.

Conforms to Omega-Fire architecture charter:
- No direct subprocess/SQL calls (delegates entirely to CreateRuleCommand
  per backend, itself delegating to the repository and adapter)
- Auditing is handled by the caller (interfaces/cli/_execute_action_flow),
  not duplicated here
"""
from dataclasses import dataclass, field
from typing import Any, Optional

from omega_fire.application.commands.create_rule import CreateRuleCommand, CreateRuleRequest


@dataclass
class CreateRuleAllBackendsRequest:
    """Input for the create-rule-on-multiple-backends use case.

    Same fields as CreateRuleRequest, minus the single `backend` field
    (replaced by target_backends — the list of backends this rule
    should be created on, determined by the caller: every backend
    detected by default, or a single one if the user explicitly chose
    the diagnostic targeting option).
    """
    name: str
    action: str
    chain: str
    protocol: str
    source_cidr: Optional[str] = None
    dest_cidr: Optional[str] = None
    dst_port: Optional[int] = None
    interface: Optional[str] = None
    description: Optional[str] = None
    target_backends: list[str] = field(default_factory=list)


@dataclass
class BackendCreateOutcome:
    """Result of creating the rule on a single backend."""
    backend: str
    success: bool
    applied: bool
    rule_id: Optional[int]
    message: str


@dataclass
class CreateRuleAllBackendsResult:
    """Output of the create-rule-on-multiple-backends use case."""
    success: bool  # True if AT LEAST one backend succeeded
    outcomes: list[BackendCreateOutcome] = field(default_factory=list)


class CreateRuleToAllBackendsCommand:
    """Use case: create a single logical rule as one independent
    FirewallRule row per targeted backend."""

    def __init__(self, rule_repository: Any, adapters: dict[str, Any]):
        """Initialize the command.

        Args:
            rule_repository: Persistence for FirewallRule, shared across
                all backends (same repository, distinct rows).
            adapters: Mapping of backend name -> already-resolved
                adapter, for every backend in request.target_backends.
                A missing or None adapter for a targeted backend results
                in that backend's rule being persisted but never applied
                (same degraded behavior as CreateRuleCommand when its
                own adapter is None).
        """
        self._repository = rule_repository
        self._adapters = adapters

    def execute(self, request: CreateRuleAllBackendsRequest) -> CreateRuleAllBackendsResult:
        outcomes: list[BackendCreateOutcome] = []

        for backend in request.target_backends:
            single_request = CreateRuleRequest(
                name=request.name,
                backend=backend,
                action=request.action,
                chain=request.chain,
                protocol=request.protocol,
                source_cidr=request.source_cidr,
                dest_cidr=request.dest_cidr,
                dst_port=request.dst_port,
                interface=request.interface,
                description=request.description,
            )

            single_result = CreateRuleCommand(
                self._repository,
                self._adapters.get(backend),
            ).execute(single_request)

            outcomes.append(BackendCreateOutcome(
                backend=backend,
                success=single_result.success,
                applied=single_result.applied,
                rule_id=single_result.rule_id,
                message=single_result.message,
            ))

        overall_success = any(o.success for o in outcomes)

        return CreateRuleAllBackendsResult(
            success=overall_success,
            outcomes=outcomes,
        )


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Crée une même règle logique (menu 3.1) sur PLUSIEURS backends —
#   par défaut tous ceux détectés, ou un seul en ciblage diagnostic
#   explicite choisi par l'utilisateur dans actions.py.
# - Une ligne FirewallRule DISTINCTE est persistée par backend (chacune
#   avec son propre external_ref) — jamais de fusion en une seule ligne
#   représentant artificiellement "les deux backends à la fois".
#
# Pourquoi dans application/commands/ (charte) :
# - Orchestration de haut niveau (boucle + agrégation), ne fait aucun
#   subprocess/SQL direct — entièrement délégué à CreateRuleCommand
#   (inchangée), elle-même déléguée au repository et à l'adapter.
#
# Ce qu'il ne contient PAS :
# ❌ Pas d'import de infrastructure/backends/ (adapters reçus en paramètre)
# ❌ Pas de rendu UI
# ❌ Pas de logique de rollback croisé (un échec sur un backend n'annule
#    jamais un succès déjà obtenu sur un autre — même principe que
#    apply_preset_all_backends.py)
#
# Points clés :
# - CreateRuleAllBackendsRequest : mêmes champs que CreateRuleRequest,
#   'backend' remplacé par 'target_backends' (liste)
# - BackendCreateOutcome : résultat individuel par backend (backend,
#   success, applied, rule_id, message) — jamais fusionné
# - CreateRuleAllBackendsResult.success : True si AU MOINS un backend a
#   réussi, détail complet toujours disponible via outcomes
#
# Flux d'exécution :
# interfaces/cli/actions.py : action_3_1_create_advanced_rule(ctx)
#   ↓ détecte les backends, résout target_backends (tous par défaut, ou
#     un seul si diagnostic choisi explicitement)
# application/commands/create_rule_all_backends.py :
#   CreateRuleToAllBackendsCommand.execute()
#   ↓ pour chaque backend ciblé : CreateRuleCommand(...).execute() (inchangée)
#---------------------------------------------------------------------->
