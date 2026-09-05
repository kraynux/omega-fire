# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 5.5 — Restaurer un backup. Patron #3 a 3 branches (restauration
immediate / configurer une automatisation / gerer les automatisations),
meme structure que RotateLogsScreen (5.4). Logique identique a
interfaces/cli/actions.py::action_5_5_restore_backup — meme fichier de
persistance (var/runtime/scheduled_restores.json)."""
from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, DataTable, Footer, Header, Input, Select, Static

from omega_fire.application.commands.restore_backup import RestoreBackupCommand, RestoreBackupRequest
from omega_fire.infrastructure.config.paths import BACKUPS_DIR, BLOCKLIST_DIR, EXPORTS_DIR, LOGS_DIR, RUNTIME_DIR
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.support.action_audit import log_action_result

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ACTION_TITLE = "5.5 Restaurer Backup"
_RESTORE_AUTO_FILE = "scheduled_restores.json"

_MODE_IMMEDIATE = "immediate"
_MODE_SCHEDULE = "schedule"
_MODE_MANAGE = "manage"

_STRATEGIES: dict[str, tuple[str, str]] = {
    "1": ("Restauration manuelle ciblee", "Restaure uniquement l'archive specifiee depuis var/backups/"),
    "2": ("Dernier etat sain", "Recherche et restaure automatiquement la derniere archive valide de la cible"),
    "3": ("Rollback periodique", "Reinitialisation automatique programmee"),
}


class RestoreBackupScreen(OmegaScreen):
    """Restauration d'un backup, immediate ou planifiee."""

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container
        self._selected_automation_index: int | None = None

    def _backups(self) -> list:
        backup_dir = BACKUPS_DIR
        backup_dir.mkdir(parents=True, exist_ok=True)
        return sorted(
            [f for f in backup_dir.glob("backup_*.tar.gz") if f.is_file()],
            key=lambda x: x.stat().st_mtime, reverse=True,
        )

    def _load_automations(self) -> list[dict]:
        auto_file = RUNTIME_DIR / _RESTORE_AUTO_FILE
        if not auto_file.exists():
            return []
        try:
            return json.loads(auto_file.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _save_automations(self, automations: list[dict]) -> None:
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        (RUNTIME_DIR / _RESTORE_AUTO_FILE).write_text(json.dumps(automations, indent=2, ensure_ascii=False), encoding="utf-8")

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(classes="omega-form-panel"):
            yield Static("RESTAURER UN BACKUP", classes="omega-title")

            yield Static("Action", classes="omega-subtitle")
            yield Select(
                [
                    ("Restaurer une sauvegarde immediatement", _MODE_IMMEDIATE),
                    ("Configurer une automatisation de restauration", _MODE_SCHEDULE),
                    ("Lister et gerer les automatisations en cours", _MODE_MANAGE),
                ],
                value=_MODE_IMMEDIATE,
                id="mode-select",
            )

            yield Static("Archive a restaurer", id="backup-label", classes="omega-subtitle")
            yield Select(self._backup_options(), id="backup-select")

            yield Static("Mode de restauration", id="restore-mode-label", classes="omega-subtitle")
            yield Select(
                [("Rajouter (fusion incrementale)", "append"), ("Ecraser (sauvegarde de securite auto)", "overwrite")],
                value="append",
                id="restore-mode-select",
            )

            yield Static("Strategie", id="strategy-label", classes="omega-subtitle omega-hidden")
            yield Select(
                [(label, key) for key, (label, _) in _STRATEGIES.items()],
                value="1",
                id="strategy-select",
                classes="omega-hidden",
            )
            yield Static("Periode de rollback", id="period-label", classes="omega-subtitle omega-hidden")
            yield Select(
                [("180 jours (standard)", "standard"), ("Personnalise", "custom")],
                value="standard",
                id="period-select",
                classes="omega-hidden",
            )
            yield Static("Nombre de jours", id="period-custom-label", classes="omega-subtitle omega-hidden")
            yield Input(value="90", id="period-custom-input", classes="omega-hidden")
            yield Static("Mode d'application", id="apply-mode-label", classes="omega-subtitle omega-hidden")
            yield Select(
                [("Incrementation (fusion)", "append"), ("Ecraser (remplacement complet)", "overwrite")],
                value="append",
                id="apply-mode-select",
                classes="omega-hidden",
            )

            yield Static("Automatisations planifiees", id="manage-label", classes="omega-subtitle omega-hidden")
            yield DataTable(id="automations-table", classes="omega-hidden")
            with Horizontal(classes="omega-actions", id="manage-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button("Supprimer la selection", id="delete-automation", variant="error")

            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button("Valider", id="launch", variant="primary")
                with Container(classes="omega-btn-frame"):
                    yield Button("Retour", id="back")
        yield Footer()

    def _backup_options(self) -> list[tuple[str, str]]:
        options = []
        for bfile in self._backups():
            mtime = datetime.fromtimestamp(bfile.stat().st_mtime).strftime("%d/%m/%Y %H:%M:%S")
            size_kb = bfile.stat().st_size / 1024
            options.append((f"{bfile.name} ({mtime} — {size_kb:.1f} KB)", str(bfile)))
        return options

    def on_mount(self) -> None:
        options = self._backup_options()
        if options:
            self.query_one("#backup-select", Select).value = options[0][1]
        self.query_one("#strategy-label", Static).set_class(True, "omega-hidden")
        self.query_one("#strategy-select", Select).set_class(True, "omega-hidden")
        self.query_one("#period-label", Static).set_class(True, "omega-hidden")
        self.query_one("#period-select", Select).set_class(True, "omega-hidden")
        self.query_one("#apply-mode-label", Static).set_class(True, "omega-hidden")
        self.query_one("#apply-mode-select", Select).set_class(True, "omega-hidden")
        self.query_one("#manage-label", Static).set_class(True, "omega-hidden")
        self.query_one("#automations-table", DataTable).set_class(True, "omega-hidden")
        self.query_one("#manage-actions", Horizontal).set_class(True, "omega-hidden")

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "mode-select":
            self._apply_mode(str(event.value))
        elif event.select.id == "strategy-select":
            is_rollback = str(event.value) == "3"
            self.query_one("#period-label", Static).set_class(not is_rollback, "omega-hidden")
            self.query_one("#period-select", Select).set_class(not is_rollback, "omega-hidden")
            period_custom = is_rollback and str(self.query_one("#period-select", Select).value) == "custom"
            self.query_one("#period-custom-label", Static).set_class(not period_custom, "omega-hidden")
            self.query_one("#period-custom-input", Input).set_class(not period_custom, "omega-hidden")
        elif event.select.id == "period-select":
            is_custom = str(event.value) == "custom"
            self.query_one("#period-custom-label", Static).set_class(not is_custom, "omega-hidden")
            self.query_one("#period-custom-input", Input).set_class(not is_custom, "omega-hidden")

    def _apply_mode(self, mode: str) -> None:
        is_immediate = mode == _MODE_IMMEDIATE
        is_schedule = mode == _MODE_SCHEDULE
        is_manage = mode == _MODE_MANAGE

        self.query_one("#backup-label", Static).set_class(not is_immediate, "omega-hidden")
        self.query_one("#backup-select", Select).set_class(not is_immediate, "omega-hidden")
        self.query_one("#restore-mode-label", Static).set_class(not is_immediate, "omega-hidden")
        self.query_one("#restore-mode-select", Select).set_class(not is_immediate, "omega-hidden")

        self.query_one("#strategy-label", Static).set_class(not is_schedule, "omega-hidden")
        self.query_one("#strategy-select", Select).set_class(not is_schedule, "omega-hidden")
        self.query_one("#apply-mode-label", Static).set_class(not is_schedule, "omega-hidden")
        self.query_one("#apply-mode-select", Select).set_class(not is_schedule, "omega-hidden")
        is_rollback = is_schedule and str(self.query_one("#strategy-select", Select).value) == "3"
        self.query_one("#period-label", Static).set_class(not is_rollback, "omega-hidden")
        self.query_one("#period-select", Select).set_class(not is_rollback, "omega-hidden")

        self.query_one("#manage-label", Static).set_class(not is_manage, "omega-hidden")
        table = self.query_one("#automations-table", DataTable)
        table.set_class(not is_manage, "omega-hidden")
        self.query_one("#manage-actions", Horizontal).set_class(not is_manage, "omega-hidden")
        self.query_one("#launch", Button).set_class(is_manage, "omega-hidden")
        if is_manage:
            self._refresh_automations_table()

    def _refresh_automations_table(self) -> None:
        table = self.query_one("#automations-table", DataTable)
        table.clear(columns=True)
        table.cursor_type = "row"
        table.add_columns("Strategie", "Intervalle", "Mode", "Creee le")
        for idx, item in enumerate(self._load_automations()):
            days = item.get("days_interval", 0)
            table.add_row(
                item.get("strategy_title", ""),
                f"{days}j" if days else "N/A",
                item.get("mode_label", ""),
                item.get("created_at", ""),
                key=str(idx),
            )

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        self._selected_automation_index = int(str(event.row_key.value))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss()
            return
        if event.button.id == "delete-automation":
            self._delete_selected_automation()
            return
        if event.button.id != "launch":
            return

        mode = str(self.query_one("#mode-select", Select).value)
        if mode == _MODE_IMMEDIATE:
            self._run_restore()
        elif mode == _MODE_SCHEDULE:
            self._configure_schedule()

    def _delete_selected_automation(self) -> None:
        idx = self._selected_automation_index
        automations = self._load_automations()
        if idx is None or not (0 <= idx < len(automations)):
            self.app.notify("Selectionnez d'abord une ligne.", severity="warning")
            return
        removed = automations.pop(idx)
        self._save_automations(automations)
        self.app.notify(f"Automatisation '{removed.get('strategy_title', '')}' supprimee.")
        self._selected_automation_index = None
        self._refresh_automations_table()

    def _run_restore(self) -> None:
        selected = self.query_one("#backup-select", Select).value
        if selected is None or selected == Select.BLANK:
            self.app.notify("Aucune sauvegarde disponible ou selectionnee.", severity="warning")
            return
        from pathlib import Path
        selected_backup = Path(str(selected))
        mode = str(self.query_one("#restore-mode-select", Select).value)

        if "blocklist" in selected_backup.name:
            target_dir = BLOCKLIST_DIR
        elif "export" in selected_backup.name:
            target_dir = EXPORTS_DIR
        else:
            target_dir = LOGS_DIR

        command = RestoreBackupCommand(persistence_port=self._container.get_persistence_port())
        result = command.execute(RestoreBackupRequest(
            backup_path=str(selected_backup), target_dir=str(target_dir), mode=mode,
        ))
        if not result.success:
            self.app.notify(f"Echec de la restauration : {result.message}", severity="error")
            log_action_result(self._container, _ACTION_TITLE, status="failure", error=result.message)
            return

        message = f"Restauration reussie : {result.target_file}"
        if result.safety_backup_path:
            message += f" (securite : {result.safety_backup_path.name})"
        self.app.notify(message)
        log_action_result(self._container, _ACTION_TITLE, status="success")
        self.dismiss()

    def _configure_schedule(self) -> None:
        strategy_key = str(self.query_one("#strategy-select", Select).value)
        days_interval = 0
        if strategy_key == "3":
            period = str(self.query_one("#period-select", Select).value)
            if period == "custom":
                raw = self.query_one("#period-custom-input", Input).value.strip()
                days_interval = int(raw) if raw.isdigit() and int(raw) > 0 else 180
            else:
                days_interval = 180

        apply_mode = str(self.query_one("#apply-mode-select", Select).value)
        mode_label = "Fusion incrementale" if apply_mode == "append" else "Ecrasement complet"
        strat_title, strat_desc = _STRATEGIES.get(strategy_key, _STRATEGIES["1"])
        if strategy_key == "3":
            strat_title = f"{strat_title} ({days_interval} jours)"

        automations = self._load_automations()
        automations.append({
            "strategy_id": strategy_key,
            "strategy_title": strat_title,
            "strategy_desc": strat_desc,
            "days_interval": days_interval,
            "mode": apply_mode,
            "mode_label": mode_label,
            "created_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        })
        self._save_automations(automations)

        self.app.notify(f"Automatisation enregistree : {strat_title} — {mode_label}.")
        log_action_result(self._container, _ACTION_TITLE, status="success")
        self.dismiss()
