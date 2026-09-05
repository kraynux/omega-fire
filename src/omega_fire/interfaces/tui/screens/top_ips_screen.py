# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 5.2 — Analyser les IPs (Top N). Patron #3 riche : source
(epingle ou chemin manuel), Top N, periode, chacun avec ses champs
conditionnels. Logique identique a
interfaces/cli/actions.py::action_5_2_top_ips. La gestion des epingles
reutilise PinnedPathsScreen (Phase 2/2.2) plutot que de dupliquer le
CRUD ici."""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, DataTable, Footer, Header, Input, Select, Static

from omega_fire.application.commands.manage_pinned_log_paths import ManagePinnedLogPathsCommand
from omega_fire.infrastructure.config.paths import DEFAULT_PINNED_FILES, RUNTIME_DIR, VAR_DIR
from omega_fire.infrastructure.storage.files.json_store import JsonStore
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.screens.ban_ip_list_screen import _extract_valid_ips
from omega_fire.interfaces.tui.screens.pinned_paths_screen import PinnedPathsScreen

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_SRC_MANUAL = "__manual__"

_LOG_PATTERN = re.compile(
    r'^(?P<ip>\S+)\s+\S+\s+\S+\s+\[(?P<time>[^\]]+)\]\s+"(?P<method>\S+)\s+(?P<path>\S+)[^"]*"\s+(?P<status>\d+)\s+(?P<size>\d+|-)'
)


def _format_size(size: int) -> str:
    if size > 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    if size > 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size} B"


class TopIpsScreen(OmegaScreen):
    """Analyse Top N des IPs les plus actives dans un log ou fichier brut."""

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container
        self._pinned_command = ManagePinnedLogPathsCommand(
            JsonStore(RUNTIME_DIR),
            relative_path="blocklist_analysis_pinned_paths.json",
            defaults=[str(p) for p in DEFAULT_PINNED_FILES],
        )

    def _source_options(self) -> list[tuple[str, str]]:
        pinned = self._pinned_command.list_paths()
        return [(p, p) for p in pinned] + [("Chemin manuel", _SRC_MANUAL)]

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(classes="omega-form-panel"):
            yield Static("ANALYSER LES IPs (TOP N)", classes="omega-title")

            yield Static("Source (fichier log ou blocklist)", classes="omega-subtitle")
            yield Select(self._source_options(), id="source-select")
            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button("Gerer les epingles", id="manage-pins")

            yield Static("Chemin manuel", id="manual-label", classes="omega-subtitle omega-hidden")
            yield Input(
                value=str(VAR_DIR / "log" / "access.log"),
                id="manual-input",
                classes="omega-hidden",
            )

            yield Static("Nombre d'IPs (Top N)", classes="omega-subtitle")
            yield Select(
                [("Top 10", "10"), ("Top 50", "50"), ("Top 100", "100"), ("Personnalise", "custom")],
                value="10",
                id="topn-select",
            )
            yield Static("Nombre personnalise", id="topn-custom-label", classes="omega-subtitle omega-hidden")
            yield Input(value="20", id="topn-custom-input", classes="omega-hidden")

            yield Static("Periode a analyser", classes="omega-subtitle")
            yield Select(
                [("Tout le fichier", "all"), ("Derniere heure", "1h"), ("Dernieres 24 heures", "24h"),
                 ("Derniers 7 jours", "7d"), ("Saisie manuelle (jours)", "custom")],
                value="all",
                id="period-select",
            )
            yield Static("Nombre de jours", id="period-custom-label", classes="omega-subtitle omega-hidden")
            yield Input(value="30", id="period-custom-input", classes="omega-hidden")

            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button("Analyser", id="launch", variant="primary")
                with Container(classes="omega-btn-frame"):
                    yield Button("Retour", id="back")

            yield Static("", id="result-hint", classes="omega-hint")
            yield DataTable(id="result-table")
        yield Footer()

    def on_mount(self) -> None:
        options = self._source_options()
        if options:
            self.query_one("#source-select", Select).value = options[0][1]

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "source-select":
            is_manual = str(event.value) == _SRC_MANUAL
            self.query_one("#manual-label", Static).set_class(not is_manual, "omega-hidden")
            self.query_one("#manual-input", Input).set_class(not is_manual, "omega-hidden")
        elif event.select.id == "topn-select":
            is_custom = str(event.value) == "custom"
            self.query_one("#topn-custom-label", Static).set_class(not is_custom, "omega-hidden")
            self.query_one("#topn-custom-input", Input).set_class(not is_custom, "omega-hidden")
        elif event.select.id == "period-select":
            is_custom = str(event.value) == "custom"
            self.query_one("#period-custom-label", Static).set_class(not is_custom, "omega-hidden")
            self.query_one("#period-custom-input", Input).set_class(not is_custom, "omega-hidden")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss()
            return
        if event.button.id == "manage-pins":
            self.app.push_screen(PinnedPathsScreen(container=self._container), self._refresh_source_select)
            return
        if event.button.id != "launch":
            return
        self._analyze()

    def _refresh_source_select(self, _result: None) -> None:
        select = self.query_one("#source-select", Select)
        select.set_options(self._source_options())

    def _analyze(self) -> None:
        source = self.query_one("#source-select", Select).value
        if source == _SRC_MANUAL or source is None or source == Select.BLANK:
            selected_file = self.query_one("#manual-input", Input).value.strip()
        else:
            selected_file = str(source)
        if not selected_file:
            self.app.notify("Saisissez un chemin de fichier.", severity="warning")
            return
        log_path = Path(selected_file)

        topn_choice = str(self.query_one("#topn-select", Select).value)
        if topn_choice == "custom":
            raw = self.query_one("#topn-custom-input", Input).value.strip()
            limit_n = int(raw) if raw.isdigit() and int(raw) > 0 else 20
        else:
            limit_n = int(topn_choice)

        period_choice = str(self.query_one("#period-select", Select).value)
        now = datetime.now()
        time_limit = None
        if period_choice == "1h":
            time_limit = now - timedelta(hours=1)
        elif period_choice == "24h":
            time_limit = now - timedelta(days=1)
        elif period_choice == "7d":
            time_limit = now - timedelta(days=7)
        elif period_choice == "custom":
            raw = self.query_one("#period-custom-input", Input).value.strip()
            if raw.isdigit() and int(raw) > 0:
                time_limit = now - timedelta(days=int(raw))

        ip_counts: dict[str, int] = {}
        ip_bytes: dict[str, int] = {}
        total_occurrences = 0
        is_raw_ip_file = False

        try:
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
            for line in lines:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                match = _LOG_PATTERN.search(line)
                if match:
                    ip = match.group("ip")
                    raw_time = match.group("time")
                    raw_size = match.group("size")
                    if time_limit:
                        try:
                            date_str = raw_time.split()[0]
                            log_dt = datetime.strptime(date_str, "%d/%b/%Y:%H:%M:%S")
                            if log_dt < time_limit:
                                continue
                        except ValueError:
                            pass
                    bytes_sent = int(raw_size) if raw_size.isdigit() else 0
                    ip_counts[ip] = ip_counts.get(ip, 0) + 1
                    ip_bytes[ip] = ip_bytes.get(ip, 0) + bytes_sent
                    total_occurrences += 1
                else:
                    raw_ips = _extract_valid_ips(line)
                    if raw_ips:
                        is_raw_ip_file = True
                        for ip in raw_ips:
                            ip_counts[ip] = ip_counts.get(ip, 0) + 1
                            total_occurrences += 1
        except Exception as e:
            self.app.notify(f"Erreur lors de la lecture du fichier : {e}", severity="error")
            return

        table = self.query_one("#result-table", DataTable)
        table.clear(columns=True)
        hint = self.query_one("#result-hint", Static)

        if not ip_counts:
            hint.update("Aucune IP valide n'a pu etre extraite de ce fichier.")
            return

        sorted_ips = sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)[:limit_n]
        duplicates_count = sum(count - 1 for count in ip_counts.values() if count > 1)

        if is_raw_ip_file:
            table.add_columns("Rang", "Adresse IP", "Occurrences", "Statut")
            for rank, (ip, count) in enumerate(sorted_ips, start=1):
                status = "Doublon" if count > 1 else "Unique"
                table.add_row(f"#{rank}", ip, str(count), status)
            if duplicates_count > 0:
                hint.update(f"Total entrees : {total_occurrences} | IPs uniques : {len(ip_counts)} | Doublons : {duplicates_count}")
            else:
                hint.update(f"Fichier propre : {len(ip_counts)} IPs uniques sans doublon.")
        else:
            table.add_columns("Rang", "Adresse IP", "Requetes", "% Trafic", "Volume")
            for rank, (ip, count) in enumerate(sorted_ips, start=1):
                pct = (count / total_occurrences * 100) if total_occurrences > 0 else 0
                table.add_row(f"#{rank}", ip, f"{count:,}", f"{pct:.1f}%", _format_size(ip_bytes.get(ip, 0)))
            hint.update(f"Analyse terminee ({len(sorted_ips)} IPs affichees sur {total_occurrences} requetes).")
