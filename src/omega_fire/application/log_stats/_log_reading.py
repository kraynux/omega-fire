# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
# Porte d'omega-log (application/use_cases/_log_reading.py) le 2026-11-09 (OMEGA-FIRE_PLAN_LOGS_NIVEAU_SERV_LOG.md) : garder identique a la source.
"""Lecture+parsing partagee entre process_ip.py et access_log_stats.py
— extrait plutot que duplique, meme logique utilisee par les deux.

`runner` optionnel AJOUTE le 2026-10-03 (plan §5.1, elevation sudo
ponctuelle) : sans lui, une PermissionError leve PermissionRequiredError
(signal pour l'ecran TUI appelant, voir son docstring) ; fourni (apres
authentification via request_elevation() cote ecran), elle retombe sur
une lecture privilegiee au lieu d'echouer.

LECTURE INVERSEE AVEC ARRET ANTICIPE AJOUTEE (2026-10-04, retour
utilisateur persistant malgre deux correctifs precedents — parser
precompile puis processus separe — "aucun changement... j'ai attendu 2
minutes, rien ne s'affiche" ; "cette meme fonction est presente dans
omega-fire et omega-serv et fonctionne quasi instantanement") : cause
racine trouvee en inspectant le fichier REEL de l'utilisateur
(~/log-test/access.log, present dans son `var/library.json`) — 136 Mo,
415 614 lignes, couvrant PRES DE 3 MOIS d'historique. Pour une requete
"7 jours", l'ancienne implementation lisait et PARSAIT L'INTEGRALITE du
fichier (3 mois) avant de filtrer en memoire — plus de 90% du travail
jete. omega-fire/_LogProvider ne souffre pas de ce probleme parce qu'il
ne regarde jamais que les N dernieres lignes (`get_recent_logs(limit=
...)`), jamais l'historique complet — exactement pourquoi il "fonctionne
quasi instantanement" sur le MEME fichier : ce n'est pas plus rapide,
c'est un calcul fondamentalement plus petit.

Solution retenue ici (differente de la limite fixe de FIRE, qui aurait
perdu en exactitude sur la periode demandee) : pour toute requete avec
une PERIODE explicite (24h/7j/30j, jamais "Tout"), lire le fichier a
l'ENVERS (derniere ligne d'abord, par blocs, sans jamais charger le
fichier entier en memoire) et s'arreter des qu'un nombre suffisant de
lignes CONSECUTIVES plus vieilles que la periode est rencontre — un
fichier d'acces reel est pour l'essentiel trie chronologiquement, donc
cet arret anticipe couvre le cas normal sans perte de lignes recentes.
Seule la requete "Tout" (period=None) doit encore lire le fichier en
entier — aucun moyen de l'eviter pour un vrai total exhaustif."""
from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from omega_fire.domain.log_stats.models import LogEntry
from omega_fire.domain.log_stats.parser import parse_log_line
from omega_fire.infrastructure.log_stats.elevation import PermissionRequiredError
from omega_fire.infrastructure.log_stats.privileged_file_ops import read_file_privileged

if TYPE_CHECKING:
    from omega_fire.ports.log_process_runner import ProcessRunnerPort

PERIOD_TO_TIMEDELTA = {
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
}

_REVERSE_CHUNK_SIZE = 262144  # 256 KiB
_MAX_CONSECUTIVE_OLD_LINES = 500
"""Marge de securite avant de considerer qu'on a vraiment depasse la
fenetre demandee : un fichier de log n'est pas forcement PARFAITEMENT
trie chronologiquement (ligne isolee en retard, tampon d'ecriture
applicatif qui vide plusieurs sources...) — exige ce nombre de lignes
CONSECUTIVES plus vieilles que la periode, jamais une seule ligne
isolee, avant d'arreter la lecture."""


def _iter_lines_reverse(path: str) -> Iterator[str]:
    """Genere les lignes du fichier de la DERNIERE a la PREMIERE, par
    blocs depuis la fin — jamais le fichier entier charge en memoire
    d'un coup. Meme principe que omega-fire/_LogProvider._read_last_lines
    (lecture par blocs depuis la fin), generalise ici a un GENERATEUR
    sans limite de lignes fixee a l'avance (l'appelant decide quand
    s'arreter, selon la periode demandee)."""
    with open(path, "rb") as f:
        f.seek(0, os.SEEK_END)
        position = f.tell()
        trailing = b""
        while position > 0:
            read_size = min(_REVERSE_CHUNK_SIZE, position)
            position -= read_size
            f.seek(position)
            chunk = f.read(read_size) + trailing
            parts = chunk.split(b"\n")
            trailing = parts[0]  # premiere "ligne" du bloc : potentiellement incomplete
            for raw in reversed(parts[1:]):
                yield raw.decode("utf-8", errors="replace")
        if trailing:
            yield trailing.decode("utf-8", errors="replace")


def _read_entries_for_period(path: str, *, period: str, now: datetime) -> list[LogEntry] | None:
    """Lecture inversee avec arret anticipe — voir note de tete de
    fichier. Retourne `None` (jamais une liste vide) si le fichier est
    absent/illisible SANS elevation fournie, pour laisser l'appelant
    distinguer "rien a lire" de "a retente avec elevation"."""
    cutoff = now - PERIOD_TO_TIMEDELTA[period]
    entries: list[LogEntry] = []
    consecutive_old = 0
    for raw_line in _iter_lines_reverse(path):
        entry = parse_log_line(raw_line, line_number=0, log_path=path)
        if entry is None:
            continue
        if entry.timestamp >= cutoff:
            entries.append(entry)
            consecutive_old = 0
        else:
            consecutive_old += 1
            if consecutive_old >= _MAX_CONSECUTIVE_OLD_LINES:
                break
    entries.reverse()
    return entries


def read_entries(path: str, *, runner: ProcessRunnerPort | None = None) -> list[LogEntry]:
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except PermissionError:
        if runner is None:
            raise PermissionRequiredError(path) from None
        result = read_file_privileged(runner, path)
        if not result.success:
            return []
        lines = result.content.splitlines(keepends=True)
    except OSError:
        return []

    entries: list[LogEntry] = []
    for line_number, line in enumerate(lines, start=1):
        entry = parse_log_line(line, line_number=line_number, log_path=path)
        if entry is not None:
            entries.append(entry)
    return entries


def read_entries_for_paths(
    paths: list[str], *, period: str | None = None, now: datetime | None = None,
    runner: ProcessRunnerPort | None = None,
) -> list[LogEntry]:
    now = now or datetime.now()
    entries: list[LogEntry] = []

    for path in paths:
        if period is not None and runner is None:
            # Lecture inversee avec arret anticipe UNIQUEMENT pour le cas
            # non privilegie (pas d'equivalent "sudo tail inverse" —
            # repli volontaire sur la lecture complete privilegiee
            # ci-dessous si le fichier s'avere protege, cas marginal face
            # au gain sur le cas normal). `PermissionError` peut survenir
            # ICI (fichier protege, decouvert seulement a l'ouverture) :
            # jamais rattrapee silencieusement, propage PermissionRequiredError
            # comme le reste du module pour que l'ecran TUI authentifie.
            try:
                period_entries = _read_entries_for_period(path, period=period, now=now)
            except PermissionError:
                raise PermissionRequiredError(path) from None
            except OSError:
                period_entries = []
            entries.extend(period_entries)
            continue

        path_entries = read_entries(path, runner=runner)
        if period is not None:
            cutoff = now - PERIOD_TO_TIMEDELTA[period]
            path_entries = [e for e in path_entries if e.timestamp >= cutoff]
        entries.extend(path_entries)

    return entries
