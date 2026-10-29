# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Regles d'autres outils (UFW, Tailscale, Docker...) presentes sur chaque backend.

Sert de garde-fou avant une action qui vide un backend (retour utilisateur
2026-10-28) : sur iptables / ip6tables, vider = `iptables -F` + `-X`, toutes les
chaines de la table filter, celles des autres outils comprises. L'utilisateur
decide ; il doit seulement savoir ce qu'il efface.

Sur nftables, Omega-Fire ne vide que sa propre table (inet filter) : les tables des
autres outils ne sont jamais touchees, elles ne sont donc pas comptees ici."""
from __future__ import annotations

from collections import Counter
from typing import Any

from omega_fire.domain.rules.ownership import rule_owner

# Backends dont le vidage efface aussi les regles des autres outils.
WHOLE_TABLE_BACKENDS = ("iptables", "ip6tables")


def foreign_rules_by_backend(adapters: dict[str, Any]) -> dict[str, Counter]:
    """backend -> Counter(outil -> nombre de regles), pour les backends de
    WHOLE_TABLE_BACKENDS qui en ont. Lecture seule ; un backend illisible est ignore."""
    found: dict[str, Counter] = {}
    for backend in WHOLE_TABLE_BACKENDS:
        adapter = adapters.get(backend)
        if adapter is None:
            continue
        try:
            rules = adapter.list_rules()
        except Exception:
            continue
        tools = Counter(owner for owner in (rule_owner(r) for r in rules) if owner)
        if tools:
            found[backend] = tools
    return found


def describe_foreign_rules(found: dict[str, Counter]) -> str:
    """« iptables : UFW 60, Tailscale 4 ; ip6tables : UFW 90 »."""
    return " ; ".join(
        f"{backend} : " + ", ".join(f"{tool} {count}" for tool, count in sorted(tools.items()))
        for backend, tools in found.items()
    )


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Garde-fou de 3.4 (profil) et 3.5 (vidages, politiques) : dire à
#   l'utilisateur quelles règles d'autres outils il va effacer.
# - Lecture seule (list_rules), aucune écriture.
#----------------------------------------------------------------------
