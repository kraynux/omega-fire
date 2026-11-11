# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
# Porte d'omega-log (application/use_cases/log_tasks.py) le 2026-11-09 (OMEGA-FIRE_PLAN_LOGS_NIVEAU_SERV_LOG.md) : garder identique a la source.
"""Lecture des logs en taches paralleles pour Statistiques et « Voir et traiter IP » (2026-11-06, retour
utilisateur : « il y a des logs plus gros de serveurs »).

- `plan_read_tasks` (processus principal, rapide) : decoupe chaque fichier lu en entier en morceaux
  ALIGNES sur des fins de ligne (aucune ligne coupee en deux, aucune comptee deux fois) ;
- `run_read_task` (un processus du pool par morceau) : lit son morceau en flux, analyse chaque ligne et
  rend un `StatsAccumulator` - jamais la liste des lignes ;
- l'appelant fusionne les accumulateurs dans l'ordre des taches : resultat identique a une lecture d'un bloc.

Periodes 24h/7j/30j : une seule tache par fichier, lecture depuis la FIN avec arret anticipe (deja rapide,
voir _log_reading.py). Fichier protege : une seule tache, lecture privilegiee (sudo) si `runner` est
fourni, sinon PermissionRequiredError (l'ecran demande l'authentification puis relance)."""
from __future__ import annotations

import os
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from itertools import pairwise
from typing import TYPE_CHECKING

from omega_fire.application.log_stats._log_reading import (
    _MAX_CONSECUTIVE_OLD_LINES,
    PERIOD_TO_TIMEDELTA,
    _iter_lines_reverse,
)
from omega_fire.domain.log_stats.parser import parse_log_line
from omega_fire.domain.log_stats.stats_accumulator import StatsAccumulator
from omega_fire.infrastructure.log_stats.elevation import PermissionRequiredError
from omega_fire.infrastructure.log_stats.privileged_file_ops import read_file_privileged

if TYPE_CHECKING:
    from omega_fire.ports.log_process_runner import ProcessRunnerPort

MIN_CHUNK_BYTES = 8 * 1024 * 1024
"""Sous 8 Mo, un fichier reste en un morceau : le lancement d'une tache coute plus que l'analyse."""
_BLOCK_BYTES = 1024 * 1024


@dataclass(frozen=True)
class ReadTask:
    path: str
    start: int = 0
    end: int | None = None
    """Octets [start, end) du fichier ; end None = jusqu'a la fin."""
    period: str | None = None
    cutoff: datetime | None = None
    privileged: bool = False
    weight: int = 0
    """Octets couverts, pour la progression affichee (0 si inconnu)."""


