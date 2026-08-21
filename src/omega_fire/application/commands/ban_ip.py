# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ban IP use case.

Orchestrates banning one or more IP addresses on a SINGLE backend
(nftables, iptables, or fail2ban): checks which IPs are already
banned (never re-adds a duplicate), then bans only what's missing,
one IP at a time so each outcome is individually reported.

Method resolution uses duck-typing (ban_ip -> ban -> add_ban) rather
than a fixed signature: fail2ban's adapter exposes a different method
surface than nftables/iptables, and this project's existing menu 2
code already relies on this same fallback chain for that reason.

Conforms to Omega-Fire architecture charter:
- No direct subprocess calls (delegates entirely to the backend
  adapter, received already resolved by the caller)
- No import of infrastructure/backends/ concrete classes
- Auditing is handled by the caller (interfaces/cli/_execute_action_flow),
  not duplicated here

Replaces a previous version of this file built on the
ExecutionPlan/PipelineStep pattern (application/pipeline/planner.py),
whose steps were never implemented (placeholders only, no actual
adapter call) and which was never wired into the real application flow
(ActionRegistry never referenced it) — see docs/decisions/ for the
project-wide decision to use this simpler direct-call pattern instead,
already applied to menus 5.4/5.5/5.6, 3.1, 3.2, 3.4.
"""
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class BanIpRequest:
    """Input for the ban IP use case."""
    backend: str
    ips: list[str]
    comment: str = ""


@dataclass
class BanIpResult:
    """Output of the ban IP use case."""
    backend: str
    banned: list[str] = field(default_factory=list)
    already_banned: list[str] = field(default_factory=list)
    errors: list[tuple[str, str]] = field(default_factory=list)  # (ip, reason)

    @property
    def success(self) -> bool:
        """True if at least one IP was newly banned, or nothing needed
        banning (already fully up to date) — False only if every
        attempted IP failed."""
        return len(self.errors) == 0 or len(self.banned) > 0 or len(self.already_banned) > 0


class BanIpCommand:
    """Use case: ban a set of IPs on one backend, skipping duplicates."""

    def __init__(self, firewall_adapter: Optional[Any], ban_repository: Optional[Any] = None):
        """Initialize the command.

        Args:
            firewall_adapter: Already-resolved backend adapter
                (nftables, iptables, or fail2ban). If None, every IP
                is reported as an error — the caller decides how to
                surface that (e.g. "backend unavailable").
            ban_repository: Optional BanRepository. When provided, each
                newly-banned IP is also persisted (BanRepository was
                previously wired everywhere — dependency container,
                audit anomaly checks, the 8.1 dashboard — but never
                actually written to by any command; this was a real
                gap, not a deliberate read-only design). Persistence
                failures never affect the result: the real ban on the
                backend already succeeded by the time this runs.
        """
        self._adapter = firewall_adapter
        self._ban_repository = ban_repository

    def execute(self, request: BanIpRequest) -> BanIpResult:
        result = BanIpResult(backend=request.backend)

        if self._adapter is None:
            for ip in request.ips:
                result.errors.append((ip, f"Backend '{request.backend}' indisponible."))
            return result

        current_ips = self._list_current_ips()

        for ip in request.ips:
            if ip in current_ips:
                result.already_banned.append(ip)
                continue

            try:
                banned = self._call_ban(ip, request.comment)
                if banned:
                    result.banned.append(ip)
                    current_ips.add(ip)
                    self._persist_ban(ip, request.backend, request.comment)
                else:
                    result.errors.append((ip, "Le backend a refusé le bannissement."))
            except Exception as e:
                error_text = str(e)
                if "File exists" in error_text or "already exists" in error_text:
                    result.already_banned.append(ip)
                else:
                    result.errors.append((ip, error_text))

        return result

    def _persist_ban(self, ip: str, backend: str, comment: str) -> None:
        if self._ban_repository is None:
            return
        try:
            from omega_fire.domain.ip_blacklist.models import BanEntry, BanSource
            self._ban_repository.save(BanEntry(
                ip=ip,
                backend=backend,
                comment=comment,
                source=BanSource.MANUAL,
            ))
        except Exception:
            pass

    def _list_current_ips(self) -> set[str]:
        """Read the live banned-IP set from the adapter, tolerant to
        both dict-shaped and object-shaped ban entries."""
        current: set[str] = set()
        try:
            raw_bans = []
            if hasattr(self._adapter, "list_bans"):
                raw_bans = self._adapter.list_bans()
            elif hasattr(self._adapter, "list_banned_ips"):
                raw_bans = self._adapter.list_banned_ips()

            for item in raw_bans:
                ip = item.get("ip") if isinstance(item, dict) else getattr(item, "ip", None)
                if ip:
                    current.add(str(ip).split("/")[0].strip())
        except Exception:
            pass
        return current

    def _call_ban(self, ip: str, comment: str) -> bool:
        """Resolve and call the adapter's ban method via duck-typing."""
        if hasattr(self._adapter, "ban_ip"):
            return bool(self._adapter.ban_ip(ip=ip, comment=comment))
        elif hasattr(self._adapter, "ban"):
            return bool(self._adapter.ban(ip=ip, comment=comment))
        elif hasattr(self._adapter, "add_ban"):
            return bool(self._adapter.add_ban(ip=ip, comment=comment))
        return False


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Bannit un ensemble d'IPs sur UN SEUL backend, en ignorant celles déjà
#   bannies (jamais de doublon), une IP à la fois pour un rapport détaillé.
#
# Pourquoi dans application/commands/ (charte) :
# - Orchestration : lecture état live + calcul delta + application.
# - Ne fait AUCUN subprocess direct (contrairement à l'ancien code de
#   actions.py qu'il remplace) — entièrement délégué à l'adapter.
#
# Ce qu'il ne contient PAS :
# ❌ Pas d'import de infrastructure/backends/ (adapter reçu en paramètre)
# ❌ Pas de rendu UI
# ❌ Pas de pattern ExecutionPlan/PipelineStep (abandonné, voir docstring
#   du module — incompatible avec l'injection de paramètres)
#
# Points clés :
# - BanIpRequest : backend + liste d'IPs (même à un seul élément) + commentaire
# - BanIpResult : banned / already_banned / errors, séparés pour un
#   rapport de diagnostic précis (menus 2.1/2.2)
# - _list_current_ips() : lecture unique en début d'exécution, tolère
#   dict ou objet selon le backend
# - _call_ban() : duck-typing (ban_ip -> ban -> add_ban), nécessaire car
#   fail2ban n'expose pas la même signature que nftables/iptables
# - _persist_ban() : écrit dans BanRepository (si fourni) pour chaque IP
#   nouvellement bannie — jamais fait auparavant par aucune commande du
#   projet malgré un repository entièrement câblé ailleurs (conteneur,
#   vérifications d'anomalies 6.3, dashboard 8.1), corrigé cette session.
#   Échec de persistance silencieux : le ban réel sur le backend a déjà
#   réussi, une erreur de BDD ne doit jamais le faire paraître en échec.
#
# Flux d'exécution :
# interfaces/cli/actions.py : action_2_1_ban_ip / action_2_2_ban_list
# application/commands/ban_ip_all_backends.py : BanIpToAllBackendsCommand
#   ↓ pour chaque backend ciblé : BanIpCommand(...).execute()
#---------------------------------------------------------------------->
