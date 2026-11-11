# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Sauvegardes planifiees EXECUTEES (2026-11-09, OMEGA-FIRE_PLAN_LOGS_NIVEAU_SERV_LOG.md lot 7) - porte
d'omega-log (domain/logs/rotation_schedule.py), lui-meme repris d'omega-serv 2.6.0.

Avant la 3.6, 5.6 enregistrait les automatisations (var/runtime/scheduled_rotations.json) sans que rien
ne les execute. Desormais une seule tache planifiee, une fois par jour : `python -m omega_fire rotate
run-automations`, qui sauvegarde chaque log dont l'automatisation est arrivee a echeance (meme geste que
« Sauvegarde manuelle » de 5.6).

Difference avec omega-log (decision utilisateur 2026-11-09) : la tache tourne en ROOT, comme omega-fire
(ses logs sont souvent reserves a root) - timer systemd systeme, sinon ligne de la crontab de root,
sinon ligne a ajouter soi-meme. Gabarits purs, aucune I/O ici."""
from __future__ import annotations

import shlex
from datetime import datetime, timedelta

from omega_fire.shared.i18n import _

UNIT_BASE_NAME = "omega-fire-rotation"
CRON_MARKER = "# omega-fire-rotation"
KEEP_CHOICES: tuple[int, ...] = (5, 10, 30)
"""Nombre de sauvegardes conservees par log (10 : comme la sauvegarde manuelle de 5.6)."""
DEFAULT_KEEP = 10


def is_due(automation: dict, now: datetime) -> bool:
    """Echeance = derniere execution reussie (ou creation) + intervalle en jours. Donnee illisible : jamais due."""
    due = next_run(automation)
    return due is not None and now >= due


def next_run(automation: dict) -> datetime | None:
    try:
        reference = datetime.fromisoformat(str(automation.get("last_run_at") or automation["created_at"]))
        return reference + timedelta(days=int(automation["days_interval"]))
    except (KeyError, TypeError, ValueError):
        return None


def rotation_command(python_executable: str) -> str:
    return f"{shlex.quote(python_executable)} -m omega_fire rotate run-automations"


def build_rotation_service_unit(*, python_executable: str, project_root: str) -> str:
    """Service root (omega-fire tourne en root) : les logs proteges (/var/log/...) sont sauvegardes la nuit."""
    return (
        "[Unit]\n"
        "Description=Sauvegardes planifiées des logs (OMEGA-FIRE, généré - ne pas éditer à la main)\n"
        "\n"
        "[Service]\n"
        "Type=oneshot\n"
        f"WorkingDirectory={project_root}\n"
        f"ExecStart={rotation_command(python_executable)}\n"
    )


def build_rotation_timer_unit() -> str:
    return (
        "[Unit]\n"
        "Description=Timer des sauvegardes planifiées des logs (OMEGA-FIRE, généré - ne pas éditer à la main)\n"
        "\n"
        "[Timer]\n"
        "OnCalendar=*-*-* 03:45:00\n"
        "RandomizedDelaySec=1800\n"
        "Persistent=true\n"
        "\n"
        "[Install]\n"
        "WantedBy=timers.target\n"
    )


def build_rotation_cron_line(*, python_executable: str, project_root: str) -> str:
    """Sortie ajoutee a var/logs/rotation-automations.log : cron n'envoie jamais de courriel pour rien."""
    root = shlex.quote(project_root)
    log = shlex.quote(f"{project_root}/var/logs/rotation-automations.log")
    return f"45 3 * * * cd {root} && {rotation_command(python_executable)} >> {log} 2>&1  {CRON_MARKER}"


def without_marked_line(existing_crontab: str) -> list[str]:
    """Lignes de la crontab de root sauf celle d'omega-fire."""
    return [line for line in existing_crontab.splitlines() if not line.rstrip().endswith(CRON_MARKER)]


def render_manual_rotation_instructions(*, cron_line: str) -> str:
    return _("Aucun planificateur détecté (ni systemd, ni crontab). Ajoutez cette ligne vous-même à votre "
             "planificateur (crontab -e, /etc/cron.d/, tâche OpenRC ou runit équivalente) :\n\n{cron_line}").format(
        cron_line=cron_line)
