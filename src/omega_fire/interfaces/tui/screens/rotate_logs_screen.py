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
import sys
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.widgets import Button, DataTable, Footer, Header, Input, Select, Static

from omega_fire.application.commands.manage_pinned_log_paths import ManagePinnedLogPathsCommand
from omega_fire.application.commands.rotate_logs import RotateLogsCommand, RotateLogsRequest
from omega_fire.application.commands.rotation_automation import (
    ScheduleResult,
    install_rotation_schedule,
    remove_rotation_schedule,
    rotation_schedule_status,
)
from omega_fire.domain.logs.rotation_schedule import DEFAULT_KEEP, KEEP_CHOICES, next_run
from omega_fire.infrastructure.config.paths import (
    BACKUPS_DIR,
    DEFAULT_PINNED_FILES,
    RUNTIME_DIR,
    _PROJECT_ROOT,
)
from omega_fire.infrastructure.storage.files.json_store import JsonStore
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.screens._log_sources import log_source_options
from omega_fire.interfaces.tui.screens.pinned_paths_screen import PinnedPathsScreen
from omega_fire.interfaces.tui.support.action_audit import log_action_result
from omega_fire.shared.i18n import _

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ACTION_TITLE = "5.6 Rotation / Backup des logs"
_AUTO_FILE = "scheduled_rotations.json"

_MODE_MANUAL = "manual"
_MODE_SCHEDULE = "schedule"
_MODE_MANAGE = "manage"

_SRC_MANUAL = "__manual__"

