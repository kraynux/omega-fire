# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 5.3 — Supprimer une IP d'un fichier source (log ou blocklist).
Meme selection de source que 5.2 (epingle/chemin manuel, gestion des
epingles via PinnedPathsScreen), puis saisie d'IP + confirmation
destructive (patron #1). Logique identique a
interfaces/cli/actions.py::action_5_3_remove_ip_logs."""
from __future__ import annotations

import ipaddress
import re
from pathlib import Path
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Input, Select, Static

from omega_fire.application.commands.manage_pinned_log_paths import ManagePinnedLogPathsCommand
from omega_fire.infrastructure.config.paths import DEFAULT_PINNED_FILES, RUNTIME_DIR, _PROJECT_ROOT
from omega_fire.infrastructure.storage.files.json_store import JsonStore
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.screens.confirm import ConfirmScreen
from omega_fire.interfaces.tui.screens.pinned_paths_screen import PinnedPathsScreen
from omega_fire.interfaces.tui.support.action_audit import log_action_result

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ACTION_TITLE = "5.3 Supprimer IP"
_SRC_MANUAL = "__manual__"


class RemoveIpFromLogScreen(OmegaScreen):
    """Retrait de toutes les occurrences d'une IP dans un fichier source."""

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container
        self._pinned_command = ManagePinnedLogPathsCommand(
            JsonStore(RUNTIME_DIR),
            relative_path="blocklist_analysis_pinned_paths.json",
            defaults=[str(p) for p in DEFAULT_PINNED_FILES],
        )

    def _source_options(self) -> list[tuple[str, str]]:
        return [(p, p) for p in self._pinned_command.list_paths()] + [("Chemin manuel", _SRC_MANUAL)]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="omega-form-panel"):
            yield Static("SUPPRIMER UNE IP DES LOGS", classes="omega-title")

            yield Static("Fichier source", classes="omega-subtitle")
            yield Select(self._source_options(), id="source-select")
            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button("Gerer les epingles", id="manage-pins")

            yield Static("Chemin manuel", id="manual-label", classes="omega-subtitle omega-hidden")
            yield Input(value="var/log/access.log", id="manual-input", classes="omega-hidden")

            yield Static("Adresse IP a retirer", classes="omega-subtitle")
            yield Input(id="ip-input")

            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button("Rechercher et supprimer", id="launch", variant="error")
                with Container(classes="omega-btn-frame"):
                    yield Button("Retour", id="back")
        yield Footer()

    def on_mount(self) -> None:
        options = self._source_options()
        if options:
            self.query_one("#source-select", Select).value = options[0][1]

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id != "source-select":
            return
        is_manual = str(event.value) == _SRC_MANUAL
        self.query_one("#manual-label", Static).set_class(not is_manual, "omega-hidden")
        self.query_one("#manual-input", Input).set_class(not is_manual, "omega-hidden")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss()
            return
        if event.button.id == "manage-pins":
            self.app.push_screen(PinnedPathsScreen(container=self._container), self._refresh_source_select)
            return
        if event.button.id != "launch":
            return
        self._launch()

    def _refresh_source_select(self, _result: None) -> None:
        self.query_one("#source-select", Select).set_options(self._source_options())

    def _resolve_target_path(self, selected_file: str) -> Path | None:
        raw_path = Path(selected_file)
        if raw_path.exists():
            return raw_path
        target_path = (
            _PROJECT_ROOT / raw_path.relative_to(raw_path.anchor)
            if raw_path.is_absolute() else _PROJECT_ROOT / raw_path
        )
        return target_path if target_path.exists() else None

    def _launch(self) -> None:
        source = self.query_one("#source-select", Select).value
        if source == _SRC_MANUAL or source is None or source == Select.BLANK:
            selected_file = self.query_one("#manual-input", Input).value.strip()
        else:
            selected_file = str(source)
        if not selected_file:
            self.app.notify("Saisissez un chemin de fichier.", severity="warning")
            return

        target_path = self._resolve_target_path(selected_file)
        if target_path is None:
            self.app.notify(f"Fichier introuvable : {selected_file}", severity="error")
            return

        target_ip = self.query_one("#ip-input", Input).value.strip()
        if not target_ip:
            self.app.notify("Saisissez une adresse IP.", severity="warning")
            return
        try:
            ipaddress.ip_address(target_ip)
        except ValueError:
            self.app.notify("Format d'adresse IP invalide.", severity="warning")
            return

        try:
            with open(target_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except Exception as e:
            self.app.notify(f"Impossible de lire le fichier : {e}", severity="error")
            return

        matched_lines = []
        cleaned_lines = []
        pattern = re.compile(rf'\b{re.escape(target_ip)}\b')
        for line in lines:
            if pattern.search(line):
                matched_lines.append(line)
            else:
                cleaned_lines.append(line)

        occurrences = len(matched_lines)
        if occurrences == 0:
            self.app.notify(f"L'adresse IP {target_ip} n'a pas ete trouvee dans '{target_path.name}'.", severity="warning")
            return

        self.app.push_screen(
            ConfirmScreen(
                title="CONFIRMER LA SUPPRESSION",
                message=(
                    f"Fichier : {target_path.name}\nIP : {target_ip}\n"
                    f"{occurrences} occurrence(s) trouvee(s), {len(cleaned_lines)} ligne(s) restante(s) apres purge."
                ),
            ),
            lambda confirmed: self._delete_if_confirmed(confirmed, target_path, target_ip, occurrences, cleaned_lines),
        )

    def _delete_if_confirmed(self, confirmed: bool | None, target_path: Path, target_ip: str, occurrences: int, cleaned_lines: list[str]) -> None:
        if not confirmed:
            return
        try:
            with open(target_path, "w", encoding="utf-8") as f:
                f.writelines(cleaned_lines)
        except Exception as e:
            self.app.notify(f"Erreur lors de l'ecriture dans le fichier : {e}", severity="error")
            log_action_result(self._container, _ACTION_TITLE, status="failure", error=str(e))
            return

        self.app.notify(f"{occurrences} occurrence(s) de {target_ip} retiree(s) de {target_path.name}.")
        log_action_result(self._container, _ACTION_TITLE, status="success")
        self.dismiss()
