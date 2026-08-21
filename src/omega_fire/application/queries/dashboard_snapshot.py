# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Dashboard snapshot query (menu 8.1).

Builds the DashboardSnapshot object expected by
interfaces/cli/renderers/dashboard.py::render_general_state() via its
fw_stats_provider.get_snapshot() contract — two attributes are read
WITHOUT a safe getattr() fallback (active_connections,
counters.dropped_packets), so they are mandatory on this object; every
other field is read via getattr() with a default, so partial/missing
data degrades gracefully rather than blanking the whole panel (the bug
diagnosed this session: MonitoringPort alone has neither attribute,
so every field silently fell back to "N/A").

Conforms to Omega-Fire architecture charter:
- Read-only query, no side effects
- Aggregates already-existing sources (MonitoringPort, AuditPort,
  LogAggregator, RuleRepository, BanRepository, Fail2banPort,
  FirewallPort adapters, CapabilityRegistry, active_preset_*.json) —
  introduces no new collection mechanism
- Never modifies any of the sources it reads
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

OMEGA_FIRE_VERSION = "v3.0"

# Un jail dont le nombre d'IPs actuellement bannies atteint ce seuil est
# signalé comme "pic d'activité" dans fail2ban_alerts.
_JAIL_ACTIVITY_SPIKE_THRESHOLD = 10

# Répertoire jail.d, même convention que
# infrastructure/backends/fail2ban/adapter.py::_get_static_config_from_disk()
# — utilisé ici seulement pour lister les noms configurés (glob), jamais
# pour lire le contenu (pas de duplication de logique de parsing).
_FAIL2BAN_JAIL_D_DIR = "/etc/fail2ban/jail.d"

# Les champs "lents" (get_stats() nftables/iptables, list_jails_info()
# fail2ban, collect_anomalies()) appellent de vrais sous-processus —
# fail2ban-client seul coûte ~400ms par appel (mesuré directement contre
# le binaire réel, cf. le plan de passage à l'échelle de list_jails_info()).
# Recalculés au plus une fois toutes les _SLOW_REFRESH_SECONDS plutôt qu'à
# chaque rafraîchissement (toutes les 2s) ou à chaque pression de touche
# ([t]/[a]) — la latence de plusieurs secondes constatée par l'utilisateur
# venait de ce recalcul systématique, pas d'un appel isolé trop lent.
_SLOW_REFRESH_SECONDS = 10.0

_TIMESTAMP_FORMAT = "%d/%m/%Y %H:%M"


@dataclass
class ConntrackCounters:
    """Nested object expected at snapshot.counters.dropped_packets.

    dropped_packets stays at 0: no packet-counter collection exists
    anywhere in the project (nftables/iptables counters are never
    read by any adapter built so far) — assumed empty, not invented.
    """
    dropped_packets: int = 0


@dataclass
class DashboardSnapshot:
    """Snapshot object returned by DashboardSnapshotProvider.get_snapshot().

    active_connections and counters are mandatory (read without
    getattr() fallback by render_general_state()). Every other field
    is optional from the renderer's point of view, but always
    populated here with a real value when a source exists — only
    fields with no data source anywhere in the project (drop/accept
    ratio, jail load, plugins) are left absent, so the renderer's own
    getattr() defaults (_default_fw_stats()) apply for exactly those,
    and only those.
    """
    active_connections: int
    counters: ConntrackCounters = field(default_factory=ConntrackCounters)

    active_policy: str = "N/A"
    last_sync_time: str = "N/A"
    last_sync_status: str = "N/A"
    registry_update: str = "N/A"
    version: str = OMEGA_FIRE_VERSION
    recent_actions: list = field(default_factory=list)
    top_attackers: list = field(default_factory=list)

    banned_count: int = 0
    rules_count: int = 0
    jails_count: int = 0
    active_alerts: int = 0

    last_ban: dict = field(default_factory=dict)
    last_unban: dict = field(default_factory=dict)
    fail2ban_alerts: list = field(default_factory=list)

    backend_latency: dict = field(default_factory=dict)

    last_backup: dict = field(default_factory=dict)
    config_integrity: str = "N/A"