def _aligned_boundaries(path: str, size: int, parts: int) -> list[int]:
    """Bornes des morceaux, chacune juste apres une fin de ligne."""
    bounds = [0]
    with open(path, "rb") as handle:
        for index in range(1, parts):
            handle.seek(size * index // parts)
            handle.readline()
            position = handle.tell()
            if bounds[-1] < position < size:
                bounds.append(position)
    bounds.append(size)
    return bounds


def plan_read_tasks(
    paths: list[str], *, period: str | None = None, now: datetime | None = None, workers: int = 1,
    runner: ProcessRunnerPort | None = None,
) -> list[ReadTask]:
    """Taches de lecture de `paths`. Leve PermissionRequiredError pour un fichier protege sans `runner`."""
    cutoff = (now or datetime.now()) - PERIOD_TO_TIMEDELTA[period] if period is not None else None
    tasks: list[ReadTask] = []
    for path in paths:
        try:
            size = os.path.getsize(path)
            readable = os.access(path, os.R_OK)
        except OSError:
            continue  # absent : rien a lire (meme comportement qu'avant)
        if not readable:
            if runner is None:
                raise PermissionRequiredError(path)
            tasks.append(ReadTask(path, period=period, cutoff=cutoff, privileged=True, weight=size))
            continue
        if period is not None:
            tasks.append(ReadTask(path, period=period, cutoff=cutoff, weight=size))
            continue
        parts = max(1, min(workers * 4, size // MIN_CHUNK_BYTES))
        try:
            bounds = _aligned_boundaries(path, size, parts) if parts > 1 else [0, size]
        except PermissionError:
            if runner is None:
                raise PermissionRequiredError(path) from None
            tasks.append(ReadTask(path, privileged=True, weight=size))
            continue
        except OSError:
            continue
        tasks.extend(ReadTask(path, start, end, weight=end - start) for start, end in pairwise(bounds))
    return tasks


def _iter_range(path: str, start: int, end: int | None) -> Iterator[str]:
    """Lignes des octets [start, end), lues par blocs de 1 Mo (jamais tout le morceau d'un coup)."""
    with open(path, "rb") as handle:
        handle.seek(start)
        remaining = None if end is None else end - start
        rest = b""
        while remaining is None or remaining > 0:
            block = handle.read(_BLOCK_BYTES if remaining is None else min(_BLOCK_BYTES, remaining))
            if not block:
                break
            if remaining is not None:
                remaining -= len(block)
            lines = (rest + block).split(b"\n")
            rest = lines.pop()
            for raw in lines:
                yield raw.decode("utf-8", errors="replace")
        if rest:
            yield rest.decode("utf-8", errors="replace")


def read_privileged_text(runner: ProcessRunnerPort, path: str) -> str:
    """Lecture sudo d'un log protege, dans le processus PRINCIPAL (porte d'omega-serv, 2026-11-07)."""
    result = read_file_privileged(runner, path)
    return result.content if result.success else ""


def accumulate_text(text: str, path: str, cutoff: datetime | None) -> StatsAccumulator:
    """Analyse d'un log deja lu avec sudo par le processus PRINCIPAL (porte d'omega-serv, 2026-11-07) : les
    processus du pool ne lancent jamais sudo eux-memes - avec `timestamp_type=ppid` dans sudoers, ils ne
    verraient pas l'authentification que vous venez de faire."""
    accumulator = StatsAccumulator()
    for line in text.splitlines():
        entry = parse_log_line(line, log_path=path)
        if entry is not None and (cutoff is None or entry.timestamp >= cutoff):
            accumulator.add(entry)
    return accumulator


def run_read_task(task: ReadTask, runner: ProcessRunnerPort | None = None) -> StatsAccumulator:
    """Analyse les lignes du morceau, rend leurs agregats. Un morceau privilegie n'est jamais confie au pool
    (voir interfaces/tui/screens/_parallel_compute.py) : ici seulement en lecture sequentielle (CLI, tests)."""
    accumulator = StatsAccumulator()
    if task.privileged:
        if runner is None:
            raise PermissionRequiredError(task.path)
        return accumulate_text(read_privileged_text(runner, task.path), task.path, task.cutoff)
    try:
        if task.period is not None:
            _accumulate_period(task, accumulator)
        else:
            for line in _iter_range(task.path, task.start, task.end):
                entry = parse_log_line(line, log_path=task.path)
                if entry is not None:
                    accumulator.add(entry)
    except PermissionError:
        raise PermissionRequiredError(task.path) from None
    except OSError:
        pass
    return accumulator


def _accumulate_period(task: ReadTask, accumulator: StatsAccumulator) -> None:
    """Depuis la fin du fichier, arret apres _MAX_CONSECUTIVE_OLD_LINES lignes consecutives trop anciennes
    (meme regle que _log_reading._read_entries_for_period)."""
    assert task.cutoff is not None
    consecutive_old = 0
    for raw_line in _iter_lines_reverse(task.path):
        entry = parse_log_line(raw_line, log_path=task.path)
        if entry is None:
            continue
        if entry.timestamp >= task.cutoff:
            accumulator.add(entry)
            consecutive_old = 0
        else:
            consecutive_old += 1
            if consecutive_old >= _MAX_CONSECUTIVE_OLD_LINES:
                break


def accumulate_paths(
    paths: list[str], *, period: str | None = None, now: datetime | None = None,
    runner: ProcessRunnerPort | None = None,
) -> StatsAccumulator:
    """Version sequentielle (CLI, tests) : memes taches, executees une par une ici."""
    total = StatsAccumulator()
    for task in plan_read_tasks(paths, period=period, now=now, runner=runner):
        total.merge(run_read_task(task, runner))
    return total
