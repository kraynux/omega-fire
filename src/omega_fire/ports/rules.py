# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Contrat pour la gestion des règles firewall (création, suppression, politiques)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Protocol

from omega_fire.shared.networking import CIDR


@dataclass(frozen=True, slots=True)
class RuleSpec:
    """Spécification d'une règle firewall.

    Attributs:
        chain: chaîne (input, output, forward).
        protocol: protocole (tcp, udp, icmp, any).
        port: port ou plage de ports (None = tous).
        source: adresse source (CIDR ou None = toutes).
        destination: adresse destination (CIDR ou None = toutes).
        action: action (accept, drop, reject, log).
        comment: commentaire optionnel.
    """
    chain: str
    protocol: str
    port: str | None = None
    source: CIDR | None = None
    destination: CIDR | None = None
    action: str = "accept"
    comment: str = ""


@dataclass(frozen=True, slots=True)
class PolicySpec:
    """Spécification d'une politique prédéfinie.

    Attributs:
        name: nom de la politique (strict, local, monitoring, maintenance).
        description: description de la politique.
        default_action: action par défaut (drop, accept).
        rules: liste de règles à appliquer.
    """
    name: str
    description: str
    default_action: str
    rules: list[RuleSpec]


class RulesPort(Protocol):
    """Contrat pour la gestion des règles firewall.

    Définit les opérations attendues pour créer, supprimer, lister
    les règles et appliquer des politiques prédéfinies.
    """

    @abstractmethod
    def create_rule(self, rule: RuleSpec, backend: str) -> str:
        """Crée une règle firewall.

        Args:
            rule: spécification de la règle.
            backend: backend cible (nftables, iptables).

        Returns:
            Identifiant de la règle créée.
        """
        ...

    @abstractmethod
    def delete_rule(self, rule_id: str, backend: str) -> None:
        """Supprime une règle firewall.

        Args:
            rule_id: identifiant de la règle.
            backend: backend cible.

        Raises:
            RuleNotFoundError: si la règle n'existe pas.
        """
        ...

    @abstractmethod
    def list_rules(self, backend: str | None = None) -> list[dict]:
        """Liste toutes les règles.

        Args:
            backend: filtre par backend (None = tous).

        Returns:
            Liste de dictionnaires représentant les règles.
        """
        ...

    @abstractmethod
    def apply_policy(self, policy_name: str, backend: str) -> int:
        """Applique une politique prédéfinie.

        Args:
            policy_name: nom de la politique (strict, local, monitoring, maintenance).
            backend: backend cible.

        Returns:
            Nombre de règles appliquées.

        Raises:
            PolicyNotFoundError: si la politique n'existe pas.
        """
        ...

    @abstractmethod
    def list_policies(self) -> list[PolicySpec]:
        """Liste les politiques prédéfinies disponibles.

        Returns:
            Liste de PolicySpec.
        """
        ...

    @abstractmethod
    def get_policy(self, policy_name: str) -> PolicySpec:
        """Récupère une politique prédéfinie.

        Args:
            policy_name: nom de la politique.

        Returns:
            PolicySpec de la politique.

        Raises:
            PolicyNotFoundError: si la politique n'existe pas.
        """
        ...

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit le contrat (Protocol) pour la gestion des règles firewall.
# - Fournit RuleSpec et PolicySpec (dataclasses frozen).
# - Spécifie les opérations : create_rule(), delete_rule(), list_rules(),
#   apply_policy(), list_policies(), get_policy().
#
# Pourquoi dans ports/ (charte) :
# - C'est un contrat attendu par le cœur applicatif (application/commands/)
# - Pas d'implémentation concrète (c'est le rôle de infrastructure/backends/)
# - Aucune dépendance vers domain/, application/, infrastructure/, interfaces/
#
# Ce qu'il ne contient PAS :
# ❌ Pas d'implémentation concrète (appels nft/iptables)
# ❌ Pas d'import depuis domain/
# ❌ Pas d'import depuis application/
# ❌ Pas d'import depuis infrastructure/
# ❌ Pas d'import depuis interfaces/
# ❌ Pas de définition des politiques prédéfinies (c'est domain/rules/policies.py)
#
# Points clés :
# - RuleSpec : dataclass frozen avec chain, protocol, port, source, destination,
#   action, comment
# - PolicySpec : dataclass frozen avec name, description, default_action, rules
# - RulesPort : Protocol définissant toutes les opérations sur règles et politiques
# - CIDR importé depuis shared/networking.py
# - Toutes les méthodes sont abstraites (via Protocol)
#
# Comment il sera utilisé (aperçu) :
# - application/commands/create_rule.py appellera rules_port.create_rule()
# - application/commands/apply_policy.py appellera rules_port.apply_policy()
# - infrastructure/backends/nftables/adapter.py implémentera RulesPort
# - infrastructure/backends/iptables/adapter.py implémentera RulesPort
# - interfaces/cli/actions.py appellera rules_port.list_policies() pour menu 3.4
#---------------------------------------------------------------------->
