# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Create rule use case.

Orchestrates the creation of a firewall rule defined manually by the
user (menu 3.1): persists it (origin="managed") then applies it to the
live backend adapter. If application succeeds, the rule's technical
identifier (external_ref) is retrieved by re-reading the backend's live
state and matching on the same network criteria, then stored — this is
what later allows menu 3.2 to remove the rule from the kernel, not just
from the database.

Conforms to Omega-Fire architecture charter:
- No direct subprocess/SQL calls (delegates to the repository and to the
  backend adapter, both received already resolved by the caller)
- Translates infrastructure exceptions into a structured result
- Auditing is handled by the caller (interfaces/cli/_execute_action_flow),
  not duplicated here
"""
from dataclasses import dataclass
from typing import Any, Optional

from omega_fire.domain.rules.models import (
    FirewallRule,
    RuleAction,
    RuleChain,
    RuleFamily,
    RuleProtocol,
)
from omega_fire.infrastructure.storage.sqlite.repositories import RuleRepository
from omega_fire.infrastructure.storage.sqlite.exceptions import RepositoryError


@dataclass
class CreateRuleRequest:
    """Input for the create rule use case.

    Values are plain strings/primitives as collected from the CLI prompts
    (menu 3.1); this use case is responsible for converting them into the
    proper domain enums before persisting.
    """
    name: str
    backend: str
    action: str  # "DROP" | "REJECT" | "ACCEPT"
    chain: str  # "INPUT" | "FORWARD" | "OUTPUT"
    protocol: str  # "tcp" | "udp" | "icmp" | "all"
    source_cidr: Optional[str] = None
    dest_cidr: Optional[str] = None
    dst_port: Optional[int] = None
    interface: Optional[str] = None
    description: Optional[str] = None


@dataclass
class CreateRuleResult:
    """Output of the create rule use case."""
    success: bool
    rule_id: Optional[int]
    message: str
    duplicate_of: Optional[int] = None
    applied: bool = False


_ACTION_MAP = {
    "DROP": RuleAction.DROP,
    "REJECT": RuleAction.REJECT,
    "ACCEPT": RuleAction.ACCEPT,
}

_CHAIN_MAP = {
    "INPUT": RuleChain.INPUT,
    "FORWARD": RuleChain.FORWARD,
    "OUTPUT": RuleChain.OUTPUT,
}

_PROTOCOL_MAP = {
    "tcp": RuleProtocol.TCP,
    "udp": RuleProtocol.UDP,
    "icmp": RuleProtocol.ICMP,
    # "all" intentionally maps to None (no protocol filter)
}


class CreateRuleCommand:
    """Use case: create, persist and apply a user-defined firewall rule."""

    def __init__(self, rule_repository: RuleRepository, firewall_adapter: Optional[Any] = None):
        """Initialize the command.

        Args:
            rule_repository: Persistence for FirewallRule.
            firewall_adapter: Already-resolved backend adapter (nftables or
                iptables), matching request.backend. If None, the rule is
                persisted but never applied — the caller is responsible for
                reflecting that in the outcome message.
        """
        self._repository = rule_repository
        self._adapter = firewall_adapter

    def execute(self, request: CreateRuleRequest) -> CreateRuleResult:
        rule_action = _ACTION_MAP.get(request.action.upper(), RuleAction.DROP)
        rule_chain = _CHAIN_MAP.get(request.chain.upper(), RuleChain.INPUT)
        rule_protocol = _PROTOCOL_MAP.get(request.protocol.lower())

        # --- 1. Vérification des doublons (scopée à CE backend) ---
        try:
            duplicate_id = self._repository.exists_similar(
                backend=request.backend,
                chain=rule_chain.value,
                action=rule_action.value,
                protocol=rule_protocol.value if rule_protocol else "ALL",
                port_start=request.dst_port,
                source_cidr=request.source_cidr,
            )
        except RepositoryError as e:
            return CreateRuleResult(
                success=False,
                rule_id=None,
                message=f"Erreur technique lors de la vérification des doublons : {e}",
            )

        if duplicate_id is not None:
            return CreateRuleResult(
                success=False,
                rule_id=None,
                message=f"Une règle identique existe déjà en base (ID #{duplicate_id}).",
                duplicate_of=duplicate_id,
            )

        # --- 2. Persistance (origin="managed") ---
        # family cohérente avec ce que _apply_to_backend() écrit réellement
        # au noyau (voir plus bas : family="inet" pour nftables). Une
        # valeur figée à IP causait un échec systématique de suppression
        # via 3.2 pour toute règle créée sur nftables (mauvaise table
        # visée par la commande nft delete).
        rule_family = RuleFamily.INET if request.backend == "nftables" else RuleFamily.IP

        rule = FirewallRule(
            backend=request.backend,
            family=rule_family,
            table_name="filter",
            chain=rule_chain,
            action=rule_action,
            protocol=rule_protocol,
            port_start=request.dst_port,
            port_end=request.dst_port,
            source_cidr=request.source_cidr,
            dest_cidr=request.dest_cidr,
            comment=request.name,
            enabled=True,
            origin="managed",
            interface=request.interface,
        )

        try:
            new_id = self._repository.save(rule)
        except RepositoryError as e:
            return CreateRuleResult(
                success=False,
                rule_id=None,
                message=f"Erreur technique lors de l'enregistrement : {e}",
            )

        # --- 3. Application au backend live ---
        if self._adapter is None:
            return CreateRuleResult(
                success=True,
                rule_id=new_id,
                applied=False,
                message=(
                    f"La règle '{request.name}' a été créée et enregistrée (ID #{new_id}), "
                    f"mais AUCUN backend n'est disponible pour l'appliquer. "
                    f"Elle reste inactive tant que {request.backend} n'est pas accessible."
                ),
            )

        try:
            applied = self._apply_to_backend(request, rule_chain, rule_protocol)
        except Exception as e:
            return CreateRuleResult(
                success=True,
                rule_id=new_id,
                applied=False,
                message=(
                    f"La règle '{request.name}' a été enregistrée (ID #{new_id}) mais son "
                    f"application sur {request.backend} a échoué : {e}. "
                    f"Elle reste inactive dans le noyau."
                ),
            )

        if not applied:
            return CreateRuleResult(
                success=True,
                rule_id=new_id,
                applied=False,
                message=(
                    f"La règle '{request.name}' a été enregistrée (ID #{new_id}) mais son "
                    f"application sur {request.backend} a échoué. Elle reste inactive dans le noyau."
                ),
            )

        # --- 4. Récupération de l'identifiant technique (external_ref) ---
        matched_ref = self._find_applied_external_ref(request, rule_chain, rule_protocol)
        if matched_ref is not None:
            try:
                self._repository.update_external_ref(new_id, matched_ref)
            except RepositoryError:
                # La règle est bien active dans le noyau ; seul l'enregistrement
                # de son identifiant technique a échoué. On ne fait pas échouer
                # la commande pour autant, mais on le signale clairement.
                return CreateRuleResult(
                    success=True,
                    rule_id=new_id,
                    applied=True,
                    message=(
                        f"La règle '{request.name}' a été créée et appliquée sur "
                        f"{request.backend} (ID #{new_id}), mais son identifiant technique "
                        f"n'a pas pu être enregistré. Sa suppression via 3.2 pourrait ne pas "
                        f"la retirer automatiquement du noyau."
                    ),
                )

        return CreateRuleResult(
            success=True,
            rule_id=new_id,
            applied=True,
            message=(
                f"La règle '{request.name}' a été créée et appliquée avec succès sur "
                f"{request.backend} (ID #{new_id})."
            ),
        )

    def _apply_to_backend(
        self,
        request: CreateRuleRequest,
        rule_chain: RuleChain,
        rule_protocol: Optional[RuleProtocol],
    ) -> bool:
        """Call the appropriate adapter.add_rule() signature for the backend."""
        protocol_str = rule_protocol.value if rule_protocol else None
        port_str = str(request.dst_port) if request.dst_port else None

        if request.backend == "nftables":
            return self._adapter.add_rule(
                family="inet",
                table="filter",
                chain=rule_chain.value,
                action=request.action.lower(),
                protocol=protocol_str,
                port=port_str,
                source=request.source_cidr,
                destination=request.dest_cidr,
                comment=request.name,
            )
        elif request.backend == "iptables":
            return self._adapter.add_rule(
                chain=rule_chain.value.upper(),
                action=request.action.lower(),
                protocol=protocol_str,
                port=port_str,
                source=request.source_cidr,
                destination=request.dest_cidr,
                comment=request.name,
            )
        return False

    def _find_applied_external_ref(
        self,
        request: CreateRuleRequest,
        rule_chain: RuleChain,
        rule_protocol: Optional[RuleProtocol],
    ) -> Optional[str]:
        """Re-read the live backend state to find the rule just applied.

        Matches on the same network criteria used for duplicate detection
        (chain, action, protocol, port, source), since add_rule() does not
        return a technical identifier directly.

        Returns:
            The external_ref of the matching live rule, or None if no
            confident match could be found (rule still considered applied;
            only its precise technical identifier is unknown).
        """
        try:
            live_rules = self._adapter.list_rules()
        except Exception:
            return None

        for live_rule in live_rules:
            if (
                live_rule.chain == rule_chain
                and live_rule.action.value == request.action.lower()
                and live_rule.protocol == rule_protocol
                and live_rule.port_start == request.dst_port
                and (live_rule.source_cidr or None) == (request.source_cidr or None)
            ):
                return live_rule.external_ref

        return None


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Crée et persiste une règle firewall définie manuellement par
#   l'utilisateur (menu 3.1), puis l'applique au backend live via
#   l'adapter fourni (nftables ou iptables).
# - Récupère l'identifiant technique de la règle appliquée en relisant
#   l'état live du backend et en comparant sur les mêmes critères réseau
#   que ceux utilisés pour la détection de doublon, puisque add_rule()
#   ne retourne pas d'identifiant directement.
#
# Pourquoi dans application/commands/ (charte) :
# - Cas d'usage qui orchestre validation + persistance + application.
# - Ne fait aucun subprocess, aucun SQL brut (délégués au repository et
#   à l'adapter, tous deux reçus déjà résolus par l'appelant).
# - Traduit les erreurs techniques en résultat structuré.
#
# Ce qu'il ne contient PAS :
# ❌ Pas d'import de infrastructure/backends/ (adapters reçus en paramètre,
#    traités par duck-typing — add_rule()/list_rules())
# ❌ Pas de rendu UI
#
# Points clés :
# - CreateRuleRequest : valeurs brutes issues des prompts CLI (strings)
# - CreateRuleResult : succès/échec + applied (booléen distinct de success :
#   une règle peut être "créée avec succès" mais "non appliquée" si le
#   backend échoue, sans que ce soit un échec de la commande elle-même)
# - origin="managed" toujours (distingue des règles importées via sync)
# - _apply_to_backend() : adapte les kwargs à la signature propre à chaque
#   backend (nftables a family/table, iptables non ; casse différente des
#   noms de chaîne : "input" vs "INPUT")
# - _find_applied_external_ref() : recherche par critères réseau (pas par
#   nom/commentaire, qui n'est pas garanti unique)
#
# Flux d'exécution :
# interfaces/cli/actions.py : action_3_1_create_advanced_rule(ctx)
#   ↓ résout l'adapter via ctx.container.get_firewall_port(backend)
#   ↓ construit CreateRuleRequest depuis les saisies utilisateur
# application/commands/create_rule.py : CreateRuleCommand.execute()
#   ↓ RuleRepository.exists_similar() / save() / update_external_ref()
#   ↓ adapter.add_rule() / adapter.list_rules()
#---------------------------------------------------------------------->
