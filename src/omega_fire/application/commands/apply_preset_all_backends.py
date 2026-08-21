# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Apply firewall preset to all detected backends use case.

Orchestrates applying a single predefined firewall profile (menu 3.4)
across every backend adapter available on the system (nftables and/or
iptables and/or ip6tables), so that the applied profile is truly
representative of the system's real filtering behavior — never
partially applied on one backend while an older, contradictory profile
stays silently active on another (confirmed in real testing: two
chains sharing the same netfilter hook combine as an intersection, so
a restrictive profile active on only one backend already blocks
traffic even if another backend looks permissive — but the reverse
confusion, a permissive profile that LOOKS applied while an old
restrictive profile still blocks everything on another backend, is
exactly what this command exists to prevent). This reasoning applies
identically to ip6tables (référentiel §53-58, plan IPv6 iptables) : an
IPv4-only-applied profile would leave IPv6 traffic silently governed by
whatever policy ip6tables had before.

Captures exactly ONE full multi-backend snapshot before touching any
backend (never one snapshot per backend) — 7.2 always offers a single
coherent restore point per profile change, never an intermediate,
partially-transitioned state as a snapshot.

Each backend is applied independently via ApplyPresetCommand — a
failure on one backend never rolls back a success already achieved on
another (cross-backend rollback would itself be a new source of risk,
on top of the flush/policy risks already mitigated elsewhere). The
outcome is reported per backend so the caller always knows the true,
possibly mixed, result rather than a single collapsed status.

Conforms to Omega-Fire architecture charter:
- No direct subprocess/SQL calls (delegates to ApplyPresetCommand per
  backend, which itself delegates to the backend adapter)
- No hardcoded runtime paths
- Auditing is handled by the caller (interfaces/cli/_execute_action_flow),
  not duplicated here
