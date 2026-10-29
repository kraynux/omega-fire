# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Menu 3.5 — Gestion des tables (retour utilisateur 2026-09-24, suite a
l'incident reel : perte totale de reseau apres application repetee de
profils, `nft flush ruleset` global necessaire pour recuperer l'acces
car aucune commande d'Omega-Fire ne couvrait ce besoin).

Six cas d'usage, tous orchestres ici (jamais de subprocess direct — les
adapters recus en parametre font l'I/O reelle, meme discipline que
apply_preset.py/delete_rule.py) :

1. GetTablesStatusQuery — diagnostic en lecture seule (etat de chaque
   backend detecte, divergences de policy entre backends).
2. InitializeTablesCommand — nftables uniquement, cree table/chaines
   MANQUANTES en policy accept, ne touche jamais a une chaine deja
   presente (voir NftablesAdapter.chain_exists()).
3. ResetChainPoliciesCommand — remet input/output/forward a ACCEPT sur
   UN backend, corrige une policy DROP orpheline laissee par un profil
   qui ne la redeclarait pas (bug reel identifie le meme jour).
4. FlushBackendTableCommand — vide un backend precis (delegue a
   adapter.flush(), deja existant).
5. FlushAllTablesSyncCommand — meme mecanisme de flush synchronise que
   application/commands/apply_preset_all_backends.py, rendu reutilisable
   independamment d'une application de profil : le "bouton panique" sur
   pour retrouver l'acces sans devoir taper `nft flush ruleset` a la main
   (qui, lui, detruit aussi les tables d'autres outils sur le systeme).
6. DeleteTableCommand — nftables uniquement, suppression complete de la
   table (chaines/hooks compris) — action avancee, plus destructrice
   qu'un simple flush.

Conforms to Omega-Fire architecture charter:
- No direct subprocess/SQL calls (delegue integralement aux adapters
  recus en parametre)
- No hardcoded runtime paths
- Traduit les exceptions infrastructure en resultats structures
- Auditing gere par l'appelant (interfaces/cli/_execute_action_flow ou
  interfaces/tui/support/action_audit.py), jamais duplique ici
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional
from omega_fire.application.commands.apply_preset import state_file_for
from omega_fire.application.queries.foreign_rules import foreign_rules_by_backend
from omega_fire.application.queries.policy_divergence import PolicyAnalysis, analyze_policies
from omega_fire.shared.i18n import _

_BASE_CHAINS_NFT = ("input", "output", "forward")
_BASE_CHAINS_IPT = ("INPUT", "OUTPUT", "FORWARD")
_TARGET_BACKENDS = ("nftables", "iptables", "ip6tables")


@dataclass
class TableActionResult:
    """Sortie commune a toutes les commandes mutantes de ce module."""
    success: bool
    message: str


@dataclass
class TableStatusEntry:
    """Etat d'UN backend, tel que rapporte par GetTablesStatusQuery."""
    backend: str
    available: bool
    table_exists: bool = False
    policies: dict[str, Optional[str]] = field(default_factory=dict)
    rule_count: int = 0
    error: Optional[str] = None


@dataclass
class TablesStatusResult:
    """Sortie de GetTablesStatusQuery — jamais un statut agrege unique,
    chaque backend reste visible individuellement (meme principe que
    ApplyPresetAllBackendsResult.outcomes)."""
    entries: list[TableStatusEntry]
    policy_divergences: list[str] = field(default_factory=list)
    # Effet reel, cause et remede (application/queries/policy_divergence.py).
    policy_analysis: Optional[PolicyAnalysis] = None


