# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 2.8 — Exporter les IPs bannies vers un fichier. Patron #3 (6
destinations possibles, champs conditionnels). Logique identique a
interfaces/cli/actions.py::action_2_8_export_file, y compris la
persistance de l'historique recent et des epingles corrigee en Phase 0
de la feuille de route (meme bug de fond que les 8 sites deja fixes)."""
from __future__ import annotations

import os
from datetime import datetime
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Input, Select, Static

from omega_fire.application.commands.manage_pinned_log_paths import ManagePinnedLogPathsCommand
from omega_fire.infrastructure.config.paths import (
    BLOCKLIST_DIR,
    DEFAULT_BLOCKLIST_FILE,
    DEFAULT_PINNED_FILES,
    RUNTIME_DIR,
)
from omega_fire.infrastructure.storage.files.json_store import JsonStore
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.screens.ban_ip_list_screen import _extract_valid_ips
from omega_fire.interfaces.tui.screens.pinned_paths_screen import PinnedPathsScreen
from omega_fire.interfaces.tui.support.action_audit import log_action_result

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ACTION_TITLE = "2.8 Exporter les IP bannies"
_RECENT_EXPORT_FILES_PATH = "recent_export_files.json"

_DST_DEFAULT = "default"
_DST_BACKUP = "backup"
_DST_BROWSE = "browse"
_DST_RECENT = "recent"
_DST_MANUAL = "manual"
_DST_PINNED = "pinned"

_ALL_BACKENDS = "__all__"


class ExportBlocklistFileScreen(OmegaScreen):
    """Export groupe des IPs bannies (tous backends) vers un fichier."""

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container
        self._supported_backends = self._detect_supported_backends()
        self._pinned_command = ManagePinnedLogPathsCommand(
            JsonStore(RUNTIME_DIR),
            relative_path="blocklist_analysis_pinned_paths.json",
            defaults=[str(p) for p in DEFAULT_PINNED_FILES],
        )
        self._recent_store = JsonStore(RUNTIME_DIR)

    def _detect_supported_backends(self) -> list[str]:
        supported = ["nftables", "iptables", "ip6tables"]
        try:
            if self._container.get_firewall_port("fail2ban") is not None:
                supported.append("fail2ban")
        except Exception:
            pass
        return supported

    def _recent_files(self) -> list[str]:
        if self._recent_store.exists(_RECENT_EXPORT_FILES_PATH):
            try:
                return self._recent_store.load(_RECENT_EXPORT_FILES_PATH)
            except Exception:
                return []
        return []

    def _browse_files(self) -> list[str]:
        if not os.path.exists(str(BLOCKLIST_DIR)):
            return []
        files = [f for f in os.listdir(str(BLOCKLIST_DIR)) if os.path.isfile(os.path.join(str(BLOCKLIST_DIR), f))]
        files.sort(key=lambda x: os.path.getmtime(os.path.join(str(BLOCKLIST_DIR), x)), reverse=True)
        return files

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="omega-form-panel"):
            yield Static("EXPORTER LES IPs BANNIES", classes="omega-title")

            yield Static("Destination", classes="omega-subtitle")
            yield Select(
                [
                    (f"Fichier par defaut ({DEFAULT_BLOCKLIST_FILE.name})", _DST_DEFAULT),
                    ("Sauvegarde horodatee (nouveau fichier)", _DST_BACKUP),
                    ("Parcourir var/blocklist/", _DST_BROWSE),
                    ("Fichier recent", _DST_RECENT),
                    ("Chemin manuel", _DST_MANUAL),
                    ("Fichier epingle", _DST_PINNED),
                ],
                value=_DST_DEFAULT,
                id="dest-select",
            )

            yield Static("Fichier dans var/blocklist/", id="browse-label", classes="omega-subtitle omega-hidden")
            yield Select(self._browse_select_options(), id="browse-select", classes="omega-hidden")

            yield Static("Fichier recent", id="recent-label", classes="omega-subtitle omega-hidden")
            yield Select(self._recent_select_options(), id="recent-select", classes="omega-hidden")

            yield Static("Chemin complet", id="manual-label", classes="omega-subtitle omega-hidden")
            yield Input(id="manual-input", classes="omega-hidden")

            yield Static("Fichier epingle", id="pinned-label", classes="omega-subtitle omega-hidden")
            yield Select(self._pinned_select_options(), id="pinned-select", classes="omega-hidden")
            with Horizontal(classes="omega-actions", id="pinned-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button("Gerer les epingles", id="manage-pins")

            yield Static("Mode d'ecriture", id="mode-label", classes="omega-subtitle")
            yield Select(
                [("Ecraser (remplace tout)", "w"), ("Rajouter (ajoute a la fin)", "a"),
                 ("Incrementer (nouvelles IP uniquement)", "inc")],
                value="w",
                id="mode-select",
            )

            yield Static("Backend(s) source", classes="omega-subtitle")
            yield Select(
                [("Tous les backends", _ALL_BACKENDS)] + [(n, n) for n in self._supported_backends],
                value=_ALL_BACKENDS,
                id="backend-select",
            )

            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button("Exporter", id="launch", variant="primary")
                with Container(classes="omega-btn-frame"):
                    yield Button("Retour", id="back")
        yield Footer()

    def _browse_select_options(self) -> list[tuple[str, str]]:
        return [(f, f) for f in self._browse_files()]

    def _recent_select_options(self) -> list[tuple[str, str]]:
        return [(p, p) for p in self._recent_files()]

    def _pinned_select_options(self) -> list[tuple[str, str]]:
        return [(p, p) for p in self._pinned_command.list_paths()]

    def on_mount(self) -> None:
        self.query_one("#pinned-actions", Horizontal).set_class(True, "omega-hidden")

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id != "dest-select":
            return
        dest = str(event.value)
        self.query_one("#browse-label", Static).set_class(dest != _DST_BROWSE, "omega-hidden")
        self.query_one("#browse-select", Select).set_class(dest != _DST_BROWSE, "omega-hidden")
        self.query_one("#recent-label", Static).set_class(dest != _DST_RECENT, "omega-hidden")
        self.query_one("#recent-select", Select).set_class(dest != _DST_RECENT, "omega-hidden")
        self.query_one("#manual-label", Static).set_class(dest != _DST_MANUAL, "omega-hidden")
        self.query_one("#manual-input", Input).set_class(dest != _DST_MANUAL, "omega-hidden")
        self.query_one("#pinned-label", Static).set_class(dest != _DST_PINNED, "omega-hidden")
        self.query_one("#pinned-select", Select).set_class(dest != _DST_PINNED, "omega-hidden")
        self.query_one("#pinned-actions", Horizontal).set_class(dest != _DST_PINNED, "omega-hidden")
        # Mode d'ecriture n'a pas de sens pour une sauvegarde horodatee
        # (toujours un nouveau fichier, ecrase par definition).
        self.query_one("#mode-label", Static).set_class(dest == _DST_BACKUP, "omega-hidden")
        self.query_one("#mode-select", Select).set_class(dest == _DST_BACKUP, "omega-hidden")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss()
            return
        if event.button.id == "manage-pins":
            self.app.push_screen(PinnedPathsScreen(container=self._container), self._refresh_pinned_select)
            return
        if event.button.id != "launch":
            return
        self._launch()

    def _refresh_pinned_select(self, _result: None) -> None:
        self.query_one("#pinned-select", Select).set_options(self._pinned_select_options())

    def _launch(self) -> None:
        dest = str(self.query_one("#dest-select", Select).value)
        write_mode = "w"

        if dest == _DST_DEFAULT:
            file_path = str(DEFAULT_BLOCKLIST_FILE)
            write_mode = str(self.query_one("#mode-select", Select).value)

        elif dest == _DST_BACKUP:
            ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            file_path = os.path.join(str(BLOCKLIST_DIR), f"blocklist_backup_{ts}.txt")
            write_mode = "w"

        elif dest == _DST_BROWSE:
            selected = self.query_one("#browse-select", Select).value
            if selected is None or selected == Select.BLANK:
                self.app.notify("Choisissez un fichier.", severity="warning")
                return
            file_path = os.path.join(str(BLOCKLIST_DIR), str(selected))
            write_mode = str(self.query_one("#mode-select", Select).value)

        elif dest == _DST_RECENT:
            selected = self.query_one("#recent-select", Select).value
            if selected is None or selected == Select.BLANK:
                self.app.notify("Choisissez un fichier recent.", severity="warning")
                return
            file_path = str(selected)
            write_mode = str(self.query_one("#mode-select", Select).value)

        elif dest == _DST_MANUAL:
            file_path = self.query_one("#manual-input", Input).value.strip()
            if not file_path:
                self.app.notify("Saisissez un chemin de fichier.", severity="warning")
                return
            write_mode = str(self.query_one("#mode-select", Select).value)

        elif dest == _DST_PINNED:
            selected = self.query_one("#pinned-select", Select).value
            if selected is None or selected == Select.BLANK:
                self.app.notify("Choisissez un fichier epingle (ou epinglez-en un).", severity="warning")
                return
            file_path = str(selected)
            write_mode = str(self.query_one("#mode-select", Select).value)

        else:
            return

        backend_choice = str(self.query_one("#backend-select", Select).value)
        target_backends = (
            list(self._supported_backends) if backend_choice == _ALL_BACKENDS else [backend_choice]
        )

        self._export(file_path, write_mode, target_backends)

    def _export(self, file_path: str, write_mode: str, target_backends: list[str]) -> None:
        recent_files = self._recent_files()
        if file_path and file_path not in recent_files:
            recent_files.insert(0, file_path)
            try:
                self._recent_store.save(_RECENT_EXPORT_FILES_PATH, recent_files[:5])
            except Exception:
                pass

        new_items: dict[str, str] = {}
        for b_name in target_backends:
            try:
                adapter = self._container.get_firewall_port(b_name)
            except Exception:
                continue
            if not adapter:
                continue
            try:
                bans = getattr(adapter, "list_bans", lambda: [])() or getattr(adapter, "list_banned_ips", lambda: [])()
            except Exception:
                continue
            for item in bans:
                ip = item.get("ip") if isinstance(item, dict) else getattr(item, "ip", str(item))
                comment = item.get("comment", "") if isinstance(item, dict) else getattr(item, "comment", "")
                if ip:
                    clean_ip = str(ip).split("/")[0].strip()
                    line = f"{clean_ip} # [{b_name}] {comment}".strip() if comment else f"{clean_ip} # [{b_name}]"
                    new_items[clean_ip] = line

        if not new_items:
            self.app.notify("Aucune IP a exporter.", severity="warning")
            return

        already_present_count = 0
        added_count = 0
        mode_label = {"w": "Ecraser", "a": "Rajouter", "inc": "Incrementer"}.get(write_mode, "Inconnu")

        try:
            parent = os.path.dirname(file_path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if write_mode == "w":
                lines = [f"# OmegaFire Export - {now_str}", *new_items.values()]
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines) + "\n")
                added_count = len(new_items)

            elif write_mode == "a":
                lines = [f"\n# OmegaFire Rajout - {now_str}", *new_items.values()]
                with open(file_path, "a", encoding="utf-8") as f:
                    f.write("\n".join(lines) + "\n")
                added_count = len(new_items)

            elif write_mode == "inc":
                existing_ips: set[str] = set()
                if os.path.exists(file_path):
                    with open(file_path, "r", encoding="utf-8") as f:
                        existing_ips = _extract_valid_ips(f.read())
                to_add = [line for ip, line in new_items.items() if ip not in existing_ips]
                already_present_count = len(new_items) - len(to_add)
                added_count = len(to_add)
                if to_add:
                    lines = [f"\n# OmegaFire Increment - {now_str}", *to_add]
                    with open(file_path, "a", encoding="utf-8") as f:
                        f.write("\n".join(lines) + "\n")
        except Exception as e:
            self.app.notify(f"Erreur ecriture : {e}", severity="error")
            log_action_result(self._container, _ACTION_TITLE, status="failure", error=str(e))
            return

        self.app.notify(
            f"[{mode_label}] {added_count} nouvelle(s) IP(s) ecrite(s), {already_present_count} deja presente(s), "
            f"dans '{file_path}'.",
        )
        log_action_result(self._container, _ACTION_TITLE, status="success")
        self.dismiss()
