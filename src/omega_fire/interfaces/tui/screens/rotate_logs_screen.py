# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 5.4 — Rotation / Backup des logs. Patron #3 a 3 branches
(sauvegarde manuelle immediate / configurer une automatisation / gerer
les automatisations en cours), chacune avec ses propres champs
conditionnels. Logique identique a
interfaces/cli/actions.py::action_5_4_rotate_logs — meme fichier de
persistance (var/runtime/scheduled_rotations.json), relu a chaque
ouverture plutot que partage en memoire entre process CLI/TUI."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, DataTable, Footer, Header, Input, Select, Static

from omega_fire.application.commands.manage_pinned_log_paths import ManagePinnedLogPathsCommand
from omega_fire.application.commands.rotate_logs import RotateLogsCommand, RotateLogsRequest
from omega_fire.infrastructure.config.paths import (
    BACKUPS_DIR,
    DEFAULT_PINNED_FILES,
    RUNTIME_DIR,
    _PROJECT_ROOT,
)
from omega_fire.infrastructure.storage.files.json_store import JsonStore
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.screens.pinned_paths_screen import PinnedPathsScreen
from omega_fire.interfaces.tui.support.action_audit import log_action_result

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ACTION_TITLE = "5.4 Rotation & Backup Logs"
_AUTO_FILE = "scheduled_rotations.json"

_MODE_MANUAL = "manual"
_MODE_SCHEDULE = "schedule"
_MODE_MANAGE = "manage"

_SRC_MANUAL = "__manual__"

_FREQ_OPTIONS: dict[str, tuple[int, str]] = {
    "weekly": (7, "Toutes les semaines"),
    "monthly": (30, "Tous les mois"),
    "quarterly": (90, "Tous les trimestres"),
    "semiannual": (180, "Tous les semestres"),
    "yearly": (364, "Tous les ans"),
    "custom": (0, "Personnalise"),
}