class GetTablesStatusQuery:
    """Cas d'usage 3.5.1 : instantane en lecture seule, jamais de
    mutation. Detecte aussi les divergences de policy entre backends
    (ex. nftables INPUT=accept mais iptables INPUT=drop) — c'est
    exactement le symptome "certaines regles ne se desactivent pas" que
    ce menu existe pour diagnostiquer."""

    def __init__(self, adapters: dict[str, Any]):
        self._adapters = adapters

    def execute(self) -> TablesStatusResult:
        entries: list[TableStatusEntry] = []
        for backend in _TARGET_BACKENDS:
            adapter = self._adapters.get(backend)
            if adapter is None:
                entries.append(TableStatusEntry(backend=backend, available=False))
                continue
            try:
                status = adapter.get_table_status()
            except Exception as e:
                entries.append(TableStatusEntry(backend=backend, available=True, error=str(e)))
                continue
            entries.append(TableStatusEntry(
                backend=backend,
                available=True,
                table_exists=status["table_exists"],
                policies=status["policies"],
                rule_count=status["rule_count"],
            ))
        return TablesStatusResult(
            entries=entries,
            policy_divergences=self._detect_divergences(entries),
            policy_analysis=analyze_policies(entries, foreign_rules_by_backend(self._adapters), self._preset_backends()),
        )

    @staticmethod
    def _preset_backends() -> set[str]:
        backends: set[str] = set()
        for backend in _TARGET_BACKENDS:
            try:
                if state_file_for(backend).exists():
                    backends.add(backend)
            except Exception:
                continue
        return backends

    @staticmethod
    def _detect_divergences(entries: list[TableStatusEntry]) -> list[str]:
        usable = [e for e in entries if e.available and e.table_exists and e.error is None]
        divergences: list[str] = []
        for chain in ("input", "output", "forward"):
            seen: dict[str, str] = {}
            for entry in usable:
                policy = entry.policies.get(chain) or entry.policies.get(chain.upper())
                if policy:
                    seen[entry.backend] = policy.lower()
            if len(set(seen.values())) > 1:
                divergences.append(f"{chain} : " + ", ".join(f"{b}={p}" for b, p in seen.items()))
        return divergences


class InitializeTablesCommand:
    """Cas d'usage 3.5.2 : nftables UNIQUEMENT — iptables/ip6tables n'ont
    rien a initialiser, leur table 'filter' est native au noyau et
    toujours presente. N'ecrase JAMAIS une chaine deja configuree (voir
    NftablesAdapter.chain_exists()) : action de "premiere utilisation"
    pure, idempotente, jamais destructrice — distincte de
    ResetChainPoliciesCommand qui force explicitement."""

    def __init__(self, nftables_adapter: Any):
        self._adapter = nftables_adapter

    def execute(self) -> TableActionResult:
        created: list[str] = []
        try:
            for chain in _BASE_CHAINS_NFT:
                if not self._adapter.chain_exists(chain):
                    self._adapter.set_chain_policy(chain, "accept")
                    created.append(chain)
        except Exception as e:
            return TableActionResult(False, _("Échec de l'initialisation : {e}").format(e=e))
        if not created:
            return TableActionResult(True, _("Table et chaînes déjà initialisées — rien à faire."))
        return TableActionResult(True, _("Chaîne(s) initialisée(s) (policy accept) : {value}.").format(value=', '.join(created)))


class ResetChainPoliciesCommand:
    """Cas d'usage 3.5.3 : remet input/output/forward a ACCEPT sur UN
    backend precis, sans toucher aux regles existantes — corrige une
    policy DROP orpheline laissee par un ancien profil qui ne redeclarait
    pas cette chaine (bug reel identifie le 2026-09-24, symptome "certaines
    regles ne se desactivent pas")."""

    def __init__(self, adapter: Any, backend: str):
        self._adapter = adapter
        self._backend = backend

    def execute(self) -> TableActionResult:
        is_nft = self._backend == "nftables"
        policy_word = "accept" if is_nft else "ACCEPT"
        chains = _BASE_CHAINS_NFT if is_nft else _BASE_CHAINS_IPT
        try:
            for chain in chains:
                self._adapter.set_chain_policy(chain, policy_word)
        except Exception as e:
            return TableActionResult(False, _("Échec de la réinitialisation des politiques sur {backend} : {e}").format(backend=self._backend, e=e))
        return TableActionResult(True, _("Politiques remises à ACCEPT sur {backend} (input/output/forward).").format(backend=self._backend))


class FlushBackendTableCommand:
    """Cas d'usage 3.5.4 : vide UN backend precis (delegue a
    adapter.flush(), deja existant). nftables : seule la table
    d'Omega-Fire (inet filter). iptables / ip6tables : TOUTE la table
    filter, regles des autres outils (UFW...) comprises — l'ecran 3.5
    le signale avant (application/queries/foreign_rules.py)."""

    def __init__(self, adapter: Any, backend: str):
        self._adapter = adapter
        self._backend = backend

    def execute(self) -> TableActionResult:
        try:
            count = self._adapter.flush()
        except Exception as e:
            return TableActionResult(False, _("Échec du vidage de {backend} : {e}").format(backend=self._backend, e=e))
        return TableActionResult(True, _("{backend} vidé ({count} règle(s) retirée(s)).").format(backend=self._backend, count=count))


