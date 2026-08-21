# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Find equivalent rules on other backends use case.

Thin query wrapping RuleRepository.find_equivalent_rules(), so the
interface layer (menu 3.2) never calls the repository directly —
consistent with every other cross-layer access in the project (e.g.
ListPersistedRulesQuery wraps the same repository for menu 3.3).

Conforms to Omega-Fire architecture charter:
- No direct SQL, no subprocess
- Translates infrastructure exceptions into a structured result
"""
from dataclasses import dataclass, field
from typing import Optional

from omega_fire.domain.rules.models import FirewallRule
from omega_fire.infrastructure.storage.sqlite.repositories import RuleRepository
from omega_fire.infrastructure.storage.sqlite.exceptions import RepositoryError


@dataclass
class FindEquivalentRulesRequest:
    """Input for the find-equivalent-rules use case."""
    exclude_backend: str
    chain: str
    action: str
    protocol: str
    port_start: Optional[int]
    source_cidr: Optional[str]


@dataclass
class FindEquivalentRulesResult:
    """Output of the find-equivalent-rules use case."""
    success: bool
    rules: list[FirewallRule] = field(default_factory=list)
    message: str = ""


class FindEquivalentRulesQuery:
    """Use case: find rules sharing the same network intent on OTHER
    backends — used by menu 3.2 to inform the user before a deletion
    that could otherwise leave a sibling rule silently active elsewhere."""

    def __init__(self, rule_repository: RuleRepository):
        self._repository = rule_repository

    def execute(self, request: FindEquivalentRulesRequest) -> FindEquivalentRulesResult:
        try:
            rules = self._repository.find_equivalent_rules(
                exclude_backend=request.exclude_backend,
                chain=request.chain,
                action=request.action,
                protocol=request.protocol,
                port_start=request.port_start,
                source_cidr=request.source_cidr,
            )
        except RepositoryError as e:
            return FindEquivalentRulesResult(
                success=False,
                rules=[],
                message=f"Erreur technique lors de la recherche de règles équivalentes : {e}",
            )

        return FindEquivalentRulesResult(success=True, rules=rules)


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Interroge RuleRepository.find_equivalent_rules() pour trouver, sur
#   TOUT backend autre que celui exclu, les règles partageant les mêmes
#   critères réseau (chaîne, action, protocole, port, source).
# - Utilisé par le menu 3.2 avant suppression, pour informer l'utilisateur
#   qu'une règle sœur existe ailleurs, sans jamais décider à sa place.
#
# Pourquoi dans application/queries/ (charte) :
# - Requête simple de lecture, aucune décision métier, juste un pont vers
#   l'infrastructure — même rôle que ListPersistedRulesQuery.
#
# Limite connue (dette technique déjà notée) :
# - La comparaison protocole ne passe pas par IFNULL côté SQL : une règle
#   sans protocole (ex. loopback_only, match_established) ne sera jamais
#   détectée comme équivalente entre backends par ce mécanisme. Sans
#   impact sur les cas d'usage courants (règles avec port/protocole
#   explicite), qui restent correctement détectées.
#
# Flux d'exécution :
# interfaces/cli/actions.py : action_3_2_delete_rule(ctx)
# application/queries/find_equivalent_rules.py : FindEquivalentRulesQuery.execute()
#   ↓ RuleRepository.find_equivalent_rules()
#---------------------------------------------------------------------->