class RotateLogsScreen(OmegaScreen):
    """Sauvegarde/rotation de logs, immediate ou planifiee."""

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container
        self._pinned_command = ManagePinnedLogPathsCommand(
            JsonStore(RUNTIME_DIR),
            relative_path="blocklist_analysis_pinned_paths.json",
            defaults=[str(p) for p in DEFAULT_PINNED_FILES],
        )
        self._selected_automation_index: int | None = None

    def _load_automations(self) -> list[dict]:
        auto_file = RUNTIME_DIR / _AUTO_FILE
        if not auto_file.exists():
            return []
        try:
            return json.loads(auto_file.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _save_automations(self, automations: list[dict]) -> None:
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        (RUNTIME_DIR / _AUTO_FILE).write_text(json.dumps(automations, indent=2, ensure_ascii=False), encoding="utf-8")

    def _source_options(self) -> list[tuple[str, str]]:
        return [(p, p) for p in self._pinned_command.list_paths()] + [("Chemin manuel", _SRC_MANUAL)]

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(classes="omega-form-panel"):
            yield Static("ROTATION / BACKUP DES LOGS", classes="omega-title")

            yield Static("Action", classes="omega-subtitle")
            yield Select(
                [
                    ("Creer une sauvegarde manuelle immediatement", _MODE_MANUAL),
                    ("Configurer une automatisation de sauvegarde", _MODE_SCHEDULE),
                    ("Lister et gerer les automatisations en cours", _MODE_MANAGE),
                ],
                value=_MODE_MANUAL,
                id="mode-select",
            )

            yield Static("Source a sauvegarder", id="source-label", classes="omega-subtitle")
            yield Select(self._source_options(), id="source-select")
            with Horizontal(classes="omega-actions", id="pins-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button("Gerer les epingles", id="manage-pins")

            yield Static("Chemin manuel", id="manual-label", classes="omega-subtitle omega-hidden")
            yield Input(value="var/log/access.log", id="manual-input", classes="omega-hidden")

            yield Static("Frequence", id="freq-label", classes="omega-subtitle omega-hidden")
            yield Select(
                [(label, key) for key, (_, label) in _FREQ_OPTIONS.items()],
                value="weekly",
                id="freq-select",
                classes="omega-hidden",
            )
            yield Static("Intervalle personnalise (jours)", id="freq-custom-label", classes="omega-subtitle omega-hidden")
            yield Input(value="15", id="freq-custom-input", classes="omega-hidden")

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

    def on_mount(self) -> None:
        options = self._source_options()
        if options:
            self.query_one("#source-select", Select).value = options[0][1]
        self.query_one("#manage-label", Static).set_class(True, "omega-hidden")
        self.query_one("#automations-table", DataTable).set_class(True, "omega-hidden")
        self.query_one("#manage-actions", Horizontal).set_class(True, "omega-hidden")

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "mode-select":
            self._apply_mode(str(event.value))
        elif event.select.id == "source-select":
            is_manual = str(event.value) == _SRC_MANUAL
            self.query_one("#manual-label", Static).set_class(not is_manual, "omega-hidden")
            self.query_one("#manual-input", Input).set_class(not is_manual, "omega-hidden")
        elif event.select.id == "freq-select":
            is_custom = str(event.value) == "custom"
            self.query_one("#freq-custom-label", Static).set_class(not is_custom, "omega-hidden")
            self.query_one("#freq-custom-input", Input).set_class(not is_custom, "omega-hidden")

    def _apply_mode(self, mode: str) -> None:
        is_manage = mode == _MODE_MANAGE
        is_schedule = mode == _MODE_SCHEDULE
        source_relevant = mode in (_MODE_MANUAL, _MODE_SCHEDULE)

        self.query_one("#source-label", Static).set_class(not source_relevant, "omega-hidden")
        self.query_one("#source-select", Select).set_class(not source_relevant, "omega-hidden")
        self.query_one("#pins-actions", Horizontal).set_class(not source_relevant, "omega-hidden")
        if source_relevant:
            source = self.query_one("#source-select", Select).value
            is_manual = source == _SRC_MANUAL
            self.query_one("#manual-label", Static).set_class(not (source_relevant and is_manual), "omega-hidden")
            self.query_one("#manual-input", Input).set_class(not (source_relevant and is_manual), "omega-hidden")
        else:
            self.query_one("#manual-label", Static).set_class(True, "omega-hidden")
            self.query_one("#manual-input", Input).set_class(True, "omega-hidden")

        self.query_one("#freq-label", Static).set_class(not is_schedule, "omega-hidden")
        self.query_one("#freq-select", Select).set_class(not is_schedule, "omega-hidden")
        freq_is_custom = is_schedule and str(self.query_one("#freq-select", Select).value) == "custom"
        self.query_one("#freq-custom-label", Static).set_class(not freq_is_custom, "omega-hidden")
        self.query_one("#freq-custom-input", Input).set_class(not freq_is_custom, "omega-hidden")

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
        table.add_columns("Source", "Frequence", "Creee le")
        for idx, item in enumerate(self._load_automations()):
            table.add_row(
                item.get("source_path", ""),
                f"{item.get('interval_label', '')} ({item.get('days_interval', '?')}j)",
                item.get("created_at", ""),
                key=str(idx),
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss()
            return
        if event.button.id == "manage-pins":
            self.app.push_screen(PinnedPathsScreen(container=self._container), self._refresh_source_select)
            return
        if event.button.id == "delete-automation":
            self._delete_selected_automation()
            return
        if event.button.id != "launch":
            return

        mode = str(self.query_one("#mode-select", Select).value)
        if mode == _MODE_MANUAL:
            self._run_manual_backup()
        elif mode == _MODE_SCHEDULE:
            self._configure_schedule()

    def _refresh_source_select(self, _result: None) -> None:
        self.query_one("#source-select", Select).set_options(self._source_options())

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        self._selected_automation_index = int(str(event.row_key.value))

    def _delete_selected_automation(self) -> None:
        idx = getattr(self, "_selected_automation_index", None)
        automations = self._load_automations()
        if idx is None or not (0 <= idx < len(automations)):
            self.app.notify("Selectionnez d'abord une ligne.", severity="warning")
            return
        removed = automations.pop(idx)
        self._save_automations(automations)
        self.app.notify(f"Automatisation pour '{removed.get('source_path', '')}' supprimee.")
        self._selected_automation_index = None
        self._refresh_automations_table()

    def _resolve_source_path(self) -> Path | None:
        source = self.query_one("#source-select", Select).value
        if source == _SRC_MANUAL or source is None or source == Select.BLANK:
            selected_file = self.query_one("#manual-input", Input).value.strip()
        else:
            selected_file = str(source)
        if not selected_file:
            self.app.notify("Saisissez un chemin de fichier.", severity="warning")
            return None
        raw_path = Path(selected_file)
        if raw_path.exists():
            return raw_path
        resolved = (
            _PROJECT_ROOT / raw_path.relative_to(raw_path.anchor)
            if raw_path.is_absolute() else _PROJECT_ROOT / raw_path
        )
        if not resolved.exists():
            self.app.notify(f"Fichier introuvable : {resolved}", severity="error")
            return None
        return resolved

    def _run_manual_backup(self) -> None:
        source_path = self._resolve_source_path()
        if source_path is None:
            return

        command = RotateLogsCommand(persistence_port=self._container.get_persistence_port())
        result = command.execute(RotateLogsRequest(
            source_path=str(source_path), reason="Sauvegarde manuelle (menu 5.4)", keep=10,
        ))
        if not result.success:
            self.app.notify(f"Echec de la sauvegarde : {result.message}", severity="error")
            log_action_result(self._container, _ACTION_TITLE, status="failure", error=result.message)
            return

        src_size = source_path.stat().st_size
        dst_size = result.backup_size_bytes or 0
        ratio = (1 - (dst_size / src_size)) * 100 if src_size > 0 else 0
        message = f"Sauvegarde reussie ({src_size / 1024:.1f} KB -> {dst_size / 1024:.1f} KB, {ratio:.1f}% de gain)"
        if result.deleted_count:
            message += f", {result.deleted_count} ancienne(s) archive(s) supprimee(s)"
        self.app.notify(message)
        log_action_result(self._container, _ACTION_TITLE, status="success")
        self.dismiss()

    def _configure_schedule(self) -> None:
        source_path = self._resolve_source_path()
        if source_path is None:
            return

        freq_key = str(self.query_one("#freq-select", Select).value)
        if freq_key == "custom":
            raw = self.query_one("#freq-custom-input", Input).value.strip()
            if not (raw.isdigit() and int(raw) > 0):
                self.app.notify("Nombre de jours invalide.", severity="warning")
                return
            days_interval = int(raw)
            interval_label = f"Tous les {days_interval} jours"
        else:
            days_interval, interval_label = _FREQ_OPTIONS[freq_key]

        automations = self._load_automations()
        automations.append({
            "source_path": str(source_path),
            "days_interval": days_interval,
            "interval_label": interval_label,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        })
        self._save_automations(automations)

        self.app.notify(
            f"Regle de rotation configuree pour '{source_path.name}' ({interval_label}) — "
            f"destination : {BACKUPS_DIR}"
        )
        log_action_result(self._container, _ACTION_TITLE, status="success")
        self.dismiss()
