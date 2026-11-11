# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Sauvegardes planifiees EXECUTEES (2026-11-09, lot 7) - porte d'omega-log
(application/use_cases/rotation_automation.py), version ROOT (decision utilisateur 2026-11-09).

- `run_due_automations` : appelee chaque nuit par `omega_fire rotate run-automations` (timer systemd
  systeme ou ligne de la crontab de root). Chaque automatisation arrivee a echeance sauvegarde son log
  comme « Sauvegarde manuelle » de 5.6 (archive + retention). Une automatisation en echec reste due :
  elle sera retentee la nuit suivante ; le resultat est note dans l'automatisation (affiche en 5.6).
- `install_rotation_schedule` / `remove_rotation_schedule` / `rotation_schedule_status` : la tache
  quotidienne, installee a la premiere automatisation et retiree a la derniere. Omega-fire tourne deja
  en root : ni sudo, ni mot de passe.

Stockage : var/runtime/scheduled_rotations.json, le MEME fichier qu'avant la 3.6 (les automatisations
deja configurees sont reprises telles quelles)."""
from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

from omega_fire.domain.logs.rotation_schedule import (
    CRON_MARKER,
    DEFAULT_KEEP,
    UNIT_BASE_NAME,
    build_rotation_cron_line,
    build_rotation_service_unit,
    build_rotation_timer_unit,
    is_due,
    render_manual_rotation_instructions,
    without_marked_line,
)
from omega_fire.shared.i18n import _

SYSTEMD_UNIT_DIR = Path("/etc/systemd/system")
AUTOMATIONS_FILE = "scheduled_rotations.json"
_TIMEOUT_SECONDS = 15.0
_CRONTAB_MISSING = 127


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""

    @property
    def ok(self) -> bool:
        return self.returncode == 0


Runner = Callable[[list[str], str | None], CommandResult]
"""(argv, entree standard) -> resultat. Jamais d'exception : commande absente = code 127."""


def run_command(argv: list[str], input_text: str | None = None) -> CommandResult:
    try:
        done = subprocess.run(argv, input=input_text, capture_output=True, text=True, timeout=_TIMEOUT_SECONDS,
                              check=False)
    except FileNotFoundError:
        return CommandResult(_CRONTAB_MISSING, "", f"{argv[0]}: introuvable")
    except (OSError, subprocess.SubprocessError) as exc:
        return CommandResult(1, "", str(exc))
    return CommandResult(done.returncode, done.stdout, done.stderr)


# ---- automatisations ----------------------------------------------------------------

