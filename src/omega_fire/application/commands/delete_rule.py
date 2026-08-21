# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Delete rule use case.

Orchestrates the deletion of a firewall rule. If the rule was applied to
a live backend (external_ref is set), it is first removed from the
kernel via the backend adapter, then removed from the database. This
prevents leaving an active, untracked rule in the kernel after its
database record disappears.

Conforms to Omega-Fire architecture charter:
- No direct backend/SQL calls
- Translates infrastructure exceptions into a structured result
- Auditing is handled by the caller (interfaces/cli/_execute_action_flow),
  not duplicated here
"""
from dataclasses import dataclass
from typing import Any, Optional

from omega_fire.infrastructure.storage.sqlite.repositories import RuleRepository
from omega_fire.infrastructure.storage.sqlite.exceptions import RepositoryError


@dataclass
class DeleteRuleRequest:
    """Input for the delete rule use case."""
    rule_id: int


@dataclass
class DeleteRuleResult:
    """Output of the delete rule use case."""
    success: bool
    rule_id: int
    message: str


class DeleteRuleCommand:
    """Use case: delete a firewall rule by ID, removing it from the live
    kernel first if it was applied there."""

    def __init__(self, rule_repository: RuleRepository, firewall_adapter: Optional[Any] = None):
        """Initialize the command.

        Args:
            rule_repository: Persistence for FirewallRule.
            firewall_adapter: Already-resolved backend adapter matching the
                rule's backend, used to remove it from the live kernel if
                it was applied (external_ref set). If None, only the
                database record is removed, with a warning in the result
                if the rule was applied.
        """
        self._repository = rule_repository
        self._adapter = firewall_adapter

    def execute(self, request: DeleteRuleRequest) -> DeleteRuleResult:
        try:
            rule = self._repository.find_by_id(request.rule_id)
        except RepositoryError as e:
            return DeleteRuleResult(
                success=False,
                rule_id=request.rule_id,
                message=f"Erreur technique lors de la lecture de la règle : {e}",
            )

        if rule is None:
            return DeleteRuleResult(
                success=False,
                rule_id=request.rule_id,
                message=f"Aucune règle trouvée avec l'ID #{request.rule_id}.",
            )

        # --- Retrait du noyau si la règle y était réellement appliquée ---
        kernel_warning = ""
        if rule.external_ref:
            if self._adapter is None:
                kernel_warning = (
                    " Attention : cette règle était active dans le noyau, mais aucun "
                    "backend n'est disponible pour l'en retirer — elle pourrait rester "
                    "effective malgré sa suppression de la base."
                )
            else:
                try:
                    removed = self._remove_from_backend(rule)
                except Exception as e:
                    return DeleteRuleResult(
                        success=False,
                        rule_id=request.rule_id,
                        message=(
                            f"La règle n'a pas pu être retirée du noyau ({e}). "
                            f"Suppression annulée pour éviter une règle active orpheline."
                        ),
                    )
                if not removed:
                    return DeleteRuleResult(
                        success=False,
                        rule_id=request.rule_id,
                        message=(
                            "La règle n'a pas pu être retirée du noyau. "
                            "Suppression annulée pour éviter une règle active orpheline."
                        ),
                    )

        # --- Suppression en base ---
        try:
            deleted = self._repository.delete(request.rule_id)
        except RepositoryError as e:
            return DeleteRuleResult(
                success=False,
                rule_id=request.rule_id,
                message=f"Erreur technique lors de la suppression : {e}",
            )

        if deleted:
            return DeleteRuleResult(
                success=True,
                rule_id=request.rule_id,
                message=f"La règle #{request.rule_id} a été supprimée avec succès.{kernel_warning}",
            )

        return DeleteRuleResult(
            success=False,
            rule_id=request.rule_id,
            message=f"Aucune règle trouvée avec l'ID #{request.rule_id}.",
        )

    def _remove_from_backend(self, rule) -> bool:
        """Call the appropriate adapter deletion method for the rule's backend."""
        if rule.backend == "nftables":
            try:
                handle = int(rule.external_ref)
            except (TypeError, ValueError):
                return False
            return self._adapter.delete_rule(
                family=rule.family.value if hasattr(rule.family, "value") else "ip",
                table=rule.table_name or "filter",
                chain=rule.chain.value,
                handle=handle,
            )
        elif rule.backend == "iptables":
            return self._adapter.delete_rule_by_content(rule.external_ref)
        elif rule.backend == "ip6tables":
            # Même mécanisme que iptables — Ip6tablesAdapter expose la même
            # API (delete_rule_by_content, spécification "-A ..." complète,
            # cf. infrastructure/backends/ip6tables/adapter.py). Branche
            # manquante jusqu'ici : toute règle ip6tables active ne pouvait
            # jamais être réellement retirée via 3.2 (retournait toujours
            # False ici, donc suppression refusée — référentiel §85bis).
            return self._adapter.delete_rule_by_content(rule.external_ref)
        return False


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Supprime une règle firewall. Si elle avait été appliquée au backend
#   live (external_ref renseigné), elle est d'abord retirée du noyau via
#   l'adapter, puis supprimée de la base — jamais l'inverse, pour éviter
#   qu'une règle reste active dans le noyau sans plus aucune trace en base.
#
# Pourquoi dans application/commands/ (charte) :
# - Cas d'usage qui orchestre lecture + suppression noyau + suppression DB.
# - Ne fait aucun subprocess, aucun SQL brut.
# - Traduit les erreurs techniques en résultat structuré.
#
# Ce qu'il ne contient PAS :
# ❌ Pas d'import de infrastructure/backends/ (adapter reçu en paramètre)
# ❌ Pas de rendu UI
#
# Points clés :
# - DeleteRuleRequest / DeleteRuleResult : mêmes DTO qu'avant
# - firewall_adapter optionnel au constructeur : si absent, seule la base
#   est nettoyée, avec avertissement si la règle était réellement active
# - _remove_from_backend() : adapte l'appel à chaque backend
#   - nftables : delete_rule(handle=int(external_ref))
#   - iptables : delete_rule_by_content(raw_line) — pas de numéro de ligne
#     volatil, suppression par spécification complète (voir
#     infrastructure/backends/iptables/adapter.py)
# - Si le retrait noyau échoue, la suppression base est annulée (pas de
#   règle active orpheline, pas de perte de traçabilité)
#
# Flux d'exécution :
# interfaces/cli/actions.py : action_3_2_delete_rule(ctx)
#   ↓ résout l'adapter via ctx.container.get_firewall_port(rule.backend)
# application/commands/delete_rule.py : DeleteRuleCommand.execute()
#   ↓ RuleRepository.find_by_id() / delete()
#   ↓ adapter.delete_rule() / delete_rule_by_content()
#---------------------------------------------------------------------->