class FlushAllTablesSyncCommand:
    """Cas d'usage 3.5.5 : le "bouton panique" sûr — meme mecanisme de
    flush synchronise que apply_preset_all_backends.py::
    ApplyPresetToAllBackendsCommand (retour utilisateur 2026-09-24),
    rendu reutilisable INDEPENDAMMENT d'une application de profil.
    Equivalent controle de `nft flush ruleset`, mais limite cote
    nftables a la table d'Omega-Fire. Cote iptables / ip6tables, le
    vidage porte sur toute la table filter, regles des autres outils
    comprises (signale par l'ecran 3.5 avant confirmation). Best-effort par
    backend : un echec sur l'un n'empeche jamais de tenter les autres."""

    def __init__(self, adapters: dict[str, Any]):
        self._adapters = adapters

    def execute(self) -> TableActionResult:
        target_backends = [name for name in _TARGET_BACKENDS if self._adapters.get(name) is not None]
        if not target_backends:
            return TableActionResult(False, _("Aucun backend firewall disponible."))

        flushed: list[str] = []
        errors: list[str] = []
        for backend in target_backends:
            try:
                self._adapters[backend].flush()
                flushed.append(backend)
            except Exception as e:
                errors.append(f"{backend} ({e})")

        if not flushed:
            return TableActionResult(False, _("Échec sur tous les backends : ") + "; ".join(errors))
        message = _("Backend(s) vidé(s) : {value}.").format(value=', '.join(flushed))
        if errors:
            message += _(" Échec(s) : ") + "; ".join(errors) + "."
        return TableActionResult(True, message)


class DeleteTableCommand:
    """Cas d'usage 3.5.6 (action avancee) : nftables UNIQUEMENT —
    suppression COMPLETE de la table (chaines/hooks compris), plus
    destructrice qu'un simple flush (qui ne retire que les regles).
    iptables/ip6tables n'ont pas d'equivalent : leur table 'filter' est
    native au noyau et ne peut pas etre supprimee — seulement videe
    (FlushBackendTableCommand) ou remise a policy ACCEPT
    (ResetChainPoliciesCommand)."""

    def __init__(self, nftables_adapter: Any):
        self._adapter = nftables_adapter

    def execute(self) -> TableActionResult:
        try:
            self._adapter.delete_table()
        except Exception as e:
            return TableActionResult(False, _("Échec de la suppression de la table : {e}").format(e=e))
        return TableActionResult(
            True,
            _("Table nftables (inet filter) supprimée — plus aucun filtrage actif sur ce "
            "backend tant qu'elle n'est pas réinitialisée (3.5.2)."),
        )


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Regroupe les 6 cas d'usage du menu 3.5 "Gestion des tables" (diagnostic,
#   initialisation, reset policies, flush cible/synchronise, suppression
#   complete) — reponse a l'incident reel du 2026-09-24 (perte totale de
#   reseau apres application repetee de profils, aucune commande interne
#   ne couvrait un nettoyage/diagnostic multi-backend synchronise).
#
# Pourquoi dans application/commands/ (charte) :
# - Aucun subprocess/SQL direct — delegue entierement aux adapters recus
#   en parametre (meme patron que apply_preset.py/delete_rule.py).
#
# Ce qu'il ne contient PAS :
# ❌ Pas d'import de infrastructure/backends/ (adapters recus en parametre)
# ❌ Pas de rendu UI
#
# Points cles :
# - InitializeTablesCommand / DeleteTableCommand : nftables SEULEMENT
#   (iptables/ip6tables n'ont ni "premiere utilisation" ni suppression de
#   table possible, leur table 'filter' est native au noyau)
# - GetTablesStatusQuery._detect_divergences() : compare les policies
#   entre backends REELLEMENT disponibles (jamais un backend absent ou en
#   erreur) — signale precisement le symptome qui a motive ce menu
#
# Flux d'execution :
# interfaces/cli/actions.py : action_3_5_table_management(ctx)
#   / interfaces/tui/screens/table_management_screen.py
#   ↓ resout les adapters via ctx.container.get_firewall_port(backend)
# application/commands/manage_tables.py : (une des 6 classes ci-dessus)
#---------------------------------------------------------------------->
