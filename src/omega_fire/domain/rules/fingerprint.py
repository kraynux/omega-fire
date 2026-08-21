# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Rule fingerprinting and grouping.

Pure domain logic to detect and group near-duplicate firewall rules for
readable, human-facing summaries (menu 6.2 HTML export). This is a
best-effort grouping meant to make a large ruleset skimmable — it is
NOT used for deduplication that affects persistence or backend sync
(that relies on external_ref, see application/commands/sync_rules_from_backends.py).

A group's fingerprint intentionally excludes the rule's name/comment:
two rules with identical network criteria (backend, chain, action,
protocol, port, source, destination, enabled state) are considered
"the same rule" for display purposes, whether or not one of them has
a label and the other doesn't.

No external dependencies beyond domain/rules/models.py.
"""
from dataclasses import dataclass, field

from omega_fire.domain.rules.models import FirewallRule


@dataclass
class RuleGroup:
    """A group of near-identical firewall rules.

    Attributes:
        fingerprint: The shared similarity key for this group.
        representative: One rule from the group, used to display the
            group's shared attributes (chain, action, protocol, etc.).
        rules: All rules belonging to this group, including the
            representative.
    """
    fingerprint: str
    representative: FirewallRule
    rules: list[FirewallRule] = field(default_factory=list)

    @property
    def count(self) -> int:
        """Number of rules in this group."""
        return len(self.rules)

    @property
    def names(self) -> list[str]:
        """Distinct, non-empty comments/names found across the group."""
        seen = []
        for rule in self.rules:
            name = (rule.comment or "").strip()
            if name and name not in seen:
                seen.append(name)
        return seen


def compute_fingerprint(rule: FirewallRule) -> str:
    """Compute a similarity fingerprint for a rule.

    The fingerprint deliberately excludes name/comment and any
    technical identifier (rule_id, external_ref): it reflects only the
    network-level criteria that make two rules functionally identical
    from a firewall behavior standpoint.

    Args:
        rule: The rule to fingerprint

    Returns:
        A string key; two rules with the same key are considered
        duplicates for display/grouping purposes.
    """
    chain_val = rule.chain.value if hasattr(rule.chain, "value") else str(rule.chain)
    action_val = rule.action.value if hasattr(rule.action, "value") else str(rule.action)
    protocol_val = rule.protocol.value if rule.protocol and hasattr(rule.protocol, "value") else "any"

    parts = [
        rule.backend or "",
        chain_val or "",
        action_val or "",
        protocol_val or "",
        str(rule.port_start) if rule.port_start is not None else "any",
        rule.source_cidr or "any",
        rule.dest_cidr or "any",
        "enabled" if rule.enabled else "disabled",
    ]
    return "|".join(parts)


def group_rules(rules: list[FirewallRule]) -> list[RuleGroup]:
    """Group a list of rules by similarity fingerprint.

    Preserves the order in which each distinct fingerprint was first
    encountered, so the output stays stable and predictable.

    Args:
        rules: Rules to group

    Returns:
        List of RuleGroup, one per distinct fingerprint
    """
    groups: dict[str, RuleGroup] = {}
    order: list[str] = []

    for rule in rules:
        key = compute_fingerprint(rule)
        if key not in groups:
            groups[key] = RuleGroup(fingerprint=key, representative=rule, rules=[])
            order.append(key)
        groups[key].rules.append(rule)

    return [groups[key] for key in order]


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Calcule une empreinte de similarité pour une règle firewall et
#   regroupe une liste de règles quasi-identiques (menu 6.2, export HTML).
# - Regroupement "au mieux" pour la lisibilité humaine, PAS pour la
#   déduplication technique (celle-ci repose sur external_ref, voir
#   application/commands/sync_rules_from_backends.py).
# Pourquoi dans domain/ (charte) :
# - C'est une règle métier : qu'est-ce qui rend deux règles "identiques"
#   du point de vue du comportement firewall, indépendamment de leur nom
# - Aucune dépendance externe hormis domain/rules/models.py
# - Testable sans aucun backend réel
# Ce qu'il ne contient PAS (règles projet) :
# ❌ Pas d'accès BDD, pas de rendu HTML/JSON
# ❌ Pas d'import depuis infrastructure/, application/, interfaces/
# Points clés :
# - compute_fingerprint(rule) : clé de similarité, EXCLUT nom/commentaire,
#   rule_id et external_ref — seulement les critères réseau
#   (backend, chaîne, action, protocole, port, source, destination, état)
# - RuleGroup : fingerprint + règle représentative + liste complète
#   - count : nombre de règles dans le groupe (affiché "×N occurrences")
#   - names : noms/commentaires distincts rencontrés dans le groupe
# - group_rules(rules) : regroupe en préservant l'ordre de première
#   apparition de chaque empreinte (affichage stable et prévisible)
# Comment il sera utilisé (aperçu) :
# - application/queries/export_rules_summary.py appelle group_rules()
#   pour préparer la vue Synthèse HTML (menu 6.2)
# - La vue Complète (JSON/TXT) n'utilise PAS ce regroupement : elle
#   reste exhaustive, une ligne par règle, pour un usage fidèle/réinjectable
#---------------------------------------------------------------------->
