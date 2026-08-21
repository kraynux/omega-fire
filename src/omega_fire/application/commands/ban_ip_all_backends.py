# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ban IP on multiple backends use case.

Orchestrates banning one or more IP addresses (menu 2.1/2.2) across
every TARGETED backend (by default, every backend detected on the
system; a single-backend diagnostic target remains possible, chosen
explicitly by the user in interfaces/cli/actions.py).

Mirrors application/commands/create_rule_all_backends.py: each backend
is handled by its own independent call to BanIpCommand (unchanged). A
failure on one backend never rolls back a success already achieved on
another; the outcome is always reported per backend.

A DROP on a single backend is already fully effective at the kernel
level (two base chains on the same hook combine as an intersection —
see domain notes in apply_preset_all_backends.py), so banning on only
one backend is not itself a safety gap. Applying to all backends by
default is still the right default for consistency of what menu 2.5
displays and to avoid confusion — see unban_ip_all_backends.py for the
asymmetric, more critical case (an unban left on only one backend
silently leaves the IP blocked).

Conforms to Omega-Fire architecture charter:
- No direct subprocess/SQL calls (delegates entirely to BanIpCommand
  per backend, itself delegating to the backend adapter)
- Auditing is handled by the caller (interfaces/cli/_execute_action_flow),
  not duplicated here
"""
from dataclasses import dataclass, field
from typing import Any, Optional

from omega_fire.application.commands.ban_ip import BanIpCommand, BanIpRequest


@dataclass
class BanIpAllBackendsRequest:
    """Input for the ban-IP-on-multiple-backends use case."""
    ips: list[str]
    comment: str = ""
    target_backends: list[str] = field(default_factory=list)


@dataclass
class BanIpAllBackendsResult:
    """Output of the ban-IP-on-multiple-backends use case."""
    success: bool  # True if AT LEAST one backend succeeded for AT LEAST one IP
    outcomes: dict[str, Any] = field(default_factory=dict)  # backend -> BanIpResult


class BanIpToAllBackendsCommand:
    """Use case: ban a set of IPs across every targeted backend."""

    def __init__(self, adapters: dict[str, Any], ban_repository: Optional[Any] = None):
        """Initialize the command.

        Args:
            adapters: Mapping of backend name -> already-resolved
                adapter, for every backend in request.target_backends.
                A missing or None adapter for a targeted backend
                results in that backend's IPs being reported as errors
                (same degraded behavior as BanIpCommand when its own
                adapter is None).
            ban_repository: Optional BanRepository, forwarded unchanged
                to each per-backend BanIpCommand — see its own
                docstring for why this exists.
        """
        self._adapters = adapters
        self._ban_repository = ban_repository

    def execute(self, request: BanIpAllBackendsRequest) -> BanIpAllBackendsResult:
        outcomes = {}

        for backend in request.target_backends:
            single_result = BanIpCommand(self._adapters.get(backend), self._ban_repository).execute(
                BanIpRequest(backend=backend, ips=request.ips, comment=request.comment)
            )
            outcomes[backend] = single_result

        overall_success = any(
            len(o.banned) > 0 or len(o.already_banned) > 0
            for o in outcomes.values()
        )

        return BanIpAllBackendsResult(success=overall_success, outcomes=outcomes)


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Bannit un ensemble d'IPs (menus 2.1/2.2) sur PLUSIEURS backends —
#   par défaut tous ceux détectés, ou un seul en ciblage diagnostic
#   explicite choisi par l'utilisateur dans actions.py.
#
# Pourquoi dans application/commands/ (charte) :
# - Orchestration de haut niveau (boucle + agrégation), ne fait aucun
#   subprocess/SQL direct — entièrement délégué à BanIpCommand
#   (inchangée), elle-même déléguée à l'adapter.
#
# Ce qu'il ne contient PAS :
# ❌ Pas d'import de infrastructure/backends/ (adapters reçus en paramètre)
# ❌ Pas de rendu UI
# ❌ Pas de logique de rollback croisé (un échec sur un backend n'annule
#    jamais un succès déjà obtenu sur un autre)
#
# Points clés :
# - BanIpAllBackendsRequest : liste d'IPs + commentaire + target_backends
# - BanIpAllBackendsResult.outcomes : dict backend -> BanIpResult complet
#   (banned/already_banned/errors), jamais fusionné en un seul statut
# - success : True si AU MOINS un backend a traité AU MOINS une IP avec
#   succès (nouvellement bannie ou déjà présente)
#
# Flux d'exécution :
# interfaces/cli/actions.py : action_2_1_ban_ip / action_2_2_ban_list
#   ↓ détecte les backends, résout target_backends (tous par défaut, ou
#     un seul si diagnostic choisi explicitement)
# application/commands/ban_ip_all_backends.py : BanIpToAllBackendsCommand.execute()
#   ↓ pour chaque backend ciblé : BanIpCommand(...).execute() (inchangée)
#---------------------------------------------------------------------->
