# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Politiques par defaut differentes selon les backends (menu 3.5) : effet reel,
cause, remede (retour utilisateur 2026-10-28).

Le noyau fait passer chaque paquet par toutes les chaines de base accrochees au meme
point (nftables d'Omega-Fire ET tables iptables-nft d'UFW...) : un paquet doit etre
accepte par chacune, la politique la plus stricte l'emporte. « nftables ACCEPT,
iptables DROP » n'ouvre donc rien ; c'est le cas normal d'une machine filtree par UFW
apres l'initialisation de la table d'Omega-Fire. Le cas a risque est une politique
DROP orpheline (ancien profil) sur un backend sans regle : tout y est bloque.

Causes d'un DROP, par ordre de priorite :
- tool    : le backend porte les regles d'un autre outil (UFW...) -> politique de cet outil ;
- preset  : un profil Omega-Fire (3.4) est actif sur ce backend ;
- orphan  : ni profil ni autre outil, aucune regle -> tout est bloque (alerte) ;
- rules   : ni profil ni autre outil, mais des regles -> seul ce qu'elles autorisent passe."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from omega_fire.shared.i18n import _

CHAINS = ("input", "output", "forward")
_BLOCKING = {"drop", "reject"}


@dataclass
class ChainDivergence:
    chain: str
    policies: dict[str, str]  # backend -> politique (minuscules), ordre des backends
    effective: str            # politique qui s'applique en pratique


@dataclass
class DropCause:
    kind: str                 # tool | preset | orphan | rules
    backends: list[str]
    tools: list[str] = field(default_factory=list)
    rule_count: int = 0

    @property
    def is_alert(self) -> bool:
        return self.kind == "orphan"


@dataclass
class PolicyAnalysis:
    chains: list[ChainDivergence] = field(default_factory=list)
    causes: list[DropCause] = field(default_factory=list)

    @property
    def has_alert(self) -> bool:
        return any(c.is_alert for c in self.causes)


def analyze_policies(
    entries: list[Any],
    foreign: dict[str, Counter],
    preset_backends: set[str],
) -> PolicyAnalysis:
    """entries : TableStatusEntry de GetTablesStatusQuery ; foreign : regles d'autres
    outils par backend (foreign_rules.py) ; preset_backends : backends ou un profil 3.4
    est actif. Un backend absent, illisible ou sans table n'est pas compare."""
    usable = [e for e in entries if e.available and e.table_exists and e.error is None]
    analysis = PolicyAnalysis()
    dropping: dict[str, Any] = {}
    for chain in CHAINS:
        seen: dict[str, str] = {}
        for entry in usable:
            policy = entry.policies.get(chain) or entry.policies.get(chain.upper())
            if policy:
                seen[entry.backend] = policy.lower()
        if len(set(seen.values())) <= 1:
            continue
        effective = next((p for p in seen.values() if p in _BLOCKING), next(iter(seen.values())))
        analysis.chains.append(ChainDivergence(chain=chain, policies=seen, effective=effective))
        for entry in usable:
            if seen.get(entry.backend) in _BLOCKING:
                dropping[entry.backend] = entry

    grouped: dict[tuple, DropCause] = {}
    for backend, entry in dropping.items():
        tools = [tool for tool, _n in foreign.get(backend, Counter()).most_common()]
        if tools:
            key = ("tool", tuple(tools))
        elif backend in preset_backends:
            key = ("preset",)
        elif entry.rule_count == 0:
            key = ("orphan", backend)
        else:
            key = ("rules", backend)
        cause = grouped.get(key)
        if cause is None:
            cause = grouped[key] = DropCause(kind=key[0], backends=[], tools=list(tools))
        cause.backends.append(backend)
        cause.rule_count += entry.rule_count
    analysis.causes = list(grouped.values())
    return analysis


def describe_policies(analysis: PolicyAnalysis) -> list[str]:
    """Lignes affichees par 3.5 (TUI et --legacy-cli) ; [] sans divergence."""
    if not analysis.chains:
        return []
    lines = [_("Politiques différentes selon les backends — un paquet doit être accepté par chaque backend, le plus strict l'emporte :")]
    for d in analysis.chains:
        policies = " · ".join(f"{backend} {policy.upper()}" for backend, policy in d.policies.items())
        lines.append("  " + _("{chain} : {policies} → en pratique {effective}").format(
            chain=d.chain.upper(), policies=policies, effective=d.effective.upper()))
    for cause in analysis.causes:
        backends = ", ".join(cause.backends)
        if cause.kind == "tool":
            tools = ", ".join(cause.tools)
            text = _("{backends} : politique posée par {tools} — normal, c'est {tools} qui filtre. Rien à faire.").format(
                backends=backends, tools=tools)
        elif cause.kind == "preset":
            text = _("{backends} : profil Omega-Fire actif (3.4). Rien à faire, ou changer de profil.").format(backends=backends)
        elif cause.kind == "orphan":
            text = _("{backends} : politique DROP orpheline (ancien profil) et aucune règle — tout ce qui passe par cette chaîne est bloqué. Remède : « Remettre les politiques à ACCEPT » sur {backends} (ci-dessous), ou appliquer un profil (3.4).").format(backends=backends)
        else:
            text = _("{backends} : politique DROP sans profil actif, avec {count} règle(s) — seul ce qu'elles autorisent passe. Vérifier en 3.3 ; si ce n'est pas voulu : « Remettre les politiques à ACCEPT » sur {backends}.").format(
                backends=backends, count=cause.rule_count)
        lines.append("  • " + text)
    return lines


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Remplace l'ancien « Divergence(s) de politique entre backends » de
#   3.5 par l'effet réel (le plus strict l'emporte), la cause et le
#   remède. Seul le cas « orphan » est une alerte.
# - Lecture seule : reçoit l'état déjà lu (GetTablesStatusQuery,
#   foreign_rules_by_backend, marqueurs de profil).
#----------------------------------------------------------------------
