# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""`python -m omega_fire rotate run-automations` (2026-11-09, lot 7) : la tache quotidienne lancee par le
timer systemd ou la crontab de root. Sauvegarde chaque log dont l'automatisation de 5.6 est arrivee a
echeance, puis s'arrete. Sortie en francais (journalctl / fichier de log de cron), jamais d'interface.
Code de sortie : 0 si tout a reussi (ou rien a faire), 1 si au moins une sauvegarde a echoue."""
from __future__ import annotations

from datetime import datetime


def run_rotation_automations() -> int:
    from omega_fire.app.dependency_container import DependencyContainer
    from omega_fire.application.commands.rotate_logs import RotateLogsCommand, RotateLogsRequest
    from omega_fire.application.commands.rotation_automation import (
        AUTOMATIONS_FILE,
        AutomationStore,
        run_due_automations,
    )
    from omega_fire.infrastructure.config.paths import RUNTIME_DIR, ensure_runtime_dirs

    ensure_runtime_dirs()
    container = DependencyContainer()

    def backup(path: str, keep: int) -> tuple[bool, str]:
        result = RotateLogsCommand(persistence_port=container.get_persistence_port()).execute(
            RotateLogsRequest(source_path=path, reason="Sauvegarde planifiée (menu 5.6)", keep=keep))
        return result.success, result.message

    runs = run_due_automations(AutomationStore(RUNTIME_DIR / AUTOMATIONS_FILE), datetime.now(), backup)
    if not runs:
        print("omega-fire : aucune sauvegarde planifiée à échéance.")
        return 0
    for run in runs:
        state = "réussie" if run.success else "ÉCHEC"
        print(f"omega-fire : sauvegarde planifiée {state} - {run.path} - {run.message}")
    return 0 if all(run.success for run in runs) else 1
