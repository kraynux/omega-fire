# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Unban IP on multiple backends use case.

Orchestrates unbanning one or more IP addresses (menu 2.3/2.4/2.9)
across every TARGETED backend. Mirrors ban_ip_all_backends.py.

This is the CRITICAL direction of the ban/unban asymmetry: a DROP
left on even one backend is already fully effective (kernel-level
intersection of base chains on the same hook — see
apply_preset_all_backends.py). So while banning on a single backend
already works, unbanning on a single backend can silently leave the
IP blocked if it was also banned elsewhere — the user believes access
is restored when it is not. Applying to all detected backends by
default directly closes this gap; a single-backend diagnostic target
remains available, explicitly chosen by the user in
interfaces/cli/actions.py.

Conforms to Omega-Fire architecture charter:
- No direct subprocess/SQL calls (delegates entirely to UnbanIpCommand
  per backend, itself delegating to the backend adapter)
- Auditing is handled by the caller (interfaces/cli/_execute_action_flow),
  not duplicated here
"""
from dataclasses import dataclass, field
from typing import Any, Optional

from omega_fire.application.commands.unban_ip import UnbanIpCommand, UnbanIpRequest


@dataclass
class UnbanIpAllBackendsRequest:
    """Input for the unban-IP-on-multiple-backends use case."""
    ips: list[str]
    target_backends: list[str] = field(default_factory=list)


@dataclass
class UnbanIpAllBackendsResult:
    """Output of the unban-IP-on-multiple-backends use case."""
    success: bool  # True if AT LEAST one backend succeeded for AT LEAST one IP
    outcomes: dict[str, Any] = field(default_factory=dict)  # backend -> UnbanIpResult


class UnbanIpToAllBackendsCommand:
    """Use case: unban a set of IPs across every targeted backend."""

    def __init__(self, adapters: dict[str, Any], ban_repository: Optional[Any] = None):
        """Initialize the command.

        Args:
            adapters: Mapping of backend name -> already-resolved
                adapter, for every backend in request.target_backends.
                A missing or None adapter for a targeted backend
                results in that backend's IPs being reported as errors.
            ban_repository: Optional BanRepository, forwarded unchanged
                to each per-backend UnbanIpCommand — see its own
                docstring for why this exists.
        """
        self._adapters = adapters
        self._ban_repository = ban_repository

    def execute(self, request: UnbanIpAllBackendsRequest) -> UnbanIpAllBackendsResult:
        outcomes = {}

        for backend in request.target_backends:
            single_result = UnbanIpCommand(self._adapters.get(backend), self._ban_repository).execute(
                UnbanIpRequest(backend=backend, ips=request.ips)
            )
            outcomes[backend] = single_result

        overall_success = any(
            len(o.unbanned) > 0 or len(o.already_free) > 0
            for o in outcomes.values()
        )

        return UnbanIpAllBackendsResult(success=overall_success, outcomes=outcomes)


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Débannit un ensemble d'IPs (menus 2.3/2.4/2.9) sur PLUSIEURS
#   backends — par défaut tous ceux détectés, ou un seul en ciblage
#   diagnostic explicite choisi par l'utilisateur dans actions.py.
# - Corrige directement le risque identifié : un unban laissé sur un
#   seul backend pouvait laisser l'IP réellement bloquée par un DROP
#   résiduel sur l'autre, silencieusement (asymétrie DROP terminal /
#   ACCEPT non-terminal entre deux chaînes de base au même hook).
#
# Pourquoi dans application/commands/ (charte) :
# - Orchestration de haut niveau (boucle + agrégation), ne fait aucun
#   subprocess/SQL direct — entièrement délégué à UnbanIpCommand
#   (inchangée), elle-même déléguée à l'adapter.
#
# Ce qu'il ne contient PAS :
# ❌ Pas d'import de infrastructure/backends/ (adapters reçus en paramètre)
# ❌ Pas de rendu UI
# ❌ Pas de logique de rollback croisé
#
# Points clés :
# - UnbanIpAllBackendsRequest : liste d'IPs + target_backends
# - UnbanIpAllBackendsResult.outcomes : dict backend -> UnbanIpResult
#   complet (unbanned/already_free/errors), jamais fusionné
# - success : True si AU MOINS un backend a traité AU MOINS une IP avec
#   succès (débannie ou déjà libre)
#
# Flux d'exécution :
# interfaces/cli/actions.py : action_2_3_unban_ip / action_2_4_unban_list / action_2_9_flush_backends
#   ↓ détecte les backends, résout target_backends (tous par défaut, ou
#     un seul si diagnostic choisi explicitement)
# application/commands/unban_ip_all_backends.py : UnbanIpToAllBackendsCommand.execute()
#   ↓ pour chaque backend ciblé : UnbanIpCommand(...).execute() (inchangée)
#---------------------------------------------------------------------->
