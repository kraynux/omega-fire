# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Export rules summary use case.

Read-only query that prepares firewall rule data for export (menu 6.2),
in two shapes:
- A full, ungrouped list (used for JSON/TXT exports — exhaustive, one
  entry per rule, suitable for future reinjection).
- A grouped summary (used for the HTML export — best-effort readability,
  see domain/rules/fingerprint.py).

Scope: nftables and iptables rules only (domain.rules.models.FirewallRule).
fail2ban jails are out of scope — they have their own dedicated menu and
export (4.8), with a structurally different domain model.

Conforms to Omega-Fire architecture charter:
- Read-only query, no side effects
- Consumes RuleRepository (infrastructure/), not raw SQL
- Delegates grouping to domain/rules/fingerprint.py (pure business logic)
- No dependency on interfaces/
"""
from dataclasses import dataclass, field
from typing import Optional

from omega_fire.domain.rules.models import FirewallRule
from omega_fire.domain.rules.fingerprint import RuleGroup, group_rules
from omega_fire.infrastructure.storage.sqlite.repositories import RuleRepository
from omega_fire.infrastructure.storage.sqlite.exceptions import RepositoryError


@dataclass
class ExportRulesSummaryRequest:
    """Input for the export rules summary use case.

    Attributes:
        origin_filter: "all" | "managed" | "imported"
        active_only: If True, excludes rules with enabled=False
    """
    origin_filter: str = "all"
    active_only: bool = False


@dataclass
class ExportRulesSummaryResult:
    """Output of the export rules summary use case.

    Attributes:
        success: Whether the query succeeded
        full_list: Every matching rule, ungrouped (JSON/TXT export)
        groups: Rules grouped by network-similarity fingerprint (HTML export)
        message: Human-readable summary or error
    """
    success: bool
    full_list: list[FirewallRule] = field(default_factory=list)
    groups: list[RuleGroup] = field(default_factory=list)
    message: str = ""


class ExportRulesSummaryQuery:
    """Use case: retrieve and prepare rules for export (menu 6.2)."""

    def __init__(self, rule_repository: RuleRepository):
        self._repository = rule_repository

    def execute(self, request: Optional[ExportRulesSummaryRequest] = None) -> ExportRulesSummaryResult:
        request = request or ExportRulesSummaryRequest()

        try:
            rules = self._repository.find_all()
        except RepositoryError as e:
            return ExportRulesSummaryResult(
                success=False,
                message=f"Erreur technique lors de la lecture des règles : {e}",
            )

        # --- Filtrage par origine ---
        if request.origin_filter == "managed":
            rules = [r for r in rules if r.origin == "managed"]
        elif request.origin_filter == "imported":
            rules = [r for r in rules if r.origin == "imported"]
        # "all" : aucun filtre

        # --- Filtrage par état actif ---
        if request.active_only:
            rules = [r for r in rules if r.enabled]

        if not rules:
            return ExportRulesSummaryResult(
                success=True,
                full_list=[],
                groups=[],
                message="Aucune règle ne correspond aux critères sélectionnés.",
            )

        groups = group_rules(rules)

        return ExportRulesSummaryResult(
            success=True,
            full_list=rules,
            groups=groups,
            message=f"{len(rules)} règle(s) trouvée(s), regroupées en {len(groups)} entrée(s) distincte(s).",
        )


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Récupère les règles firewall persistées (RuleRepository), applique les
#   filtres choisis à l'écran (origine, état actif), puis prépare deux
#   représentations : liste complète (JSON/TXT) et groupes (HTML).
# - Périmètre : nftables/iptables uniquement (FirewallRule). fail2ban est
#   hors périmètre, géré par son propre menu et export (4.8).
#
# Pourquoi dans application/queries/ (charte) :
# - Query en lecture seule, aucun effet de bord.
# - Consomme RuleRepository (infrastructure/), pas de SQL brut ici.
# - Délègue le regroupement à domain/rules/fingerprint.py (logique métier
#   pure), ne réimplémente pas la logique de similarité elle-même.
#
# Ce qu'il ne contient PAS :
# ❌ Pas d'accès SQL direct
# ❌ Pas de rendu (JSON/TXT/HTML) — c'est le rôle des exporters +
#    interfaces/cli/actions.py
# ❌ Pas de logique fail2ban
#
# Points clés :
# - ExportRulesSummaryRequest : origin_filter ("all"/"managed"/"imported"),
#   active_only (bool)
# - ExportRulesSummaryResult :
#   - full_list : toutes les règles filtrées, non groupées (source fidèle
#     pour JSON/TXT, réutilisable/réinjectable)
#   - groups : mêmes règles, regroupées par empreinte (domain/rules/
#     fingerprint.py), pour la vue HTML lisible
# - Le filtrage se fait sur la liste déjà en mémoire (find_all() sans
#   filtre BDD) : volumétrie confirmée non problématique (centaines de
#   règles, pas de souci de performance à ce stade)
#
# Flux d'exécution :
# interfaces/cli/actions.py : action_6_2_export_rules(ctx)
#   ↓ construit ExportRulesSummaryRequest depuis les choix utilisateur
# application/queries/export_rules_summary.py : ExportRulesSummaryQuery.execute()
#   ↓ RuleRepository.find_all()
#   ↓ domain/rules/fingerprint.py : group_rules()
#   ↓ résultat transmis aux exporters (JsonExporter/TxtExporter/HtmlExporter)
#---------------------------------------------------------------------->
