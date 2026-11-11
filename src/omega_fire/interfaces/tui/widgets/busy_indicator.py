# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
# Porte d'omega-log (interfaces/tui/widgets/busy_indicator.py) le 2026-11-09 (OMEGA-FIRE_PLAN_LOGS_NIVEAU_SERV_LOG.md) : garder identique a la source.
"""Indicateur d'attente des calculs longs (Statistiques, Voir et traiter IP) - retour utilisateur
2026-11-06 : « sa reste sur calcul en cours… c'est long, ca peut faire peur a l'utilisateur, mettre un
spinner avec differents messages ; il faut que ce soit explicite que le temps varie selon la taille ».

Progression : un gros fichier est decoupe en morceaux analyses en parallele ; la barre avance a chaque
morceau termine (vraie mesure, jamais simulee). Un petit fichier ou une periode courte = un seul morceau,
pas de barre. Sinon l'indicateur montre ce qui est vrai - une roue qui tourne, le temps ecoule, la taille des
fichiers et leur nombre de lignes ESTIME (« environ », d'apres 16 echantillons) - et des messages qui
changent pour dire que l'application travaille."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from rich.text import Text
from textual.timer import Timer
from textual.widgets import Static

from omega_fire.shared.i18n import N_, _

PERIOD_BUTTON_LABELS = {"24h": N_("24h"), "7j": N_("7j"), "30j": N_("30j"), "Tout": N_("Tout (fichier entier)")}
"""Cle = id du bouton (jamais traduite) ; libelle traduit a l'affichage avec _()."""
PERIOD_HINT = (_("24h, 7j, 30j : lecture depuis la fin du fichier, rapide. « Tout » lit le "
                 "fichier entier : la durée dépend de sa taille (de quelques secondes à "
                 "plusieurs minutes pour un gros log)."))
"""Sous les boutons de periode des deux ecrans de calcul : la duree de « Tout » est annoncee avant le clic."""
_FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
_PROGRESS_WIDTH = 30
_SAMPLE_BYTES = 16 * 1024
_SAMPLES = 16
_MESSAGE_SECONDS = 4.0
_MESSAGES_FULL = (
    _("Lecture du fichier entier, ligne par ligne…"),
    _("Analyse des lignes (date, IP, code HTTP, chemin)…"),
    _("Plus le fichier est gros, plus c'est long : quelques secondes à plusieurs minutes."),
    _("Échap arrête l'analyse : il faudra la relancer."),
    _("Toujours en cours, rien n'est bloqué…"),
)
_MESSAGES_PERIOD = (
    _("Lecture depuis la fin du fichier, arrêt dès que les lignes sortent de la période…"),
    _("Analyse des lignes de la période…"),
    _("Toujours en cours, rien n'est bloqué…"),
)


def _format_size(size: int) -> str:
    for unit, factor in ((_("Go"), 1024 ** 3), (_("Mo"), 1024 ** 2), (_("Ko"), 1024)):
        if size >= factor:
            return f"{size / factor:.1f} {unit}"
    return f"{size} o"


def _estimated_lines(path: Path, size: int) -> int | None:
    """Lignes estimees d'apres la longueur moyenne de 16 echantillons de 16 Ko repartis sur le fichier :
    un seul echantillon du debut se trompait de 60 % sur un vrai access.log. None si illisible sans sudo."""
    if size == 0:
        return 0
    try:
        with path.open("rb") as handle:
            if size <= _SAMPLES * _SAMPLE_BYTES:
                return handle.read().count(b"\n")
            sampled, newlines = 0, 0
            for index in range(_SAMPLES):
                offset = (size - _SAMPLE_BYTES) * index // (_SAMPLES - 1)
                handle.seek(offset)
                chunk = handle.read(_SAMPLE_BYTES)
                sampled += len(chunk)
                newlines += chunk.count(b"\n")
    except OSError:
        return None
    return round(size / (sampled / max(newlines, 1)))


def describe_selection(paths: list[str]) -> str:
    """« 2 log(s) · 131.2 Mo · environ 420 000 lignes » - vide si aucun fichier lisible."""
    total_size, total_lines, unknown = 0, 0, False
    for raw in paths:
        path = Path(raw)
        try:
            size = path.stat().st_size
        except OSError:
            unknown = True
            continue
        total_size += size
        estimated = _estimated_lines(path, size)
        if estimated is None:
            unknown = True
        else:
            total_lines += estimated
    if not paths:
        return ""
    parts = [_("{count} log(s)").format(count=len(paths)), _format_size(total_size)]
    if total_lines:
        lines = f"{total_lines:,}".replace(",", " ")
        parts.append(_("environ {lines} lignes").format(lines=lines) + (_(" (au moins)") if unknown else ""))
    return " · ".join(parts)


class BusyIndicator(Static):
    """Ligne d'attente : roue, message, temps ecoule, puis la selection analysee. Cachee au repos."""

    DEFAULT_CSS = "BusyIndicator { display: none; height: auto; margin: 1 0 0 0; }"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__("", **kwargs)
        self._timer: Timer | None = None
        self._started = 0.0
        self._messages: tuple[str, ...] = _MESSAGES_FULL
        self._selection = ""
        self._progress: tuple[int, int, int, int] | None = None

    def start(self, paths: list[str], period: str | None) -> None:
        self._started = time.monotonic()
        self._messages = _MESSAGES_FULL if period is None else _MESSAGES_PERIOD
        self._selection = describe_selection(paths)
        self._progress = None
        self.display = True
        self._tick()
        if self._timer is None:
            self._timer = self.set_interval(0.12, self._tick)

    def set_progress(self, done_bytes: int, total_bytes: int, done_parts: int, total_parts: int) -> None:
        """Progression REELLE, mise a jour a chaque morceau termine (2026-11-06)."""
        self._progress = (done_bytes, total_bytes, done_parts, total_parts)
        self._tick()

    def stop(self) -> None:
        if self._timer is not None:
            self._timer.stop()
            self._timer = None
        self.display = False
        self.update("")

    def _tick(self) -> None:
        elapsed = time.monotonic() - self._started
        frame = _FRAMES[int(elapsed / 0.12) % len(_FRAMES)]
        message = self._messages[int(elapsed / _MESSAGE_SECONDS) % len(self._messages)]
        minutes, seconds = divmod(int(elapsed), 60)
        content = Text()
        content.append(f" {frame} ", style="bold")
        content.append(_("Calcul en cours"), style="bold")
        content.append(f"  ({minutes:d}:{seconds:02d})\n", style="dim")
        content.append(f"   {message}")
        if self._progress is not None and self._progress[3] > 1:
            done_bytes, total_bytes, done_parts, total_parts = self._progress
            share = done_bytes / total_bytes if total_bytes else done_parts / total_parts
            filled = round(share * _PROGRESS_WIDTH)
            content.append("\n   ")
            content.append("█" * filled, style="bold")
            content.append("░" * (_PROGRESS_WIDTH - filled), style="dim")
            content.append(_(" {value:3.0f} %  ({done_parts}/{total_parts} morceaux analysés)").format(value=share * 100, done_parts=done_parts, total_parts=total_parts))
        self.update(content)