_FREQ_OPTIONS: dict[str, tuple[int, str]] = {
    "daily": (1, _("Tous les jours")),
    "weekly": (7, _("Toutes les semaines")),
    "monthly": (30, _("Tous les mois")),
    "quarterly": (90, _("Tous les trimestres")),
    "semiannual": (180, _("Tous les semestres")),
    "yearly": (364, _("Tous les ans")),
    "custom": (0, _("Personnalisé")),
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
        # Bibliotheque (5.1) en tete, puis epingles, puis chemin manuel (2026-11-09).
        return log_source_options(self._pinned_command.list_paths(), _SRC_MANUAL)

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(classes="omega-form-panel"):
            yield Static(_("ROTATION / BACKUP DES LOGS"), classes="omega-title")

            yield Static(_("Action"), classes="omega-subtitle")
            yield Select(
                [
                    (_("Créer une sauvegarde manuelle immédiatement"), _MODE_MANUAL),
                    (_("Configurer une automatisation de sauvegarde"), _MODE_SCHEDULE),
                    (_("Lister et gérer les automatisations en cours"), _MODE_MANAGE),
                ],
                value=_MODE_MANUAL,
                id="mode-select",
            )

            yield Static(_("Source à sauvegarder"), id="source-label", classes="omega-subtitle")
            yield Select(self._source_options(), id="source-select", prompt=_("Sélectionner"))
            with Horizontal(classes="omega-actions", id="pins-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Gérer les épingles"), id="manage-pins")

            yield Static(_("Chemin manuel"), id="manual-label", classes="omega-subtitle omega-hidden")
            yield Input(value="var/log/access.log", id="manual-input", classes="omega-hidden")

            yield Static(_("Fréquence"), id="freq-label", classes="omega-subtitle omega-hidden")
            yield Select(
                [(label, key) for key, (_ignored, label) in _FREQ_OPTIONS.items()],
                value="weekly",
                id="freq-select",
                classes="omega-hidden",
            )
            yield Static(_("Intervalle personnalisé (jours)"), id="freq-custom-label", classes="omega-subtitle omega-hidden")
            yield Input(value="15", id="freq-custom-input", classes="omega-hidden")
            # Sauvegardes conservees par log (comme omega-serv / omega-log, 2026-11-09).
            yield Static(_("Sauvegardes conservées"), id="keep-label", classes="omega-subtitle omega-hidden")
            yield Select([(str(count), str(count)) for count in KEEP_CHOICES], value=str(DEFAULT_KEEP),
                         allow_blank=False, id="keep-select", classes="omega-hidden")

            yield Static(_("Automatisations planifiées"), id="manage-label", classes="omega-subtitle omega-hidden")
            yield DataTable(id="automations-table", classes="omega-hidden")
            # Execution reelle des automatisations (3.6) : tache quotidienne root (timer systemd ou crontab).
            yield Static("", id="schedule-status", classes="omega-hint omega-hidden")
            with Horizontal(classes="omega-actions", id="manage-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Supprimer la sélection"), id="delete-automation", variant="error")
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Réinstaller l'exécution"), id="install-schedule")
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Désinstaller l'exécution"), id="remove-schedule")

            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Valider"), id="launch", variant="primary")
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Retour"), id="back")
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
        self.query_one("#keep-label", Static).set_class(not is_schedule, "omega-hidden")
        self.query_one("#keep-select", Select).set_class(not is_schedule, "omega-hidden")

        self.query_one("#manage-label", Static).set_class(not is_manage, "omega-hidden")
        self.query_one("#schedule-status", Static).set_class(not is_manage, "omega-hidden")
        table = self.query_one("#automations-table", DataTable)
        table.set_class(not is_manage, "omega-hidden")
        self.query_one("#manage-actions", Horizontal).set_class(not is_manage, "omega-hidden")
        self.query_one("#launch", Button).set_class(is_manage, "omega-hidden")
        if is_manage:
            self._refresh_automations_table()
            self._refresh_schedule_status()

    def _refresh_automations_table(self) -> None:
        table = self.query_one("#automations-table", DataTable)
        table.clear(columns=True)
        table.cursor_type = "row"
        table.add_columns(_("Source"), _("Fréquence"), _("Gardées"), _("Créée le"), _("Dernière sauvegarde"),
                          _("Prochaine"), _("Résultat"))
        for idx, item in enumerate(self._load_automations()):
            due = next_run(item)
            if "last_success" not in item:
                result = "-"
            else:
                result = _("réussie") if item.get("last_success") else _("échec : {message}").format(
                    message=item.get("last_result", ""))
            table.add_row(
                item.get("source_path", ""),
                f"{item.get('interval_label', '')} ({item.get('days_interval', '?')}j)",
                str(item.get("keep") or DEFAULT_KEEP),
                item.get("created_at", ""),
                str(item.get("last_run_at") or "-").replace("T", " ")[:16],
                due.strftime("%Y-%m-%d") if due is not None else "-",
                result,
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
        if event.button.id == "install-schedule":
            self._schedule_in_thread(install=True)
            return
        if event.button.id == "remove-schedule":
            self._schedule_in_thread(install=False)
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
            self.app.notify(_("Sélectionnez d'abord une ligne."), severity="warning")
            return
        removed = automations.pop(idx)
        self._save_automations(automations)
        if not automations:
            self._schedule_in_thread(install=False)  # plus aucune automatisation : tache quotidienne retiree
        self.app.notify(_("Automatisation pour '{value}' supprimée.").format(value=removed.get('source_path', '')))
        self._selected_automation_index = None
        self._refresh_automations_table()

    # ------------------------------------------------------------------
    # Execution quotidienne des automatisations (3.6, porte d'omega-log / omega-serv, version root)
    # ------------------------------------------------------------------
    def _refresh_schedule_status(self) -> None:
        self.run_worker(lambda: self._show_schedule(rotation_schedule_status()), thread=True, group="rotation-status")

    def _schedule_in_thread(self, *, install: bool) -> None:
        def work() -> None:
            if install:
                result = install_rotation_schedule(_PROJECT_ROOT, sys.executable)
            else:
                result = remove_rotation_schedule()
            if result.message:
                self.app.call_from_thread(self.app.notify, result.message,
                                          severity="information" if result.success else "warning", timeout=12)
            self._show_schedule(rotation_schedule_status())

        self.run_worker(work, thread=True, group="rotation-schedule")

    def _show_schedule(self, status: ScheduleResult) -> None:
        def update() -> None:
            try:
                self.query_one("#schedule-status", Static).update(status.message)
            except NoMatches:
                pass  # ecran deja ferme

        self.app.call_from_thread(update)

    def _resolve_source_path(self) -> Path | None:
        source = self.query_one("#source-select", Select).value
        if source == _SRC_MANUAL or source is None or source == Select.BLANK:
            selected_file = self.query_one("#manual-input", Input).value.strip()
        else:
            selected_file = str(source)
        if not selected_file:
            self.app.notify(_("Saisissez un chemin de fichier."), severity="warning")
            return None
        raw_path = Path(selected_file)
        if raw_path.exists():
            return raw_path
        resolved = (
            _PROJECT_ROOT / raw_path.relative_to(raw_path.anchor)
            if raw_path.is_absolute() else _PROJECT_ROOT / raw_path
        )
        if not resolved.exists():
            self.app.notify(_("Fichier introuvable : {resolved}").format(resolved=resolved), severity="error")
            return None
        return resolved

    def _run_manual_backup(self) -> None:
        source_path = self._resolve_source_path()
        if source_path is None:
            return

        command = RotateLogsCommand(persistence_port=self._container.get_persistence_port())
        result = command.execute(RotateLogsRequest(
            source_path=str(source_path), reason="Sauvegarde manuelle (menu 5.6)", keep=10,
        ))
        if not result.success:
            self.app.notify(_("Échec de la sauvegarde : {message}").format(message=result.message), severity="error")
            log_action_result(self._container, _ACTION_TITLE, status="failure", error=result.message)
            return

        src_size = source_path.stat().st_size
        dst_size = result.backup_size_bytes or 0
        ratio = (1 - (dst_size / src_size)) * 100 if src_size > 0 else 0
        message = _("Sauvegarde réussie ({value:.1f} KB -> {value2:.1f} KB, {ratio:.1f}% de gain)").format(value=src_size / 1024, value2=dst_size / 1024, ratio=ratio)
        if result.deleted_count:
            message += _(", {deleted_count} ancienne(s) archive(s) supprimée(s)").format(deleted_count=result.deleted_count)
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
                self.app.notify(_("Nombre de jours invalide."), severity="warning")
                return
            days_interval = int(raw)
            interval_label = _("Tous les {days_interval} jours").format(days_interval=days_interval)
        else:
            days_interval, interval_label = _FREQ_OPTIONS[freq_key]

        automations = self._load_automations()
        automations.append({
            "source_path": str(source_path),
            "days_interval": days_interval,
            "interval_label": interval_label,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "keep": int(str(self.query_one("#keep-select", Select).value)),
        })
        self._save_automations(automations)
        if len(automations) == 1 or not rotation_schedule_status().success:
            # Premiere automatisation (ou tache absente) : installe l'execution quotidienne (3.6).
            self._schedule_in_thread(install=True)

        self.app.notify(
            _("Règle de rotation configurée pour '{name}' ({interval_label}) — destination : {BACKUPS_DIR}").format(name=source_path.name, interval_label=interval_label, BACKUPS_DIR=BACKUPS_DIR)
        )
        log_action_result(self._container, _ACTION_TITLE, status="success")
        self.dismiss()
