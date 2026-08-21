# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Build periodic stats report query.

Orchestrates the collection of data from three independent sources —
LogAggregator (ban/jail activity), AuditLogger (operator activity),
PersistencePort (rule/ban count evolution via snapshots) — unpacks
their respective dataclasses into plain primitives, and delegates the
actual report construction to domain/reports/service.py::build_stats_report()
(which never depends on core.stats.models or ports.* directly — see
that method's docstring).

Used by menus 8.3 (7-day report) and 8.4 (30-day report).

Conforms to Omega-Fire architecture charter:
- Read-only query, no side effects
- Consumes ports (AuditPort, PersistencePort) and infrastructure
  services received already resolved by the caller — never imports
  infrastructure/backends/ or infrastructure/logging/ concrete classes
  directly except LogAggregator, which lives in infrastructure/logging/
  stats/ specifically for this purpose (no port abstraction exists for
  it yet — same pattern already used by menu 5.8's log_stats_view.py)
- Delegates report construction to domain/reports/service.py — never
  builds the Report object's sections itself
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional

from omega_fire.domain.reports.service import ReportsService
from omega_fire.domain.reports.builders import Report
from omega_fire.infrastructure.logging.stats.log_aggregator import LogAggregator


@dataclass
class BuildStatsReportRequest:
    """Input for the build-stats-report use case."""
    period_code: str  # "7d" or "30d"
    period_label: str  # "7 jours" or "30 jours"


@dataclass
class BuildStatsReportResult:
    """Output of the build-stats-report use case.

    Carries both the assembled Report (ready for HTML export via
    HtmlExporter.export_report()) and the raw data used to build it
    (ready for direct CLI rendering via interfaces/cli/renderers/stats/,
    avoiding an unnecessary round-trip through Report's generic
    dict-based sections just to redisplay what was just assembled).
    """
    success: bool
    report: Optional[Report] = None
    kpi: dict = field(default_factory=dict)
    hourly_series: list = field(default_factory=list)
    daily_trend: list = field(default_factory=list)
    top_ips: list = field(default_factory=list)
    top_jails: list = field(default_factory=list)
    management: dict = field(default_factory=dict)
    rules_evolution: list = field(default_factory=list)
    message: str = ""


class BuildStatsReportQuery:
    """Use case: assemble a full periodic stats report from three
    independent sources."""

    def __init__(
        self,
        audit_port: Optional[Any],
        persistence_port: Optional[Any],
        log_aggregator: Optional[LogAggregator] = None,
    ):
        """Initialize the query.

        Args:
            audit_port: Already-resolved AuditPort implementation
                (ctx.container.get_audit_port()). If None, the
                "Gestion" section is built empty rather than failing
                the whole report.
            persistence_port: Already-resolved PersistencePort
                implementation (ctx.container.get_persistence_port()).
                If None, the "Évolution des Règles" section is built
                empty rather than failing the whole report.
            log_aggregator: Optional pre-built LogAggregator. If None,
                a default instance is created (same defaults as menu
                5.8's log_stats_view.py).
        """
        self._audit_port = audit_port
        self._persistence_port = persistence_port
        self._aggregator = log_aggregator or LogAggregator()

    def execute(self, request: BuildStatsReportRequest) -> BuildStatsReportResult:
        try:
            summary = self._aggregator.get_summary(period_code=request.period_code)
            daily_trend = self._aggregator.get_daily_trend(period_code=request.period_code)
        except Exception as e:
            return BuildStatsReportResult(
                success=False,
                message=f"Erreur lors de l'agrégation des logs : {e}",
            )

        kpi = {
            "total_events": summary.total_events,
            "total_bans": summary.total_bans,
            "top_jail_name": summary.top_jail_name,
            "peak_hour": summary.peak_hour,
            "peak_count": summary.peak_count,
            "data_source": summary.data_source,
        }

        top_ips = [
            {"ip": s.ip, "total_bans": s.total_bans, "last_ban": s.last_ban.isoformat()}
            for s in summary.top_ips
        ]
        top_jails = [
            {"name": j.name, "total_bans": j.total_bans, "is_active": j.is_active, "percentage": j.percentage}
            for j in summary.top_jails
        ]

        period_delta = self._aggregator.PERIOD_MAP.get(request.period_code, timedelta(days=7))
        since = datetime.now() - period_delta

        management = self._build_management_section(since)
        rules_evolution = self._build_rules_evolution_section(since)

        try:
            report = ReportsService().build_stats_report(
                period_label=request.period_label,
                kpi=kpi,
                hourly_series=summary.hourly_series,
                daily_trend=daily_trend,
                top_ips=top_ips,
                top_jails=top_jails,
                management=management,
                rules_evolution=rules_evolution,
                title=f"Rapport Statistique — {request.period_label}",
            )
        except Exception as e:
            return BuildStatsReportResult(
                success=False,
                message=f"Erreur lors de la construction du rapport : {e}",
            )

        return BuildStatsReportResult(
            success=True,
            report=report,
            kpi=kpi,
            hourly_series=summary.hourly_series,
            daily_trend=daily_trend,
            top_ips=top_ips,
            top_jails=top_jails,
            management=management,
            rules_evolution=rules_evolution,
        )

    def _build_management_section(self, since: datetime) -> dict:
        """Filter audit.log entries since the given date into the
        counters expected by domain's build_stats_report()."""
        empty = {
            "rule_changes": 0,
            "backups": 0,
            "restores": 0,
            "total_actions": 0,
            "success_rate": 0.0,
            "recent_entries": [],
        }

        if self._audit_port is None:
            return empty

        try:
            entries = self._audit_port.get_all_since(since=since)
        except Exception:
            return empty

        if not entries:
            return empty

        rule_changes = sum(
            1 for e in entries
            if e.action.startswith("rule_") or e.action.startswith("apply_preset")
        )
        backups = sum(1 for e in entries if e.action.startswith("backup"))
        restores = sum(1 for e in entries if e.action.startswith("restore"))
        total_actions = len(entries)
        success_count = sum(1 for e in entries if e.success)
        success_rate = (success_count / total_actions * 100.0) if total_actions > 0 else 0.0

        recent_sorted = sorted(entries, key=lambda e: e.timestamp, reverse=True)[:8]
        recent_entries = [
            (e.timestamp.strftime("%d/%m %H:%M"), e.action, e.success)
            for e in recent_sorted
        ]

        return {
            "rule_changes": rule_changes,
            "backups": backups,
            "restores": restores,
            "total_actions": total_actions,
            "success_rate": success_rate,
            "recent_entries": recent_entries,
        }

    def _build_rules_evolution_section(self, since: datetime) -> list:
        """Filter snapshots (list_snapshots() has no built-in date
        filter, unlike audit's get_all_since()) into chronologically
        sorted (label, rules_count, ips_count) points."""
        if self._persistence_port is None:
            return []

        try:
            all_snapshots = self._persistence_port.list_snapshots()
        except Exception:
            return []

        in_period = [s for s in all_snapshots if s.created_at >= since]
        in_period.sort(key=lambda s: s.created_at)

        return [
            (s.created_at.strftime("%d/%m %H:%M"), s.rules_count, s.blacklist_count)
            for s in in_period
        ]


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Orchestre la collecte depuis 3 sources indépendantes (LogAggregator
#   pour l'activité de ban/jail, AuditLogger pour l'activité opérateur,
#   PersistencePort pour l'évolution règles/IPs via snapshots) et
#   délègue la construction du Report à domain/reports/service.py.
# - Alimente les menus 8.3 (7 jours) et 8.4 (30 jours).
#
# Pourquoi dans application/queries/ (charte) :
# - Requête de lecture seule, aucun effet de bord.
# - Ne construit jamais lui-même les sections du Report — délégué
#   entièrement à ReportsService.build_stats_report() (domain/).
# - Dépaquette les dataclasses de core/ (LogStatsSummary, JailStat,
#   IpStat) et de ports/ (AuditEntry, Snapshot) en primitives, seule
#   couche autorisée à connaître ces deux mondes à la fois.
#
# Ce qu'il ne contient PAS :
# ❌ Pas d'accès direct à SQLite/fichiers (délégué à LogAggregator)
# ❌ Pas de construction de sections de rapport (délégué au domaine)
# ❌ Pas de rendu UI ni HTML
#
# Points clés :
# - BuildStatsReportRequest : period_code ("7d"/"30d") + period_label
#   (affiché tel quel dans le rapport)
# - BuildStatsReportResult : porte À LA FOIS le Report assemblé (pour
#   export HTML) ET les données brutes (pour affichage CLI direct via
#   interfaces/cli/renderers/stats/) — évite un aller-retour inutile
#   par les sections génériques du Report juste pour réafficher ce
#   qu'on vient de construire
# - _build_management_section() : filtre get_all_since() par préfixe
#   d'action (rule_/apply_preset/backup/restore), taux de succès sur
#   TOUTES les entrées de la période (pas seulement ces 3 catégories)
# - _build_rules_evolution_section() : list_snapshots() n'a pas de
#   filtre by-date intégré (contrairement à get_all_since()) —
#   filtrage manuel sur created_at ici
# - audit_port/persistence_port optionnels (None accepté) : une source
#   indisponible ne fait jamais échouer tout le rapport, section vide
#   à la place — même philosophie de dégradation que le reste du projet
#
# Flux d'exécution :
# interfaces/cli/actions.py : action_8_3_stats_7_days / action_8_4_stats_30_days
#   ↓ résout audit_port/persistence_port via ctx.container
# application/queries/build_stats_report.py : BuildStatsReportQuery.execute()
#   ↓ LogAggregator.get_summary()/get_daily_trend() (infrastructure/logging/stats/)
#   ↓ audit_port.get_all_since() (infrastructure/logging/audit_logger.py)
#   ↓ persistence_port.list_snapshots() (infrastructure/storage/files/persistence_adapter.py)
#   ↓ ReportsService.build_stats_report() (domain/reports/service.py)
#---------------------------------------------------------------------->
