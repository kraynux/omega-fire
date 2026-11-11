# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
# Porte d'omega-log (application/use_cases/access_log_stats.py) le 2026-11-09 (OMEGA-FIRE_PLAN_LOGS_NIVEAU_SERV_LOG.md) : garder identique a la source.
"""Use case Statistiques (plan_omega_log.md §2/§6) : ADAPTE depuis
omega-serv/log_stats_screen.py (source retenue) — meme principe
(periode 24h/7j/30j, top IPs, repartition horaire), mais generalise a
N'IMPORTE QUEL log de la Bibliotheque via domain/logs/{parser,
analytics}.py (generiques, Phase 2) au lieu du seul access log fixe de
SERV.

`runner` optionnel (AJOUTE 2026-10-03, plan §5.1, elevation sudo
ponctuelle) : PermissionRequiredError sans lui sur un log protege.

2026-11-06 : calcul EN FLUX par StatsAccumulator (log_tasks.py), plus jamais la liste des lignes en
memoire ; `stats` (LogStats) retire, le rapport le remplace partout."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from omega_fire.application.log_stats.log_tasks import accumulate_paths
from omega_fire.domain.log_stats.stats_report import StatsReport

if TYPE_CHECKING:
    from omega_fire.ports.log_process_runner import ProcessRunnerPort


@dataclass
class AccessLogStatsResult:
    sources: list[str]
    period: str | None
    report: StatsReport
    """Rapport complet (synthese, horaire, tendance par jour, statuts, tops), 2026-11-06."""


def compute_access_log_stats(
    paths: list[str], *, period: str | None = None, runner: ProcessRunnerPort | None = None,
) -> AccessLogStatsResult:
    """Version sequentielle (tests, CLI). L'ecran, lui, repartit les memes taches sur plusieurs processus
    (log_tasks.plan_read_tasks / run_read_task) et fusionne."""
    accumulator = accumulate_paths(paths, period=period, runner=runner)
    return AccessLogStatsResult(sources=paths, period=period, report=accumulator.to_report())
