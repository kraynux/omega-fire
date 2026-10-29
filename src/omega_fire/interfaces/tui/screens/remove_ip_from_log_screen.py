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
from omega_fire.infrastructure.config.paths import BLOCKLIST_DIR, DEFAULT_PINNED_FILES, RUNTIME_DIR, _PROJECT_ROOT
from omega_fire.infrastructure.exporters.export_catalog import ip_list_exports
from omega_fire.infrastructure.exporters.top_ips_exporter import read_exported_ips
from omega_fire.infrastructure.storage.files.json_store import JsonStore
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.screens.checklist import CheckListScreen
from omega_fire.interfaces.tui.screens.confirm import ConfirmScreen
from omega_fire.interfaces.tui.screens.export_picker import ExportPickerScreen
from omega_fire.interfaces.tui.screens.pinned_paths_screen import PinnedPathsScreen
from omega_fire.interfaces.tui.support.action_audit import log_action_result
from omega_fire.shared.i18n import _

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ACTION_TITLE = "5.5 Supprimer une IP des logs"
_SRC_MANUAL = "__manual__"
_IP_SEPARATORS = re.compile(r"[\s,;]+")


def parse_ip_list(raw: str) -> tuple[list[str], list[str]]:
    """Version 3.5 : plusieurs IPs separees par virgule, espace ou point-virgule.
    Retourne (IPs valides sans doublon, saisies invalides)."""
    valid: list[str] = []
    invalid: list[str] = []
    for token in _IP_SEPARATORS.split(raw.strip()):
        if not token:
            continue
        try:
            ip = str(ipaddress.ip_address(token))
        except ValueError:
            invalid.append(token)
            continue
        if ip not in valid:
            valid.append(ip)
    return valid, invalid