class DashboardSnapshotProvider:
    """Use case: aggregate the dashboard's firewall-side statistics
    from existing sources — no new collection mechanism introduced."""

    def __init__(
        self,
        monitoring_port: Optional[Any],
        audit_port: Optional[Any],
        rule_repository: Optional[Any] = None,
        log_aggregator: Optional[Any] = None,
        ban_repository: Optional[Any] = None,
        fail2ban_port: Optional[Any] = None,
        firewall_ports: Optional[dict[str, Any]] = None,
        capability_registry: Optional[Any] = None,
    ):
        self._monitoring_port = monitoring_port
        self._audit_port = audit_port
        self._rule_repository = rule_repository
        self._log_aggregator = log_aggregator
        self._ban_repository = ban_repository
        self._fail2ban_port = fail2ban_port
        self._firewall_ports = firewall_ports or {}
        self._capability_registry = capability_registry

        # Cache des champs coûteux (voir _get_slow_fields()) — un
        # provider est recréé à chaque ouverture du menu 8.1
        # (action_8_1_live_dashboard), donc ce cache ne survit jamais
        # au-delà d'une seule session d'écran.
        self._slow_cache: dict = {}
        self._slow_cache_at: float = 0.0

    def get_snapshot(self) -> DashboardSnapshot:
        active_connections = self._count_connections()

        sync_time, sync_status = self._get_last_sync()
        last_ban, last_unban = self._get_last_ban_unban()
        slow = self._get_slow_fields()

        snapshot = DashboardSnapshot(
            active_connections=active_connections,
            active_policy=self._get_active_policy(),
            registry_update=self._get_registry_update(),
            recent_actions=self._get_recent_actions(),
            top_attackers=self._get_top_attackers(),
            last_sync_time=sync_time,
            last_sync_status=sync_status,
            banned_count=self._count_banned(),
            rules_count=slow["rules_count"],
            jails_count=slow["jails_count"],
            last_ban=last_ban,
            last_unban=last_unban,
            fail2ban_alerts=slow["fail2ban_alerts"],
            active_alerts=len(slow["fail2ban_alerts"]),
            backend_latency=slow["backend_latency"],
            last_backup=self._get_last_backup(),
            config_integrity=slow["config_integrity"],
        )

        return snapshot

    def _count_connections(self) -> int:
        if self._monitoring_port is None:
            return 0
        try:
            return len(self._monitoring_port.list_connections())
        except Exception:
            return 0

    def _count_banned(self) -> int:
        """Currently-active bans, all backends combined — stored state
        (BanRepository), the same source already used by
        audit_report/anomalies_section.py for its own live-vs-stored
        checks. Cheap (single DB read), refreshed every call unlike
        the subprocess-backed fields in _get_slow_fields()."""
        if self._ban_repository is None:
            return 0
        try:
            return len(self._ban_repository.find_all(status="active"))
        except Exception:
            return 0

    def _get_active_policy(self) -> str:
        """Read the first available backend's active_preset_{backend}.json
        and compare rules_count_at_apply against the current live count
        (RuleRepository.count_managed()) to detect manual drift.

        Only one state file is read: since the multi-backend apply
        fix (menu 3.4), a preset is always applied to every detected
        backend simultaneously (nftables, iptables, ip6tables —
        référentiel §58), so the state files can no longer diverge on
        which preset is active — reading one is sufficient. A backend
        that fails to apply (e.g. ip6tables not installed) simply has
        no state file, and is skipped by this loop like any other
        unavailable backend — never treated as a divergence.
        """
        import json
        from omega_fire.infrastructure.config.paths import RUNTIME_DIR
        from omega_fire.domain.rules.presets import get_preset

        for backend in ("nftables", "iptables", "ip6tables"):
            state_file = RUNTIME_DIR / f"active_preset_{backend}.json"
            if not state_file.exists():
                continue

            try:
                data = json.loads(state_file.read_text(encoding="utf-8"))
            except Exception:
                continue

            preset_key = data.get("active_preset")
            preset_obj = get_preset(preset_key) if preset_key else None
            preset_name = preset_obj.name if preset_obj else (preset_key or "Inconnu")

            rules_count_at_apply = data.get("rules_count_at_apply")
            if rules_count_at_apply is None or self._rule_repository is None:
                return preset_name

            try:
                current_count = self._rule_repository.count_managed(backend)
            except Exception:
                return preset_name

            if current_count != rules_count_at_apply:
                return f"{preset_name} + Custom"
            return preset_name

        return "Aucun"

    def _get_registry_update(self) -> str:
        """Find the most recent audit entry for a system rescan (menu
        1.3 or 7.4 — both call scanner.scan() under the hood), used as
        a proxy for "last time the capability registry was updated"
        since no dedicated timestamp is stored anywhere else.
        """
        if self._audit_port is None:
            return "N/A"

        try:
            entries = self._audit_port.get_recent(limit=100)
        except Exception:
            return "N/A"

        for entry in entries:
            if entry.action.startswith("1.3") or entry.action.startswith("7.4"):
                return entry.timestamp.strftime(_TIMESTAMP_FORMAT)

        return "N/A"

    def _get_recent_actions(self) -> list:
        """Fetch the 5 most recent audit entries, converted to the
        dict shape expected by dashboard.py::_render_recent_actions_box()
        — {"time": str, "description": str} per entry, not raw
        AuditEntry objects.
        """
        if self._audit_port is None:
            return []

        try:
            entries = self._audit_port.get_recent(limit=5)
        except Exception:
            return []

        return [
            {
                "time": entry.timestamp.strftime(_TIMESTAMP_FORMAT),
                "description": entry.action,
            }
            for entry in entries
        ]

    def _get_top_attackers(self) -> list:
        """Fetch top attacking IPs over the last 24h, converted to the
        (ip, count) tuple shape expected by dashboard.py::
        _render_top_attackers_box() — reuses LogAggregator, already
        proven for menus 8.3/8.4.
        """
        if self._log_aggregator is None:
            return []

        try:
            summary = self._log_aggregator.get_summary(period_code="24h")
        except Exception:
            return []

        return [(ip_stat.ip, ip_stat.total_bans) for ip_stat in summary.top_ips]

    def _get_last_sync(self) -> tuple:
        """Find the most recent audit entry for menu 2.6 (backend
        synchronization), returning (time_label, status_label).
        """
        if self._audit_port is None:
            return ("N/A", "N/A")

        try:
            entries = self._audit_port.get_recent(limit=100)
        except Exception:
            return ("N/A", "N/A")

        for entry in entries:
            if entry.action.startswith("2.6"):
                time_label = entry.timestamp.strftime(_TIMESTAMP_FORMAT)
                status_label = "Réussie" if entry.success else "Échec"
                return (time_label, status_label)

        return ("N/A", "N/A")

    def _get_last_ban_unban(self) -> tuple[dict, dict]:
        """Most recent ban and most recent lift, from the stored ban
        history (BanRepository) — real per-event timestamps, unlike
        Fail2banPort.list_jails_info() which only carries current
        counts/IP lists with no per-ban time.

        Reflects only bans/unbans that went through Omega-Fire's own
        commands (2.1/2.2/etc, which write to BanRepository) — a ban
        applied directly via fail2ban-client or a raw nft/iptables
        command outside the app is invisible here, by the same "stored
        vs live" boundary already documented on _get_fail2ban_alerts().
        Cheap (single DB read), refreshed every call.
        """
        if self._ban_repository is None:
            return ({}, {})

        try:
            all_bans = self._ban_repository.find_all()
        except Exception:
            return ({}, {})

        last_ban: dict = {}
        banned_sorted = sorted(all_bans, key=lambda b: b.banned_at, reverse=True)
        if banned_sorted:
            b = banned_sorted[0]
            last_ban = {
                "ip": b.ip,
                "backend": b.backend,
                "time": b.banned_at.strftime(_TIMESTAMP_FORMAT),
            }

        last_unban: dict = {}
        lifted = [b for b in all_bans if getattr(b, "removed_at", None) is not None]
        lifted_sorted = sorted(lifted, key=lambda b: b.removed_at, reverse=True)
        if lifted_sorted:
            b = lifted_sorted[0]
            last_unban = {
                "ip": b.ip,
                "time": b.removed_at.strftime(_TIMESTAMP_FORMAT),
            }

        return (last_ban, last_unban)

    def _get_last_backup(self) -> dict:
        """Most recent successful menu 7.1 execution, read from the
        audit journal — no separate storage needed: 7.1 already logs
        itself via _execute_action_flow()'s automatic audit logging,
        the same source already used by _get_registry_update()/
        _get_last_sync() above (same prefix-matching pattern). Cheap
        (single DB/file read via audit_port), refreshed every call.
        """
        if self._audit_port is None:
            return {}

        try:
            entries = self._audit_port.get_recent(limit=100)
        except Exception:
            return {}

        for entry in entries:
            if entry.action.startswith("7.1") and entry.success:
                return {
                    "date": entry.timestamp.strftime(_TIMESTAMP_FORMAT),
                    "status": "ok",
                }

        return {}

    def _get_slow_fields(self) -> dict:
        """Single collection pass for every field backed by a real
        subprocess call (nftables/iptables get_stats(), fail2ban
        list_jails_info(), collect_anomalies()'s own adapter.list_rules()
        calls) — cached for _SLOW_REFRESH_SECONDS.

        Two problems fixed at once, both root-caused to the same
        design mistake (recomputing everything from scratch on every
        build_layout() call, including the ones triggered synchronously
        by a keypress): each field used to call list_jails_info() (or
        get_stats()) a second or third time independently
        (_count_jails/_get_fail2ban_alerts/_get_backend_latency each
        called list_jails_info() separately) — now computed once and
        shared. And the whole bundle is now throttled to once per
        _SLOW_REFRESH_SECONDS instead of every 2s background tick AND
        every [t]/[a] keypress, which is what produced the multi-second
        UI freeze the user reported.
        """
        import time as _time

        now = _time.monotonic()
        if self._slow_cache and (now - self._slow_cache_at) < _SLOW_REFRESH_SECONDS:
            return self._slow_cache

        jails = []
        f2b_latency_ms = None
        if self._fail2ban_port is not None:
            try:
                start = _time.perf_counter()
                jails = self._fail2ban_port.list_jails_info()
                f2b_latency_ms = round((_time.perf_counter() - start) * 1000)
            except Exception:
                jails = []
                f2b_latency_ms = None

        backend_latency: dict[str, int] = {}
        rules_count = 0
        for backend, adapter in self._firewall_ports.items():
            if adapter is None:
                continue
            try:
                start = _time.perf_counter()
                stats = adapter.get_stats()
                backend_latency[backend] = round((_time.perf_counter() - start) * 1000)
                rules_count += stats.total_rules
            except Exception:
                continue

        if f2b_latency_ms is not None:
            backend_latency["fail2ban"] = f2b_latency_ms

        fail2ban_alerts = self._compute_fail2ban_alerts(jails)
        config_integrity = self._compute_config_integrity()

        self._slow_cache = {
            "rules_count": rules_count,
            "jails_count": len(jails),
            "fail2ban_alerts": fail2ban_alerts,
            "backend_latency": backend_latency,
            "config_integrity": config_integrity,
        }
        self._slow_cache_at = now
        return self._slow_cache

    def _compute_fail2ban_alerts(self, jails: list) -> list[str]:
        """Two independent checks, combined (validated with the user
        rather than invented unilaterally):
        1. A jail whose current ban count reaches the spike threshold
           — indicator of an ongoing attack.
        2. A jail configured on disk (jail.d/*.conf) but not currently
           loaded by the running fail2ban service — same "stored vs
           live" philosophy already used by audit_report/
           anomalies_section.py, applied here to jails specifically.

        Takes the already-fetched jail list (from _get_slow_fields())
        rather than calling list_jails_info() again — that duplicate
        call was part of the original latency bug.
        """
        alerts: list[str] = []

        loaded_names = set()
        for jail in jails:
            loaded_names.add(jail.name)
            if jail.banned_count >= _JAIL_ACTIVITY_SPIKE_THRESHOLD:
                alerts.append(
                    f"{jail.name} : {jail.banned_count} IPs bannies (pic d'activité)"
                )

        try:
            from pathlib import Path
            jail_d_dir = Path(_FAIL2BAN_JAIL_D_DIR)
            if jail_d_dir.is_dir():
                configured_names = {f.stem for f in jail_d_dir.glob("*.conf")}
                for name in sorted(configured_names - loaded_names):
                    alerts.append(f"{name} : configuré (jail.d) mais non chargé")
        except Exception:
            pass

        return alerts

    def _compute_config_integrity(self) -> str:
        """Reuses two already-audited mechanisms rather than inventing
        a third: group_rules() (domain/rules/fingerprint.py, duplicate
        rule detection by network fingerprint, already used by menu
        6.2's HTML export) and collect_anomalies() (audit_report,
        live-vs-stored inconsistencies, already used by menu 6.3).
        "ok" only if both come back clean.
        """
        duplicate_groups = []
        try:
            from omega_fire.domain.rules.fingerprint import group_rules
            rules = self._rule_repository.find_all() if self._rule_repository else []
            duplicate_groups = [g for g in group_rules(rules) if g.count > 1]
        except Exception:
            pass

        anomalies = []
        try:
            from omega_fire.application.queries.audit_report.anomalies_section import (
                collect_anomalies,
            )
            adapters = dict(self._firewall_ports)
            if self._fail2ban_port is not None:
                adapters["fail2ban"] = self._fail2ban_port
            anomalies = collect_anomalies(
                rule_repository=self._rule_repository,
                ban_repository=self._ban_repository,
                registry=self._capability_registry,
                adapters=adapters,
            )
        except Exception:
            pass

        if not duplicate_groups and not anomalies:
            return "ok"

        parts = []
        if duplicate_groups:
            parts.append(f"{len(duplicate_groups)} doublon(s) de règle")

        critical = [a for a in anomalies if getattr(a, "severity", "") == "critical"]
        if critical:
            parts.append(f"{len(critical)} anomalie(s) critique(s)")
        elif anomalies:
            parts.append(f"{len(anomalies)} anomalie(s)")

        return ", ".join(parts) if parts else "ok"


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Construit l'objet DashboardSnapshot attendu par
#   render_general_state() (menu 8.1) via son contrat
#   fw_stats_provider.get_snapshot().
#
# Pourquoi dans application/queries/ (charte) :
# - Lecture seule, aucun effet de bord.
# - Agrège des sources déjà existantes (MonitoringPort, AuditPort,
#   RuleRepository, BanRepository, Fail2banPort, adapters FirewallPort,
#   CapabilityRegistry, LogAggregator) — n'introduit aucun nouveau
#   mécanisme de collecte.
#
# Ce qu'il ne contient PAS :
# ❌ Pas de rendu UI (délégué à dashboard.py)
# ❌ Pas de collecte directe (subprocess, fichiers) — délégué aux
#    ports/services déjà existants reçus en paramètre
#
# Points clés :
# - ConntrackCounters/DashboardSnapshot : structure attendue par
#   render_general_state() — active_connections et counters.
#   dropped_packets lus SANS getattr() côté renderer, donc obligatoires
#   ici. Champs volontairement absents (défaut renderer appliqué) :
#   drop_accept_ratio, jail_load, plugins — aucune source n'existe
#   nulle part dans le projet pour ces données, assumé plutôt qu'inventé.
# - _TIMESTAMP_FORMAT ("%d/%m/%Y %H:%M") : utilisé partout où un
#   horodatage est affiché — bug corrigé cette session (l'année était
#   absente du format d'origine sur registry_update/last_sync_time/
#   recent_actions, uniquement visible en fin/début d'année).
# - _get_slow_fields() : point de collecte UNIQUE pour tout ce qui
#   déclenche un vrai sous-processus (get_stats() nftables/iptables,
#   list_jails_info() fail2ban, collect_anomalies()) — mis en cache
#   _SLOW_REFRESH_SECONDS (10s). Corrige un bug de latence réel : chaque
#   champ appelait auparavant list_jails_info()/get_stats() séparément
#   (jusqu'à 3x par rafraîchissement), et ce recalcul complet se
#   déclenchait aussi de façon synchrone à chaque pression de [t]/[a],
#   d'où les 3-6s de gel constatés par l'utilisateur.
# - _count_banned()/_get_last_ban_unban()/_get_last_backup() : lecture
#   seule (BanRepository/AuditPort), pas de sous-processus — restent
#   rafraîchis à chaque appel, pas soumis au cache lent.
# - _get_last_ban_unban() : reflète uniquement les bans/levées passés
#   par les commandes Omega-Fire (2.1/2.2/etc, qui écrivent dans
#   BanRepository) — un ban posé directement via fail2ban-client ou une
#   commande nft/iptables brute hors de l'app n'y apparaît pas, même
#   limite déjà documentée pour _compute_fail2ban_alerts().
# - _compute_fail2ban_alerts() : deux vérifications combinées (validé
#   avec l'utilisateur) — pic d'activité (banned_count ≥ seuil) et jail
#   configuré (jail.d/*.conf) mais non chargé par le service actif.
#   Prend la liste de jails déjà récupérée par _get_slow_fields(), ne
#   rappelle plus list_jails_info() elle-même.
# - _compute_config_integrity() : réutilise group_rules() (doublons de
#   règles par empreinte réseau, déjà utilisé par 6.2) et
#   collect_anomalies() (incohérences base/live, déjà utilisé par 6.3)
#   plutôt que d'inventer un 3e mécanisme — "ok" seulement si les deux
#   sont propres.
#
# Flux d'exécution :
# interfaces/cli/actions.py : action_8_1_live_dashboard(ctx)
#   ↓ instancie DashboardSnapshotProvider avec les ports/repositories résolus
# interfaces/cli/renderers/dashboard.py : fw_stats_provider.get_snapshot()
#---------------------------------------------------------------------->
