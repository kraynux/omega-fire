# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Sync rules from backends use case.

Reads live firewall rules from backend adapters (nftables, iptables) and
reconciles them with the rules persisted in the Omega-Fire database:
- New live rules (not yet in DB, matched by external_ref) are inserted
  with origin="imported".
- Previously imported rules no longer present in the live backend are
  marked enabled=False (not deleted), preserving history for reporting
  and audit (menus 1.5, 7.3, 8.3, 8.4).
- Rules with origin="managed" (created via Omega-Fire itself, e.g. 3.1/3.4)
  are never touched by this synchronization.

Conforms to Omega-Fire architecture charter:
- No subprocess, no raw SQL
- No direct import of infrastructure/backends/ (adapters are received
  already resolved, treated via duck-typing on list_rules())
- Translates infrastructure exceptions into a structured result
- Auditing is handled by the caller (interfaces/cli/_execute_action_flow),
  not duplicated here
"""
from dataclasses import dataclass, field
from typing import Any

from omega_fire.infrastructure.storage.sqlite.repositories import RuleRepository
from omega_fire.infrastructure.storage.sqlite.exceptions import RepositoryError


@dataclass
class SyncRulesRequest:
    """Input for the sync rules use case.

    Attributes:
        backends: Mapping of backend name ("nftables", "iptables") to its
            already-resolved adapter instance. Adapters are expected to
            expose a list_rules() method returning list[FirewallRule]
            with external_ref populated (see infrastructure/backends/*/mapper.py).
    """
    backends: dict[str, Any] = field(default_factory=dict)


@dataclass
class SyncRulesResult:
    """Output of the sync rules use case."""
    success: bool
    added: int
    disabled: int
    unchanged: int
    message: str


class SyncRulesFromBackendsCommand:
    """Use case: reconcile persisted rules with live backend state."""

    def __init__(self, rule_repository: RuleRepository):
        self._repository = rule_repository

    def execute(self, request: SyncRulesRequest) -> SyncRulesResult:
        added = 0
        disabled = 0
        unchanged = 0

        try:
            for backend_name, adapter in request.backends.items():
                if adapter is None or not hasattr(adapter, "list_rules"):
                    continue

                try:
                    live_rules = adapter.list_rules()
                except Exception:
                    # Backend détecté mais interrogation refusée (accès
                    # noyau non privilégié, etc.) — ignoré proprement pour
                    # CE backend seul, la synchronisation continue sur les
                    # autres plutôt que de faire planter toute l'action
                    # (miroir du motif déjà utilisé ailleurs dans le
                    # projet pour ce type d'appel, ex. actions.py 2.5/2.6/
                    # 2.8/2.9).
                    continue

                live_refs: set[str] = set()

                # Step 1: insert rules present live but not yet in DB
                for rule in live_rules:
                    if not rule.external_ref:
                        # No stable technical identifier: skip to avoid
                        # inserting unreconciliable duplicates on every sync.
                        continue

                    live_refs.add(rule.external_ref)

                    existing = self._repository.find_by_external_ref(
                        backend_name, rule.external_ref
                    )
                    if existing is None:
                        rule.origin = "imported"
                        rule.enabled = True
                        self._repository.save(rule)
                        added += 1
                    else:
                        unchanged += 1

                # Step 2: disable previously imported rules no longer live
                db_rules = self._repository.find_all(backend=backend_name)
                for db_rule in db_rules:
                    if db_rule.origin != "imported":
                        continue
                    if not db_rule.enabled:
                        continue
                    if db_rule.external_ref and db_rule.external_ref not in live_refs:
                        self._repository.update_enabled(db_rule.rule_id, False)
                        disabled += 1

        except RepositoryError as e:
            return SyncRulesResult(
                success=False,
                added=added,
                disabled=disabled,
                unchanged=unchanged,
                message=f"Erreur technique lors de la synchronisation : {e}",
            )

        return SyncRulesResult(
            success=True,
            added=added,
            disabled=disabled,
            unchanged=unchanged,
            message=(
                f"{added} règle(s) importée(s), {disabled} désactivée(s), "
                f"{unchanged} déjà à jour."
            ),
        )


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Réconcilie les règles firewall live (backends nftables/iptables) avec
#   la base de données persistée par Omega-Fire.
# - Insère les nouvelles règles détectées (origin="imported").
# - Désactive (enabled=False) les règles importées qui ont disparu du
#   backend live, sans jamais les supprimer (historique conservé pour
#   1.5, 7.3, 8.3, 8.4).
# - Ne touche jamais aux règles origin="managed" (créées via 3.1/3.4).
#
# Pourquoi dans application/commands/ (charte) :
# - Cas d'usage qui orchestre lecture backend + comparaison + écriture DB.
# - Ne fait aucun subprocess, aucun SQL brut (délégué au repository).
# - Ne connaît pas les classes concrètes d'infrastructure/backends/ :
#   les adapters sont reçus déjà résolus, traités par duck-typing.
#
# Ce qu'il ne contient PAS :
# ❌ Pas d'import de infrastructure/backends/ (nftables, iptables)
# ❌ Pas d'appel subprocess direct
# ❌ Pas de rendu UI
#
# Points clés :
# - SyncRulesRequest : dict backend_name -> adapter déjà résolu (fourni
#   par l'appelant, typiquement via ctx.container.get_firewall_port(...))
# - SyncRulesResult : compte added / disabled / unchanged + message
# - Comparaison par external_ref (identifiant technique stable, voir
#   infrastructure/backends/*/mapper.py), jamais par rule_id (ID SQLite)
# - Règles sans external_ref ignorées (pas de comparaison fiable possible)
#
# Flux d'exécution :
# interfaces/cli/actions.py : action_3_3_list_rules(ctx)
#   ↓ résout les adapters via ctx.container.get_firewall_port(...)
#   ↓ construit SyncRulesRequest(backends={...})
# application/commands/sync_rules_from_backends.py : SyncRulesFromBackendsCommand.execute()
#   ↓ adapter.list_rules() (infrastructure/backends/*/adapter.py)
#   ↓ RuleRepository.find_by_external_ref() / save() / update_enabled()
#---------------------------------------------------------------------->
