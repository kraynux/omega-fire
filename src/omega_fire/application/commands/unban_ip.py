# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Unban IP use case.

Orchestrates unbanning one or more IP addresses on a SINGLE backend
(nftables, iptables, or fail2ban): only acts on IPs actually present,
one IP at a time so each outcome is individually reported. Never
raises for an IP that was already free — that already satisfies the
goal.

Method resolution uses duck-typing (unban_ip -> unban -> remove_ban),
same reasoning as ban_ip.py — see that module's docstring.

Conforms to Omega-Fire architecture charter:
- No direct subprocess calls (delegates entirely to the backend
  adapter, received already resolved by the caller) — replaces the
  previous direct 'iptables -D ...' subprocess call that lived in
  interfaces/cli/actions.py, a charter violation this command exists
  to remove
- No import of infrastructure/backends/ concrete classes
- Auditing is handled by the caller (interfaces/cli/_execute_action_flow),
  not duplicated here

Replaces a previous version of this file built on the
ExecutionPlan/PipelineStep pattern, whose steps were never implemented
(placeholders only) and which was never wired into the real
application flow — same rationale as ban_ip.py.
"""
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class UnbanIpRequest:
    """Input for the unban IP use case."""
    backend: str
    ips: list[str]


@dataclass
class UnbanIpResult:
    """Output of the unban IP use case."""
    backend: str
    unbanned: list[str] = field(default_factory=list)
    already_free: list[str] = field(default_factory=list)
    errors: list[tuple[str, str]] = field(default_factory=list)  # (ip, reason)

    @property
    def success(self) -> bool:
        """True unless every attempted IP hit a real error."""
        return len(self.errors) == 0 or len(self.unbanned) > 0 or len(self.already_free) > 0


class UnbanIpCommand:
    """Use case: unban a set of IPs on one backend, skipping IPs
    already free."""

    def __init__(self, firewall_adapter: Optional[Any], ban_repository: Optional[Any] = None):
        """Initialize the command.

        Args:
            firewall_adapter: Already-resolved backend adapter
                (nftables, iptables, or fail2ban). If None, every IP
                is reported as an error.
            ban_repository: Optional BanRepository. When provided, each
                unbanned IP has its active BanRepository row (if any)
                marked removed — mirrors ban_ip.py's own persistence,
                same previously-missing wiring. No error if no matching
                row exists (e.g. the ban predates this fix, or was
                applied outside Omega-Fire): the real unban already
                succeeded on the backend regardless.
        """
        self._adapter = firewall_adapter
        self._ban_repository = ban_repository

    def execute(self, request: UnbanIpRequest) -> UnbanIpResult:
        result = UnbanIpResult(backend=request.backend)

        if self._adapter is None:
            for ip in request.ips:
                result.errors.append((ip, f"Backend '{request.backend}' indisponible."))
            return result

        current_ips = self._list_current_ips()

        for ip in request.ips:
            if ip not in current_ips:
                result.already_free.append(ip)
                continue

            try:
                unbanned = self._call_unban(ip)
                if unbanned:
                    result.unbanned.append(ip)
                    current_ips.discard(ip)
                    self._persist_unban(ip, request.backend)
                else:
                    result.errors.append((ip, "Le backend a refusé le débannissement."))
            except Exception as e:
                error_text = str(e)
                lowered = error_text.lower()
                if "no such file or directory" in lowered or "does not exist" in lowered or "bad rule" in lowered:
                    # Déjà absente du noyau : l'objectif (IP non bloquée)
                    # est déjà atteint, ce n'est pas une vraie erreur.
                    result.already_free.append(ip)
                else:
                    result.errors.append((ip, error_text))

        return result

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

    def _call_unban(self, ip: str) -> bool:
        """Resolve and call the adapter's unban method via duck-typing."""
        if hasattr(self._adapter, "unban_ip"):
            return bool(self._adapter.unban_ip(ip=ip))
        elif hasattr(self._adapter, "unban"):
            return bool(self._adapter.unban(ip=ip))
        elif hasattr(self._adapter, "remove_ban"):
            return bool(self._adapter.remove_ban(ip=ip))
        return False

    def _persist_unban(self, ip: str, backend: str) -> None:
        if self._ban_repository is None:
            return
        try:
            self._ban_repository.mark_removed_by_ip(ip, backend, removed_by="user")
        except Exception:
            pass


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Débannit un ensemble d'IPs sur UN SEUL backend, en ignorant celles
#   déjà libres, une IP à la fois pour un rapport détaillé.
#
# Pourquoi dans application/commands/ (charte) :
# - Orchestration : lecture état live + calcul delta + application.
# - Ne fait AUCUN subprocess direct — remplace l'ancien appel
#   'iptables -D INPUT -s IP -j DROP' qui vivait directement dans
#   interfaces/cli/actions.py (violation de charte corrigée ici).
#
# Ce qu'il ne contient PAS :
# ❌ Pas d'import de infrastructure/backends/ (adapter reçu en paramètre)
# ❌ Pas de rendu UI
# ❌ Pas de pattern ExecutionPlan/PipelineStep (abandonné, voir docstring
#   du module)
#
# Points clés :
# - UnbanIpRequest : backend + liste d'IPs (même à un seul élément)
# - UnbanIpResult : unbanned / already_free / errors, séparés pour un
#   rapport de diagnostic précis (menus 2.3/2.4/2.9)
# - Erreurs "règle absente" traitées comme already_free, pas comme échec
#   réel : l'objectif (IP non bloquée) est déjà atteint
# - _persist_unban() : marque la ligne BanRepository correspondante
#   comme retirée (status='removed', removed_at/removed_by) via
#   mark_removed_by_ip() — symétrique de ban_ip.py::_persist_ban(),
#   même correctif de session (repository jamais écrit auparavant).
# - _call_unban() : duck-typing (unban_ip -> unban -> remove_ban)
#
# Flux d'exécution :
# interfaces/cli/actions.py : action_2_3_unban_ip / action_2_4_unban_list / action_2_9_flush_backends
# application/commands/unban_ip_all_backends.py : UnbanIpToAllBackendsCommand
#   ↓ pour chaque backend ciblé : UnbanIpCommand(...).execute()
#---------------------------------------------------------------------->