"""
from dataclasses import dataclass, field
from typing import Any, Optional

from omega_fire.domain.rules.presets import FirewallPreset
from omega_fire.application.commands.apply_preset import (
    ApplyPresetCommand,
    ApplyPresetRequest,
)
from omega_fire.application.commands.backup_state import _collect_banned_ips, _collect_jails


@dataclass
class ApplyPresetAllBackendsRequest:
    """Input for the apply-preset-to-all-backends use case."""
    preset: FirewallPreset


@dataclass
class BackendApplyOutcome:
    """Result of applying the preset to a single backend."""
    backend: str
    success: bool
    message: str


@dataclass
class ApplyPresetAllBackendsResult:
    """Output of the apply-preset-to-all-backends use case."""
    success: bool  # True if AT LEAST one backend succeeded
    outcomes: list[BackendApplyOutcome] = field(default_factory=list)
    snapshot_warning: Optional[str] = None


class ApplyPresetToAllBackendsCommand:
    """Use case: apply a single FirewallPreset to every detected backend."""

    def __init__(
        self,
        adapters: dict[str, Any],
        persistence_port: Any = None,
        rule_repository: Any = None,
    ):
        """Initialize the command.

        Args:
            adapters: Mapping of ALL resolved backend adapters (nftables,
                iptables, ip6tables, fail2ban). Only "nftables", "iptables"
                and "ip6tables" keys with a non-None value are targeted for
                preset application; "fail2ban" (if present) is used only
                for the full snapshot capture below, never for preset
                application itself (presets never touch fail2ban jails).
            persistence_port: Optional PersistencePort implementation, used
                to store ONE multi-backend snapshot (origin="auto_preset")
                before touching any backend. If None, the capture is
                skipped (dégradé, jamais bloquant).
            rule_repository: Optional RuleRepository instance, forwarded to
                each per-backend ApplyPresetCommand for its own DB sync.
        """
        self._adapters = adapters
        self._persistence_port = persistence_port
        self._rule_repository = rule_repository

    def execute(self, request: ApplyPresetAllBackendsRequest) -> ApplyPresetAllBackendsResult:
        target_backends = [
            name for name in ("nftables", "iptables", "ip6tables")
            if self._adapters.get(name) is not None
        ]

        if not target_backends:
            return ApplyPresetAllBackendsResult(
                success=False,
                outcomes=[],
                snapshot_warning="Aucun backend firewall disponible pour appliquer un profil.",
            )

        snapshot_warning = None
        if self._persistence_port is not None:
            try:
                self._capture_full_snapshot(request.preset, target_backends)
            except Exception as e:
                snapshot_warning = f"snapshot complet non créé ({e})"

        outcomes: list[BackendApplyOutcome] = []
        for backend in target_backends:
            # Chaque backend reçoit sa PROPRE instance d'ApplyPresetCommand,
            # avec persistence_port=None et adapters=None : le snapshot
            # global a déjà été capturé UNE SEULE fois ci-dessus, avant de
            # toucher le premier backend — le repasser ici recapturerait un
            # snapshot par backend (état partiellement transitionné), ce
            # que ce module existe justement pour éviter.
            single_result = ApplyPresetCommand(
                firewall_adapter=self._adapters[backend],
                adapters=None,
                persistence_port=None,
                rule_repository=self._rule_repository,
            ).execute(ApplyPresetRequest(preset=request.preset, backend=backend))

            outcomes.append(BackendApplyOutcome(
                backend=backend,
                success=single_result.success,
                message=single_result.message,
            ))

        overall_success = any(o.success for o in outcomes)

        return ApplyPresetAllBackendsResult(
            success=overall_success,
            outcomes=outcomes,
            snapshot_warning=snapshot_warning,
        )

    def _capture_full_snapshot(self, preset: FirewallPreset, target_backends: list[str]) -> None:
        """Capture l'état complet (tous backends) UNE SEULE fois, avant de
        toucher le premier backend — voir docstring du module.
        """
        banned_ips = _collect_banned_ips({
            k: v for k, v in self._adapters.items()
            if k in ("nftables", "iptables", "ip6tables", "fail2ban")
        })

        rules = []
        for backend_name in ("nftables", "iptables", "ip6tables"):
            backend_adapter = self._adapters.get(backend_name)
            if backend_adapter is None:
                continue
            try:
                rules.extend(backend_adapter.list_rules())
            except Exception:
                continue

        jails = _collect_jails(self._adapters.get("fail2ban"))

        self._persistence_port.create_snapshot(
            banned_ips=banned_ips,
            rules=rules,
            jails=jails,
            description=(
                f"Auto — avant application du profil '{preset.name}' "
                f"sur {', '.join(target_backends)}"
            ),
            origin="auto_preset",
        )


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Applique un profil (domain/rules/presets.py) à TOUS les backends
#   détectés (nftables + iptables + ip6tables), au lieu d'un choix
#   unique, pour que le profil reste représentatif de l'état réel
#   combiné du système.
# - Capture le snapshot complet multi-backend UNE SEULE fois, avant de
#   toucher le premier backend.
# - N'effectue jamais de rollback croisé entre backends : un échec sur
#   l'un n'annule jamais un succès déjà obtenu sur l'autre.
#
# Pourquoi dans application/commands/ (charte) :
# - Orchestration de haut niveau (boucle sur backends, agrégation de
#   résultats) — ne fait aucun subprocess/SQL direct, délégué entièrement
#   à ApplyPresetCommand (inchangée) et à FileBackupAdapter.
#
# Ce qu'il ne contient PAS :
# ❌ Pas d'import de infrastructure/backends/ (adapters reçus en paramètre)
# ❌ Pas de rendu UI
# ❌ Pas de logique de flush/application nft/iptables (déléguée à
#    ApplyPresetCommand, elle-même déléguée aux adapters)
#
# Points clés :
# - ApplyPresetAllBackendsRequest : uniquement le preset (plus de choix
#   de backend, contrairement à ApplyPresetRequest qu'elle encapsule)
# - BackendApplyOutcome : résultat individuel par backend (backend,
#   success, message) — jamais fusionné en un seul statut opaque
# - ApplyPresetAllBackendsResult.success : True si AU MOINS un backend a
#   réussi (succès partiel toujours possible et toujours rapporté en détail
#   via outcomes, jamais masqué)
#
# Flux d'exécution :
# interfaces/cli/actions.py : action_3_4_apply_preset(ctx)
#   ↓ résout preset_adapters (dict complet, y compris fail2ban)
# application/commands/apply_preset_all_backends.py :
#   ApplyPresetToAllBackendsCommand.execute()
#   ↓ _capture_full_snapshot() (une fois)
#   ↓ pour chaque backend : ApplyPresetCommand(...).execute() (inchangée)
#---------------------------------------------------------------------->
