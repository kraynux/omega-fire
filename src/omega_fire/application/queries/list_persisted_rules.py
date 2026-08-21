# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""List persisted rules use case.

Read-only query that retrieves firewall rules stored in the Omega-Fire
database (managed rules + previously imported system rules), via the
RuleRepository. Distinct from application/queries/list_rules.py, which
targets live backend state through ports/firewall.py.

Conforms to Omega-Fire architecture charter:
- Read-only query, no side effects
- Consumes RuleRepository (infrastructure/), not raw SQL
- No dependency on interfaces/
"""
from dataclasses import dataclass

from omega_fire.domain.rules.models import FirewallRule
from omega_fire.infrastructure.storage.sqlite.repositories import RuleRepository
from omega_fire.infrastructure.storage.sqlite.exceptions import RepositoryError


@dataclass
class ListPersistedRulesResult:
    """Output of the list persisted rules use case."""
    success: bool
    rules: list[FirewallRule]
    message: str = ""


class ListPersistedRulesQuery:
    """Use case: retrieve all firewall rules persisted in the database."""

    def __init__(self, rule_repository: RuleRepository):
        self._repository = rule_repository

    def execute(self) -> ListPersistedRulesResult:
        try:
            rules = self._repository.find_all()
        except RepositoryError as e:
            return ListPersistedRulesResult(success=False, rules=[], message=f"Erreur technique : {e}")

        return ListPersistedRulesResult(success=True, rules=rules)
