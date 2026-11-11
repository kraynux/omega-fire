# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
# Porte d'omega-log (interfaces/tui/screens/_parallel_compute.py) le 2026-11-09 (OMEGA-FIRE_PLAN_LOGS_NIVEAU_SERV_LOG.md) : garder identique a la source.
"""Repartit les taches de lecture (application/use_cases/log_tasks.py) sur le pool de processus et
fusionne leurs agregats DANS L'ORDRE des taches (resultat identique a une lecture d'un bloc) - commun a
Statistiques et « Voir et traiter IP » (2026-11-06).

Un log protege (apres authentification) est LU avec sudo par le processus principal, dans un thread, puis
seulement ANALYSE dans le pool (porte d'omega-serv, 2026-11-07) : un processus du pool ne lance jamais sudo -
avec `timestamp_type=ppid` dans sudoers, il ne verrait pas l'authentification faite par l'interface.

Progression REELLE : `on_progress(octets_faits, octets_total, taches_faites, taches_total)` a chaque
morceau termine. Annulation (ecran ferme, Textual annule son worker) : les morceaux pas encore demarres
sont annules, jamais lances pour rien. Une erreur d'un morceau (PermissionRequiredError notamment)
annule les autres et remonte telle quelle a l'ecran."""
from __future__ import annotations

import asyncio
import functools
from collections.abc import Callable
from typing import TYPE_CHECKING

from omega_fire.application.log_stats.log_tasks import (
    ReadTask,
    accumulate_text,
    plan_read_tasks,
    read_privileged_text,
    run_read_task,
)
from omega_fire.domain.log_stats.stats_accumulator import StatsAccumulator
from omega_fire.infrastructure.log_stats.process_pool import POOL_WORKERS, STATS_PROCESS_POOL
from omega_fire.infrastructure.log_stats.elevation import PermissionRequiredError

if TYPE_CHECKING:
    from omega_fire.ports.log_process_runner import ProcessRunnerPort


async def _run_one(task: ReadTask, runner: ProcessRunnerPort | None) -> StatsAccumulator:
    loop = asyncio.get_running_loop()
    if task.privileged:
        if runner is None:
            raise PermissionRequiredError(task.path)
        # Lecture sudo dans CE processus (un thread : c'est de l'attente), analyse dans le pool.
        text = await loop.run_in_executor(None, read_privileged_text, runner, task.path)
        return await loop.run_in_executor(
            STATS_PROCESS_POOL, functools.partial(accumulate_text, text, task.path, task.cutoff))
    return await loop.run_in_executor(STATS_PROCESS_POOL, functools.partial(run_read_task, task))


async def run_read_tasks(
    tasks: list[ReadTask], runner: ProcessRunnerPort | None,
    on_progress: Callable[[int, int, int, int], None] | None = None,
) -> StatsAccumulator:
    futures = [asyncio.ensure_future(_run_one(task, runner)) for task in tasks]
    index_of = {future: index for index, future in enumerate(futures)}
    results: list[StatsAccumulator | None] = [None] * len(tasks)
    total_weight = sum(task.weight for task in tasks)
    done_weight, done_tasks = 0, 0
    pending = set(futures)
    try:
        while pending:
            done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
            for future in done:
                index = index_of[future]
                results[index] = future.result()  # leve l'erreur du morceau, le finally annule les autres
                done_weight += tasks[index].weight
                done_tasks += 1
            if on_progress is not None:
                on_progress(done_weight, total_weight, done_tasks, len(tasks))
    finally:
        for future in pending:
            future.cancel()
    total = StatsAccumulator()
    for result in results:
        if result is not None:
            total.merge(result)
    return total


async def accumulate_in_pool(
    paths: list[str], period: str | None, runner: ProcessRunnerPort | None,
    on_progress: Callable[[int, int, int, int], None] | None = None,
) -> StatsAccumulator:
    """Planifie (processus principal, rapide) puis execute en parallele. PermissionRequiredError possible
    des la planification (fichier protege)."""
    tasks = plan_read_tasks(paths, period=period, workers=POOL_WORKERS, runner=runner)
    if on_progress is not None:
        on_progress(0, sum(task.weight for task in tasks), 0, len(tasks))
    return await run_read_tasks(tasks, runner, on_progress)
