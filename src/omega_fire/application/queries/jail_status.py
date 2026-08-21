# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Query: Get Fail2ban jail status.

Provides read-only access to the status of all Fail2ban jails.
Used by menu 4.1 (État des jails), and — starting with Phase 2 of the
Fail2ban conformance remediation — the shared source of jail listing
data for the rest of Menu 4 (replaces 8 copies of the same raw
fail2ban-client parsing block previously duplicated across
interfaces/cli/actions.py).

Conforms to Omega-Fire architecture charter:
- Read-only query, no side effects
- Consumes ports/fail2ban.py contract (not infrastructure directly)
- Returns formatted string for UI display
- No dependency on interfaces/ or infrastructure/ directly
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional

from omega_fire.ports.fail2ban import JailInfo


@dataclass
class JailStatusResult:
    """Result of the jail status query.

    Attributes:
        jails: List of jails (ports.fail2ban.JailInfo — the real port DTO,
            not a locally redefined one).
        total_jails: Total number of jails.
        active_jails: Number of active jails.
        inactive_jails: Number of inactive jails.
        total_banned_ips: Total banned IPs across all jails.
        message: Human-readable summary.
    """
    jails: List[JailInfo]
    total_jails: int
    active_jails: int
    inactive_jails: int
    total_banned_ips: int
    message: str


def get_jail_status(
    fail2ban_port: Optional[Any] = None,
) -> JailStatusResult:
    """4.1 (et Phase 2 du Menu 4) : récupère l'état de tous les jails Fail2ban.

    Consomme list_jails_info() (Fail2banPort — Phase 1B), qui retourne
    déjà des JailInfo réels (active: bool, banned_count, banned_ips en
    IPAddress, filter, log_path, max_retry, ban_time, find_time). Ne
    refait aucun mapping de champ — élimine le bug historique où ce
    fichier redéfinissait son propre DTO (status: str / filter_name)
    incompatible avec ce que les appelants lisaient réellement
    (jail.active / jail.filter), ce qui faisait toujours afficher
    "Inactif" et "N/A" en 4.1 quelle que soit la réalité.

    Args:
        fail2ban_port: Fail2banPort implementation. If None, returns empty result.

    Returns:
        JailStatusResult with jails and counts.
    """
    if fail2ban_port is None:
        return JailStatusResult(
            jails=[],
            total_jails=0,
            active_jails=0,
            inactive_jails=0,
            total_banned_ips=0,
            message="⚠️ Port Fail2banPort non disponible. Les adapters infrastructure/ ne sont pas encore câblés.",
        )

    try:
        if not hasattr(fail2ban_port, "list_jails_info"):
            return JailStatusResult(
                jails=[],
                total_jails=0,
                active_jails=0,
                inactive_jails=0,
                total_banned_ips=0,
                message="⚠️ Le port ne supporte pas list_jails_info().",
            )

        jails = sorted(fail2ban_port.list_jails_info(), key=lambda j: j.name)
        active = sum(1 for j in jails if j.active)
        inactive = len(jails) - active
        total_banned = sum(j.banned_count for j in jails)

        return JailStatusResult(
            jails=jails,
            total_jails=len(jails),
            active_jails=active,
            inactive_jails=inactive,
            total_banned_ips=total_banned,
            message=f"{len(jails)} jail(s) détecté(s), {active} actif(s), {total_banned} IP(s) bannie(s).",
        )

    except Exception as e:
        return JailStatusResult(
            jails=[],
            total_jails=0,
            active_jails=0,
            inactive_jails=0,
            total_banned_ips=0,
            message=f"❌ Erreur lors de la récupération des jails : {e}",
        )


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Query read-only pour récupérer l'état des jails Fail2ban.
# - Utilisée par le menu 4.1 (État des jails).
# - Consomme le port Fail2banPort (ports/fail2ban.py).
# - Retourne un DTO structuré (JailStatusResult) + formatage pour l'UI.
#
# Pourquoi dans application/queries/ (charte) :
# - C'est une query (lecture seule), pas une command (modification).
# - Consomme un port (Fail2banPort), pas une implémentation concrète.
# - Retourne des DTOs, pas des objets d'infrastructure.
# - Ne dépend pas de infrastructure/ ni interfaces/.
#
# Ce qu'il ne contient PAS :
# ❌ Pas d'import de infrastructure/backends/fail2ban/.
# ❌ Pas d'appel système direct (fail2ban-client).
# ❌ Pas de logique métier de validation (c'est le rôle de domain/fail2ban/).
# ❌ Pas de rendu UI (c'est le rôle de interfaces/).
# ❌ Pas de modification des jails (c'est le rôle des commands).
#
# Points clés :
# - JailStatusResult : DTO de résultat (jails: list[ports.fail2ban.JailInfo], compteurs, message).
#   Ne redéfinit plus son propre DTO JailInfo local — utilise directement
#   celui du port (name, active: bool, banned_count, banned_ips: list[IPAddress],
#   filter, log_path, max_retry, ban_time, find_time). L'ancien DTO local
#   (status: str / filter_name) divergeait de ce que les appelants lisaient
#   réellement (jail.active / jail.filter) : bug corrigé en Phase 2.
# - get_jail_status() : fonction principale avec fail2ban_port optionnel.
# - Gestion d'erreur via message structuré (pas d'exception brute).
# - Fallback propre si le port n'est pas disponible.
#
# Flux d'exécution :
# interfaces/cli/actions.py : action_4_1_jails_status(ctx), et Phase 2 du
#   Menu 4 (4.4, 4.5, 4.6, 4.7, 4.8, 4.9) — point de vérité unique remplaçant
#   les blocs de parsing subprocess dupliqués.
#   ↓
# application/queries/jail_status.py : get_jail_status(fail2ban_port)
#   ↓
# ports/fail2ban.py : Fail2banPort.list_jails_info()
#   ↓
# infrastructure/backends/fail2ban/adapter.py : implémentation concrète
#   ↓
# Retourne JailStatusResult → consommé directement (JailInfo réel) par
# l'appelant, qui gère lui-même son propre rendu (interfaces/)
#---------------------------------------------------------------------->
