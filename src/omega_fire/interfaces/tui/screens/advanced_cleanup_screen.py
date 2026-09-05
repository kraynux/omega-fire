# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 5.7 — Nettoyage avance (par age/taille/extension). Patron #3
(3 champs conditionnels selon le critere choisi) + confirmation
destructive (patron #1). Logique identique a
interfaces/cli/actions.py::action_5_7_advanced_cleanup : app.log/
audit.log toujours exclus (fichiers actifs, geres par 1.5/7.3)."""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Input, Select, Static

from omega_fire.infrastructure.config.paths import (
    APP_LOG_PATH,
    AUDIT_LOG_PATH,
    BACKUPS_DIR,
    CACHE_DIR,
    EXPORTS_DIR,
    LOGS_DIR,
    _PROJECT_ROOT,
)
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.screens.confirm import ConfirmScreen
from omega_fire.interfaces.tui.support.action_audit import log_action_result

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ACTION_TITLE = "5.7 Nettoyage Avance"

_TARGET_DIRS: dict[str, list[Path]] = {
    "logs": [LOGS_DIR],
    "cache": [CACHE_DIR],
    "exports": [EXPORTS_DIR],
    "backups": [BACKUPS_DIR],
    "all": [LOGS_DIR, CACHE_DIR, EXPORTS_DIR, BACKUPS_DIR],
}


class AdvancedCleanupScreen(OmegaScreen):
    """Suppression ciblee de fichiers runtime par age/taille/extension."""

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="omega-form-panel"):
            yield Static("NETTOYAGE AVANCE DES FICHIERS", classes="omega-title")
            yield Static(
                "app.log et audit.log sont toujours exclus (fichiers actifs) — voir 1.5 / 7.3.",
                classes="omega-hint",
            )

            yield Static("Dossier cible", classes="omega-subtitle")
            yield Select(
                [
                    ("Tous les logs (var/logs/)", "logs"),
                    ("Cache temporaire (var/cache/)", "cache"),
                    ("Fichiers d'exports (var/exports/)", "exports"),
                    ("Archives de backups (var/backups/)", "backups"),
                    ("Tout l'environnement runtime (var/)", "all"),
                ],
                value="logs",
                id="target-select",
            )

            yield Static("Critere de filtrage", classes="omega-subtitle")
            yield Select(
                [
                    ("Age (fichiers plus anciens que X jours)", "age"),
                    ("Taille minimale (fichiers plus grands que X MB)", "size"),
                    ("Extension (ex: .log, .tmp, .gz, .json)", "extension"),
                    ("Age + Taille combines", "both"),
                ],
                value="age",
                id="criteria-select",
            )

            yield Static("Age minimum (jours)", id="age-label", classes="omega-subtitle")
            yield Input(value="30", id="age-input")

            yield Static("Taille minimale (MB)", id="size-label", classes="omega-subtitle omega-hidden")
            yield Input(value="5.0", id="size-input", classes="omega-hidden")

            yield Static("Extension recherchee", id="ext-label", classes="omega-subtitle omega-hidden")
            yield Input(value="log", id="ext-input", classes="omega-hidden")

            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button("Analyser", id="analyze", variant="primary")
                with Container(classes="omega-btn-frame"):
                    yield Button("Retour", id="back")
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_conditional_fields("age")

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "criteria-select":
            self._refresh_conditional_fields(str(event.value))

    def _refresh_conditional_fields(self, criteria: str) -> None:
        show_age = criteria in ("age", "both")
        show_size = criteria in ("size", "both")
        show_ext = criteria == "extension"
        self.query_one("#age-label", Static).set_class(not show_age, "omega-hidden")
        self.query_one("#age-input", Input).set_class(not show_age, "omega-hidden")
        self.query_one("#size-label", Static).set_class(not show_size, "omega-hidden")
        self.query_one("#size-input", Input).set_class(not show_size, "omega-hidden")
        self.query_one("#ext-label", Static).set_class(not show_ext, "omega-hidden")
        self.query_one("#ext-input", Input).set_class(not show_ext, "omega-hidden")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss()
            return
        if event.button.id != "analyze":
            return

        target = str(self.query_one("#target-select", Select).value)
        criteria = str(self.query_one("#criteria-select", Select).value)
        selected_dirs = _TARGET_DIRS[target]

        min_age_days: int | None = None
        min_size_mb: float | None = None
        target_extension: str | None = None

        if criteria in ("age", "both"):
            age_raw = self.query_one("#age-input", Input).value.strip()
            min_age_days = int(age_raw) if age_raw.isdigit() else 30
        if criteria in ("size", "both"):
            size_raw = self.query_one("#size-input", Input).value.strip()
            try:
                min_size_mb = float(size_raw) if size_raw else 5.0
            except ValueError:
                min_size_mb = 5.0
        if criteria == "extension":
            ext_raw = self.query_one("#ext-input", Input).value.strip().lower()
            target_extension = (ext_raw or "log").replace(".", "")

        for d in selected_dirs:
            d.mkdir(parents=True, exist_ok=True)

        protected = {APP_LOG_PATH.resolve(), AUDIT_LOG_PATH.resolve()}
        candidates: list[Path] = []
        for d in selected_dirs:
            for f in d.rglob("*"):
                if f.is_file() and f.resolve() not in protected:
                    candidates.append(f)

        now = datetime.now()
        matching: list[Path] = []
        for f in candidates:
            try:
                stat = f.stat()
                mtime = datetime.fromtimestamp(stat.st_mtime)
                size_mb = stat.st_size / (1024 * 1024)
                if min_age_days is not None and now - mtime < timedelta(days=min_age_days):
                    continue
                if min_size_mb is not None and size_mb < min_size_mb:
                    continue
                if target_extension is not None and not f.name.lower().endswith(f".{target_extension}"):
                    continue
                matching.append(f)
            except Exception:
                continue

        if not matching:
            self.app.notify("Aucun fichier ne correspond a vos criteres de filtrage.", severity="warning")
            return

        total_mb = sum(f.stat().st_size for f in matching) / (1024 * 1024)
        self.app.push_screen(
            ConfirmScreen(
                title="CONFIRMER LE NETTOYAGE",
                message=f"Supprimer definitivement {len(matching)} fichier(s) ({total_mb:.2f} MB) ?",
            ),
            lambda confirmed: self._delete_if_confirmed(confirmed, matching, total_mb),
        )

    def _delete_if_confirmed(self, confirmed: bool | None, matching: list[Path], total_mb: float) -> None:
        if not confirmed:
            return

        deleted_count = 0
        error_count = 0
        for f in matching:
            try:
                f.unlink()
                deleted_count += 1
            except Exception as e:
                error_count += 1
                self.app.notify(f"Erreur pour '{f.name}' : {e}", severity="error")

        if deleted_count:
            self.app.notify(f"Nettoyage termine : {deleted_count} fichier(s) supprime(s), {total_mb:.2f} MB liberes.")
        if error_count:
            self.app.notify(f"{error_count} erreur(s) lors de la suppression.", severity="error")

        log_action_result(self._container, _ACTION_TITLE, status="success" if deleted_count else "failure")
        self.dismiss()
