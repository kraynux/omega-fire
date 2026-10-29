# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Outil proprietaire d'une regle lue dans le noyau (retour utilisateur 2026-10-28).

Le listage melangeait les regles d'Omega-Fire et celles d'autres outils (UFW,
Tailscale, docker...) sous une meme etiquette « SYSTEME ». Ces regles appartiennent
a leur outil : Omega-Fire les affiche, ne les modifie pas.

Reconnu d'apres la chaine (iptables/ip6tables : `-A <chaine>` de l'external_ref ;
nftables : nom de chaine lu dans le noyau quand il est connu) ou la table nftables."""
from __future__ import annotations

from typing import Any, Optional

# Prefixe de chaine -> outil. Noms de chaines poses par ces outils eux-memes.
_CHAIN_PATTERNS = (
    ("ufw6-", "UFW"),
    ("ufw-", "UFW"),
    ("ts-", "Tailscale"),
    ("DOCKER", "Docker"),
    ("f2b-", "Fail2Ban"),
    ("fail2ban-", "Fail2Ban"),
    ("LIBVIRT_", "libvirt"),
    ("KUBE-", "Kubernetes"),
    ("CNI-", "CNI"),
    ("cali-", "Calico"),
    ("FLANNEL", "Flannel"),
    ("FORWARD_", "firewalld"),
    ("INPUT_", "firewalld"),
    ("OUTPUT_", "firewalld"),
    ("IN_", "firewalld"),
)
_NFT_TABLE_PATTERNS = {"firewalld": "firewalld", "tailscale": "Tailscale", "docker": "Docker"}
_BASE_CHAINS = {"input", "output", "forward"}


def chain_of(rule: Any) -> Optional[str]:
    """Vrai nom de chaine : lu dans le noyau, ou retrouve dans l'external_ref iptables."""
    name = getattr(rule, "chain_name", None)
    if name:
        return name
    ref = getattr(rule, "external_ref", None) or ""
    if getattr(rule, "backend", "") in ("iptables", "ip6tables") and ref.startswith("-A "):
        parts = ref.split()
        return parts[1] if len(parts) > 1 else None
    return None


def rule_owner(rule: Any) -> Optional[str]:
    """Nom de l'outil qui a pose la regle, ou None (Omega-Fire ou regle manuelle)."""
    chain = chain_of(rule)
    if chain and chain.lower() not in _BASE_CHAINS:
        for prefix, tool in _CHAIN_PATTERNS:
            if chain.startswith(prefix):
                return tool
    if getattr(rule, "backend", "") == "nftables":
        family = getattr(rule, "family", "")
        family = getattr(family, "value", family)
        table = str(getattr(rule, "table_name", "") or "")
        if (family, table) != ("inet", "filter"):
            for key, tool in _NFT_TABLE_PATTERNS.items():
                if key in table.lower():
                    return tool
            return " ".join(("nft", str(family), table))
    if chain and chain.lower() not in _BASE_CHAINS:
        return chain
    return None


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Étiquette « outil propriétaire » des règles (3.3 listage, 3.2
#   suppression : une règle d'un autre outil n'est pas supprimée par
#   Omega-Fire, elle se gère avec son outil).
# Pourquoi dans domain/ :
# - Règle pure, aucune I/O (lit seulement les champs de FirewallRule).
#----------------------------------------------------------------------
