# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 5.6 — Purge et nettoyage des backups. Patron #3 a 5 branches
(anciennete / quota / securite automatique / selection manuelle /
gestion des regles planifiees), meme structure que RotateLogsScreen
(5.4) et RestoreBackupScreen (5.5). Logique identique a
interfaces/cli/actions.py::action_5_6_purge_backups — meme fichier de
persistance (var/runtime/scheduled_purges.json)."""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, DataTable, Footer, Header, Input, Select, Static

from omega_fire.application.commands.purge_backups import PurgeBackupsCommand
from omega_fire.infrastructure.config.paths import BACKUPS_DIR, RUNTIME_DIR
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.screens.confirm import ConfirmScreen
from omega_fire.interfaces.tui.support.action_audit import log_action_result

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ACTION_TITLE = "5.6 Purge Backups"
_PURGE_AUTO_FILE = "scheduled_purges.json"

_MODE_AGE = "age"
_MODE_QUOTA = "quota"
_MODE_SAFETY = "safety"
_MODE_MANUAL = "manual"
_MODE_MANAGE = "manage"


class PurgeBackupsScreen(OmegaScreen):
    """Purge des archives de backup selon divers criteres."""

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container
        self._selected_rule_index: int | None = None

    def _all_backups(self) -> list[Path]:
        backup_dir = BACKUPS_DIR
        backup_dir.mkdir(parents=True, exist_ok=True)
        return sorted(
            [f for f in backup_dir.glob("*.tar.gz") if f.is_file()],
            key=lambda x: x.stat().st_mtime, reverse=True,
        )

    def _load_rules(self) -> list[dict]:
        f = RUNTIME_DIR / _PURGE_AUTO_FILE
        if not f.exists():
            return []
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _save_rules(self, rules: list[dict]) -> None:
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        (RUNTIME_DIR / _PURGE_AUTO_FILE).write_text(json.dumps(rules, indent=2, ensure_ascii=False), encoding="utf-8")

    def compose(self) -> ComposeResult:
        all_backups = self._all_backups()
        total_size_mb = sum(f.stat().st_size for f in all_backups) / (1024 * 1024) if all_backups else 0.0
        free_gb = shutil.disk_usage(BACKUPS_DIR).free / (1024 ** 3)

        yield Header()
        with VerticalScroll(classes="omega-form-panel"):
            yield Static("PURGE ET NETTOYAGE DES BACKUPS", classes="omega-title")
            yield Static(
                f"{len(all_backups)} archive(s), {total_size_mb:.2f} MB occupes, {free_gb:.2f} GB libres sur disque.",
                classes="omega-hint",
            )

            yield Static("Mode de nettoyage", classes="omega-subtitle")
            yield Select(
                [
                    ("Purger par anciennete", _MODE_AGE),
                    ("Purger par quota (conserver les N plus recentes)", _MODE_QUOTA),
                    ("Purger les backups de securite ('safety_auto_*')", _MODE_SAFETY),
                    ("Selection manuelle ciblee", _MODE_MANUAL),
                    ("Gerer les regles de purge automatique", _MODE_MANAGE),
                ],
                value=_MODE_AGE,
                id="mode-select",
            )

            yield Static("Age limite", id="age-label", classes="omega-subtitle")
            yield Select(
                [("Plus de 30 jours", "30"), ("Plus de 90 jours", "90"), ("Plus de 180 jours", "180"),
                 ("Plus de 365 jours", "365"), ("Personnalise", "custom")],
                value="30",
                id="age-select",
            )
            yield Static("Nombre de jours", id="age-custom-label", classes="omega-subtitle omega-hidden")
            yield Input(value="45", id="age-custom-input", classes="omega-hidden")

            yield Static("Conserver", id="quota-label", classes="omega-subtitle omega-hidden")
            yield Select(
                [("Les 5 plus recentes", "5"), ("Les 10 plus recentes", "10"),
                 ("Les 20 plus recentes", "20"), ("Personnalise", "custom")],
                value="5",
                id="quota-select",
                classes="omega-hidden",
            )
            yield Static("Nombre a conserver", id="quota-custom-label", classes="omega-subtitle omega-hidden")
            yield Input(value="15", id="quota-custom-input", classes="omega-hidden")

            yield Static("Fichier a supprimer", id="manual-label", classes="omega-subtitle omega-hidden")
            yield Select(self._backup_options(), id="manual-select", classes="omega-hidden")

            yield Static("Regles de purge planifiees", id="manage-label", classes="omega-subtitle omega-hidden")
            yield DataTable(id="rules-table", classes="omega-hidden")
            with Horizontal(classes="omega-actions", id="manage-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button("Supprimer la selection", id="delete-rule", variant="error")

            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button("Purger", id="launch", variant="error")
                with Container(classes="omega-btn-frame"):
                    yield Button("Retour", id="back")
        yield Footer()

    def _backup_options(self) -> list[tuple[str, str]]:
        options = []
        for bfile in self._all_backups():
            mtime = datetime.fromtimestamp(bfile.stat().st_mtime).strftime("%d/%m/%Y %H:%M:%S")
            size_kb = bfile.stat().st_size / 1024
            options.append((f"{bfile.name} ({mtime} — {size_kb:.1f} KB)", str(bfile)))
        return options

    def on_mount(self) -> None:
        options = self._backup_options()
        if options:
            self.query_one("#manual-select", Select).value = options[0][1]
        self._apply_mode(_MODE_AGE)

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "mode-select":
            self._apply_mode(str(event.value))
        elif event.select.id == "age-select":
            is_custom = str(event.value) == "custom"
            self.query_one("#age-custom-label", Static).set_class(not is_custom, "omega-hidden")
            self.query_one("#age-custom-input", Input).set_class(not is_custom, "omega-hidden")
        elif event.select.id == "quota-select":
            is_custom = str(event.value) == "custom"
            self.query_one("#quota-custom-label", Static).set_class(not is_custom, "omega-hidden")
            self.query_one("#quota-custom-input", Input).set_class(not is_custom, "omega-hidden")

    def _apply_mode(self, mode: str) -> None:
        is_age = mode == _MODE_AGE
        is_quota = mode == _MODE_QUOTA
        is_manual = mode == _MODE_MANUAL
        is_manage = mode == _MODE_MANAGE

        self.query_one("#age-label", Static).set_class(not is_age, "omega-hidden")
        self.query_one("#age-select", Select).set_class(not is_age, "omega-hidden")
        age_custom = is_age and str(self.query_one("#age-select", Select).value) == "custom"
        self.query_one("#age-custom-label", Static).set_class(not age_custom, "omega-hidden")
        self.query_one("#age-custom-input", Input).set_class(not age_custom, "omega-hidden")

        self.query_one("#quota-label", Static).set_class(not is_quota, "omega-hidden")
        self.query_one("#quota-select", Select).set_class(not is_quota, "omega-hidden")
        quota_custom = is_quota and str(self.query_one("#quota-select", Select).value) == "custom"
        self.query_one("#quota-custom-label", Static).set_class(not quota_custom, "omega-hidden")
        self.query_one("#quota-custom-input", Input).set_class(not quota_custom, "omega-hidden")

        self.query_one("#manual-label", Static).set_class(not is_manual, "omega-hidden")
        self.query_one("#manual-select", Select).set_class(not is_manual, "omega-hidden")

        self.query_one("#manage-label", Static).set_class(not is_manage, "omega-hidden")
        table = self.query_one("#rules-table", DataTable)
        table.set_class(not is_manage, "omega-hidden")
        self.query_one("#manage-actions", Horizontal).set_class(not is_manage, "omega-hidden")
        self.query_one("#launch", Button).set_class(is_manage, "omega-hidden")
        if is_manage:
            self._refresh_rules_table()

    def _refresh_rules_table(self) -> None:
        table = self.query_one("#rules-table", DataTable)
        table.clear(columns=True)
        table.cursor_type = "row"
        table.add_columns("Type", "Valeur", "Creee le")
        for idx, rule in enumerate(self._load_rules()):
            table.add_row(rule.get("type", ""), rule.get("value", ""), rule.get("created_at", ""), key=str(idx))

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        self._selected_rule_index = int(str(event.row_key.value))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss()
            return
        if event.button.id == "delete-rule":
            self._delete_selected_rule()
            return
        if event.button.id != "launch":
            return

        mode = str(self.query_one("#mode-select", Select).value)
        all_backups = self._all_backups()
        files_to_delete: list[Path] = []
        action_title = ""

        if mode == _MODE_AGE:
            age_choice = str(self.query_one("#age-select", Select).value)
            if age_choice == "custom":
                raw = self.query_one("#age-custom-input", Input).value.strip()
                target_days = int(raw) if raw.isdigit() and int(raw) > 0 else 30
            else:
                target_days = int(age_choice)
            cutoff = datetime.now() - timedelta(days=target_days)
            files_to_delete = [f for f in all_backups if datetime.fromtimestamp(f.stat().st_mtime) < cutoff]
            action_title = f"Purge des archives de plus de {target_days} jours"

        elif mode == _MODE_QUOTA:
            quota_choice = str(self.query_one("#quota-select", Select).value)
            if quota_choice == "custom":
                raw = self.query_one("#quota-custom-input", Input).value.strip()
                keep_count = int(raw) if raw.isdigit() and int(raw) >= 0 else 5
            else:
                keep_count = int(quota_choice)
            if len(all_backups) > keep_count:
                files_to_delete = all_backups[keep_count:]
            action_title = f"Purge par quota (conservation des {keep_count} plus recentes)"

        elif mode == _MODE_SAFETY:
            files_to_delete = [f for f in all_backups if f.name.startswith("safety_auto_")]
            action_title = "Purge des backups temporaires de securite"

        elif mode == _MODE_MANUAL:
            selected = self.query_one("#manual-select", Select).value
            if selected is None or selected == Select.BLANK:
                self.app.notify("Aucun fichier disponible ou selectionne.", severity="warning")
                return
            files_to_delete = [Path(str(selected))]
            action_title = f"Suppression manuelle ciblee de '{files_to_delete[0].name}'"

        if not files_to_delete:
            self.app.notify("Aucun fichier ne correspond aux criteres de suppression choisis.", severity="warning")
            return

        recap_size_mb = sum(f.stat().st_size for f in files_to_delete) / (1024 * 1024)
        preview = "\n".join(f"  - {f.name}" for f in files_to_delete[:8])
        if len(files_to_delete) > 8:
            preview += f"\n  ... et {len(files_to_delete) - 8} autre(s)."

        self.app.push_screen(
            ConfirmScreen(
                title="CONFIRMER LA PURGE",
                message=f"{action_title}\n{len(files_to_delete)} fichier(s), {recap_size_mb:.2f} MB.\n{preview}",
            ),
            lambda confirmed: self._purge_if_confirmed(confirmed, files_to_delete, recap_size_mb),
        )

    def _purge_if_confirmed(self, confirmed: bool | None, files_to_delete: list[Path], recap_size_mb: float) -> None:
        if not confirmed:
            return

        persistence_port = self._container.get_persistence_port()
        all_backup_infos = persistence_port.list_backups(BACKUPS_DIR)
        backups_by_path = {b.path: b for b in all_backup_infos}
        backups_to_delete = [backups_by_path[f] for f in files_to_delete if f in backups_by_path]

        result = PurgeBackupsCommand(persistence_port=persistence_port).execute(backups_to_delete)

        if result.deleted_count > 0:
            self.app.notify(f"Purge terminee : {result.deleted_count} fichier(s) supprime(s), {recap_size_mb:.2f} MB liberes.")
        if result.error_count > 0:
            for err in result.errors:
                self.app.notify(f"Erreur lors de la suppression de {err}", severity="error")

        log_action_result(self._container, _ACTION_TITLE, status="success" if result.deleted_count else "failure")
        self.dismiss()

    def _delete_selected_rule(self) -> None:
        idx = self._selected_rule_index
        rules = self._load_rules()
        if idx is None or not (0 <= idx < len(rules)):
            self.app.notify("Selectionnez d'abord une ligne.", severity="warning")
            return
        removed = rules.pop(idx)
        self._save_rules(rules)
        self.app.notify(f"Regle de purge '{removed.get('type', '')}' supprimee.")
        self._selected_rule_index = None
        self._refresh_rules_table()