class AutomationStore:
    """var/runtime/scheduled_rotations.json (liste de dicts) ; illisible = liste vide, jamais d'erreur."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def list_all(self) -> list[dict]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
        return [item for item in data if isinstance(item, dict)] if isinstance(data, list) else []

    def save_all(self, automations: list[dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(automations, indent=2, ensure_ascii=False), encoding="utf-8")


@dataclass(frozen=True)
class AutomationRun:
    path: str
    success: bool
    message: str


def run_due_automations(
    store: AutomationStore, now: datetime, backup: Callable[[str, int], tuple[bool, str]],
) -> list[AutomationRun]:
    """`backup(chemin, a_garder)` -> (reussi, message) : RotateLogsCommand. Une automatisation en echec
    ne bloque jamais les suivantes et reste due."""
    runs: list[AutomationRun] = []
    automations = store.list_all()
    for automation in automations:
        if not is_due(automation, now):
            continue
        path = str(automation.get("source_path", ""))
        try:
            keep = int(automation.get("keep") or DEFAULT_KEEP)
        except (TypeError, ValueError):
            keep = DEFAULT_KEEP
        try:
            success, message = backup(path, keep)
        except Exception as exc:  # noqa: BLE001 - une automatisation en echec ne bloque jamais les suivantes
            success, message = False, str(exc)
        runs.append(AutomationRun(path, success, message))
        automation["last_result"], automation["last_success"] = message, success
        automation["last_attempt_at"] = now.isoformat(timespec="seconds")
        if success:
            automation["last_run_at"] = now.isoformat(timespec="seconds")
    if runs:
        store.save_all(automations)
    return runs


# ---- tache planifiee ------------------------------------------------------------------

@dataclass(frozen=True)
class ScheduleResult:
    mechanism: Literal["systemd", "cron", "manual", "error"]
    success: bool
    message: str


def uses_systemd() -> bool:
    """systemd est le gestionnaire du systeme (pas seulement installe)."""
    return shutil.which("systemctl") is not None and Path("/run/systemd/system").is_dir()


_TIMER = f"{UNIT_BASE_NAME}.timer"
_SERVICE = f"{UNIT_BASE_NAME}.service"


def rotation_schedule_status(runner: Runner = run_command) -> ScheduleResult:
    if uses_systemd():
        if runner(["systemctl", "is-enabled", _TIMER], None).ok:
            return ScheduleResult("systemd", True, _("Exécution : timer systemd {timer} actif (chaque nuit).").format(timer=_TIMER))
        return ScheduleResult("systemd", False, _("Exécution : timer systemd {timer} non installé.").format(timer=_TIMER))
    listing = runner(["crontab", "-l"], None)
    if listing.returncode == _CRONTAB_MISSING:
        return ScheduleResult("manual", False, _("Exécution : aucun planificateur (ni systemd, ni crontab)."))
    if any(line.rstrip().endswith(CRON_MARKER) for line in listing.stdout.splitlines()):
        return ScheduleResult("cron", True, _("Exécution : ligne crontab installée (chaque nuit)."))
    return ScheduleResult("cron", False, _("Exécution : aucune ligne crontab pour ce compte."))


def install_rotation_schedule(project_root: Path, python_executable: str, runner: Runner = run_command,
                              unit_dir: Path = SYSTEMD_UNIT_DIR) -> ScheduleResult:
    root = str(project_root.resolve())
    if uses_systemd():
        try:
            unit_dir.mkdir(parents=True, exist_ok=True)
            for name, content in (
                (_SERVICE, build_rotation_service_unit(python_executable=python_executable, project_root=root)),
                (_TIMER, build_rotation_timer_unit()),
            ):
                (unit_dir / name).write_text(content, encoding="utf-8")
                (unit_dir / name).chmod(0o644)
        except OSError as exc:
            return ScheduleResult("error", False, _("Timer systemd non installé : {error}").format(error=exc))
        for argv in (["systemctl", "daemon-reload"], ["systemctl", "enable", "--now", _TIMER]):
            result = runner(argv, None)
            if not result.ok:
                error = result.stderr.strip() or _("code {returncode}").format(returncode=result.returncode)
                return ScheduleResult("error", False, _("Timer systemd non installé : {error}").format(error=error))
        return ScheduleResult("systemd", True, _("Timer systemd {timer} installé : les automatisations "
                                                 "s'exécutent chaque nuit.").format(timer=_TIMER))

    line = build_rotation_cron_line(python_executable=python_executable, project_root=root)
    listing = runner(["crontab", "-l"], None)
    if listing.returncode == _CRONTAB_MISSING:
        return ScheduleResult("manual", False, render_manual_rotation_instructions(cron_line=line))
    kept = without_marked_line(listing.stdout if listing.returncode == 0 else "")
    written = runner(["crontab", "-"], "\n".join([*kept, line]) + "\n")
    if not written.ok:
        return ScheduleResult("error", False, _("Échec de l'écriture de la crontab : {value}").format(
            value=(written.stderr or written.stdout).strip()))
    return ScheduleResult("cron", True, _("Ligne crontab installée : les automatisations s'exécutent chaque nuit."))


def remove_rotation_schedule(runner: Runner = run_command, unit_dir: Path = SYSTEMD_UNIT_DIR) -> ScheduleResult:
    if uses_systemd():
        if not (unit_dir / _TIMER).exists():
            return ScheduleResult("systemd", True, "")
        disabled = runner(["systemctl", "disable", "--now", _TIMER], None)
        if not disabled.ok:
            error = disabled.stderr.strip() or _("code {returncode}").format(returncode=disabled.returncode)
            return ScheduleResult("error", False, _("Timer systemd non retiré : {error}").format(error=error))
        for name in (_TIMER, _SERVICE):
            try:
                (unit_dir / name).unlink(missing_ok=True)
            except OSError as exc:
                return ScheduleResult("error", False, _("Timer systemd non retiré : {error}").format(error=exc))
        runner(["systemctl", "daemon-reload"], None)
        return ScheduleResult("systemd", True, _("Plus aucune automatisation : timer systemd retiré."))
    listing = runner(["crontab", "-l"], None)
    if listing.returncode != 0:
        return ScheduleResult("cron", True, "")
    kept = without_marked_line(listing.stdout)
    if len(kept) == len(listing.stdout.splitlines()):
        return ScheduleResult("cron", True, "")
    written = runner(["crontab", "-"], "\n".join(kept) + "\n" if kept else "")
    if not written.ok:
        return ScheduleResult("error", False, _("Échec de l'écriture de la crontab : {value}").format(
            value=(written.stderr or written.stdout).strip()))
    return ScheduleResult("cron", True, _("Plus aucune automatisation : ligne crontab retirée."))