def split_lines_by_ips(lines: list[str], ips: list[str]) -> tuple[dict[str, int], list[str]]:
    """(lignes retirees par IP, lignes conservees). Une ligne qui contient plusieurs des
    IPs n'est comptee qu'une fois, pour la premiere IP de la liste."""
    patterns = [(ip, re.compile(rf"(?<![\w.:]){re.escape(ip)}(?![\w:]|\.\d)")) for ip in ips]
    counts = {ip: 0 for ip in ips}
    kept: list[str] = []
    for line in lines:
        for ip, pattern in patterns:
            if pattern.search(line):
                counts[ip] += 1
                break
        else:
            kept.append(line)
    return counts, kept


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
        return [(p, p) for p in self._pinned_command.list_paths()] + [(_("Chemin manuel"), _SRC_MANUAL)]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="omega-form-panel"):
            yield Static(_("SUPPRIMER UNE IP DES LOGS"), classes="omega-title")

            yield Static(_("Fichier source"), classes="omega-subtitle")
            yield Select(self._source_options(), id="source-select", prompt=_("Sélectionner"))
            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Gérer les épingles"), id="manage-pins")

            yield Static(_("Chemin manuel"), id="manual-label", classes="omega-subtitle omega-hidden")
            yield Input(value="var/log/access.log", id="manual-input", classes="omega-hidden")

            yield Static(_("Adresse(s) IP à retirer (séparées par des virgules)"), classes="omega-subtitle")
            yield Input(id="ip-input")
            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Charger depuis un export"), id="load-export")

            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Rechercher et supprimer"), id="launch", variant="error")
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Retour"), id="back")
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
        if event.button.id == "load-export":
            self._pick_export()
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
            self.app.notify(_("Saisissez un chemin de fichier."), severity="warning")
            return

        target_path = self._resolve_target_path(selected_file)
        if target_path is None:
            self.app.notify(_("Fichier introuvable : {selected_file}").format(selected_file=selected_file), severity="error")
            return

        target_ips, invalid = parse_ip_list(self.query_one("#ip-input", Input).value)
        if invalid:
            self.app.notify(_("Format d'adresse IP invalide : {values}").format(values=", ".join(invalid)),
                            severity="warning")
            return
        if not target_ips:
            self.app.notify(_("Saisissez une adresse IP."), severity="warning")
            return

        try:
            with open(target_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except Exception as e:
            self.app.notify(_("Impossible de lire le fichier : {e}").format(e=e), severity="error")
            return

        counts, cleaned_lines = split_lines_by_ips(lines, target_ips)
        occurrences = sum(counts.values())
        if occurrences == 0:
            self.app.notify(_("Aucune de ces IPs n'a été trouvée dans '{name}'.").format(name=target_path.name),
                            severity="warning")
            return

        found = [ip for ip in target_ips if counts[ip]]
        missing = [ip for ip in target_ips if not counts[ip]]
        details = "\n".join(_("  {ip} : {count} ligne(s)").format(ip=ip, count=counts[ip]) for ip in found)
        if missing:
            details += "\n" + _("Absentes du fichier : {values}").format(values=", ".join(missing))
        self.app.push_screen(
            ConfirmScreen(
                title=_("CONFIRMER LA SUPPRESSION"),
                message=_("Fichier : {name}\n{details}\n{occurrences} ligne(s) retirée(s), {count} ligne(s) "
                          "restante(s) après purge.").format(
                    name=target_path.name, details=details, occurrences=occurrences, count=len(cleaned_lines)),
            ),
            lambda confirmed: self._delete_if_confirmed(confirmed, target_path, found, occurrences, cleaned_lines),
        )

    def _delete_if_confirmed(self, confirmed: bool | None, target_path: Path, target_ips: list[str], occurrences: int, cleaned_lines: list[str]) -> None:
        if not confirmed:
            return
        try:
            with open(target_path, "w", encoding="utf-8") as f:
                f.writelines(cleaned_lines)
        except Exception as e:
            self.app.notify(_("Erreur lors de l'écriture dans le fichier : {e}").format(e=e), severity="error")
            log_action_result(self._container, _ACTION_TITLE, status="failure", error=str(e))
            return

        self.app.notify(_("{occurrences} ligne(s) retirée(s) de {name} ({count} IP(s)).").format(
            occurrences=occurrences, name=target_path.name, count=len(target_ips)))
        log_action_result(self._container, _ACTION_TITLE, status="success")
        self.dismiss()

    def _pick_export(self) -> None:
        """Version 3.5 : recharger les IPs d'un export (5.4 Top N, 6.1, 4.8) au lieu de
        les recopier a la main."""
        files = ip_list_exports(self._container.exports_dir, BLOCKLIST_DIR)
        if not files:
            self.app.notify(_("Aucun export d'IPs trouvé : exportez d'abord un résultat en 5.4."),
                            severity="warning")
            return
        self.app.push_screen(
            ExportPickerScreen(title=_("CHARGER UNE LISTE D'IPs"),
                               message=_("Exports contenant des IPs, Top N (5.4) en premier."), files=files),
            self._pick_ips,
        )

    def _pick_ips(self, path: Path | None) -> None:
        if path is None:
            return
        try:
            ips = read_exported_ips(path)
        except OSError as e:
            self.app.notify(_("Impossible de lire le fichier : {e}").format(e=e), severity="error")
            return
        if not ips:
            self.app.notify(_("Aucune IP dans '{name}'.").format(name=path.name), severity="warning")
            return
        current, _invalid = parse_ip_list(self.query_one("#ip-input", Input).value)
        self.app.push_screen(
            CheckListScreen(
                title=_("IPs À RETIRER DES LOGS"),
                message=_("{name} — cochez les IPs à retirer du fichier source.").format(name=path.name),
                items=[(ip, ip) for ip in ips],
                checked=set(current),
            ),
            self._apply_picked_ips,
        )

    def _apply_picked_ips(self, ips: list[str] | None) -> None:
        if ips is None:
            return
        self.query_one("#ip-input", Input).value = ", ".join(ips)
