# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 2.2 — Bannir une liste d'IPs (toutes sources). Patron #3 le
plus riche : 6 sources possibles (saisie manuelle, fichier par defaut,
fichier Fail2ban par defaut, parcours de var/blocklist/, fichier
epingle, chemin libre), chacune n'affichant que son propre champ. La
gestion des epingles reutilise PinnedPathsScreen (Phase 2) plutot que de
dupliquer le CRUD ici. Logique identique a
interfaces/cli/actions.py::action_2_2_ban_list."""
from __future__ import annotations

import ipaddress
import os
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Input, Select, Static

from omega_fire.application.commands.ban_ip_all_backends import (
    BanIpAllBackendsRequest,
    BanIpToAllBackendsCommand,
)
from omega_fire.application.commands.manage_pinned_log_paths import ManagePinnedLogPathsCommand
from omega_fire.infrastructure.config.paths import (
    BLOCKLIST_DIR,
    DEFAULT_BLOCKLIST_FILE,
    DEFAULT_F2B_BLOCKLIST_FILE,
    DEFAULT_PINNED_FILES,
    RUNTIME_DIR,
)
from omega_fire.infrastructure.storage.files.json_store import JsonStore
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.screens.confirm import ConfirmScreen
from omega_fire.interfaces.tui.screens.pinned_paths_screen import PinnedPathsScreen
from omega_fire.interfaces.tui.support.action_audit import log_action_result
from omega_fire.shared.parsing import extract_ips

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ACTION_TITLE = "2.2 Bannir une liste d'IPs"
_ALL_BACKENDS = "__all__"
_BACKEND_CANDIDATES = ("nftables", "iptables", "ip6tables", "fail2ban")

_SRC_MANUAL = "manual"
_SRC_DEFAULT = "default"
_SRC_F2B_DEFAULT = "f2b_default"
_SRC_BROWSE = "browse"
_SRC_PINNED = "pinned"
_SRC_CUSTOM = "custom"


def _extract_valid_ips(text: str) -> set[str]:
    valid: set[str] = set()
    for candidate in extract_ips(text):
        try:
            valid.add(str(ipaddress.ip_address(candidate)))
        except ValueError:
            continue
    return valid


def _safe_extract_from_file(filepath: str) -> tuple[set[str], str]:
    """Retourne (IPs, message d'erreur eventuel)."""
    if not os.path.exists(filepath):
        return set(), f"Le fichier '{filepath}' n'existe pas."
    try:
        with open(filepath, "rb") as f:
            header = f.read(1024)
            if header.startswith(b"%PDF") or b"\x00" in header:
                return set(), "Le fichier selectionne est binaire/PDF (attendu : fichier texte)."
    except Exception as e:
        return set(), f"Erreur de lecture binaire : {e}"

    ips: set[str] = set()
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line_str = line.strip()
                if line_str and not line_str.startswith("#"):
                    ips |= _extract_valid_ips(line_str)
    except Exception as e:
        return set(), f"Erreur de lecture texte : {e}"
    return ips, ""


class BanIpListScreen(OmegaScreen):
    """Bannissement groupe d'IPs, depuis l'une de 6 sources possibles."""

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container
        self._supported_backends: list[str] = self._detect_supported_backends()
        self._pinned_command = ManagePinnedLogPathsCommand(
            JsonStore(RUNTIME_DIR),
            relative_path="blocklist_analysis_pinned_paths.json",
            defaults=[str(p) for p in DEFAULT_PINNED_FILES],
        )

    def _detect_supported_backends(self) -> list[str]:
        supported: list[str] = []
        for name in _BACKEND_CANDIDATES:
            try:
                if self._container.get_firewall_port(name) is not None:
                    supported.append(name)
            except Exception:
                continue
        return supported

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="omega-form-panel"):
            yield Static("BANNIR UNE LISTE D'IPs", classes="omega-title")

            yield Static("Source des adresses", classes="omega-subtitle")
            yield Select(
                [
                    ("Saisie manuelle (IPs separees par espaces/virgules)", _SRC_MANUAL),
                    (f"Fichier par defaut ({DEFAULT_BLOCKLIST_FILE.name})", _SRC_DEFAULT),
                    (f"Fichier Fail2ban par defaut ({DEFAULT_F2B_BLOCKLIST_FILE.name})", _SRC_F2B_DEFAULT),
                    ("Parcourir var/blocklist/", _SRC_BROWSE),
                    ("Fichier epingle", _SRC_PINNED),
                    ("Chemin de fichier personnalise", _SRC_CUSTOM),
                ],
                value=_SRC_MANUAL,
                id="source-select",
            )

            yield Static("IPs (separees par espaces/virgules)", id="manual-label", classes="omega-subtitle")
            yield Input(id="manual-input")

            yield Static("Fichier dans var/blocklist/", id="browse-label", classes="omega-subtitle omega-hidden")
            yield Select(self._browse_options(), id="browse-select", classes="omega-hidden")

            yield Static("Fichier epingle", id="pinned-label", classes="omega-subtitle omega-hidden")
            yield Select(self._pinned_options(), id="pinned-select", classes="omega-hidden")
            with Horizontal(classes="omega-actions", id="pinned-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button("Gerer les epingles", id="manage-pins")

            yield Static("Chemin complet du fichier", id="custom-label", classes="omega-subtitle omega-hidden")
            yield Input(id="custom-input", classes="omega-hidden")

            yield Static("Backend(s) cible(s)", classes="omega-subtitle")
            if self._supported_backends:
                options = [("Tous les backends (recommande)", _ALL_BACKENDS)] + [
                    (f"Uniquement {name} (diagnostic)", name) for name in self._supported_backends
                ]
                yield Select(options, value=_ALL_BACKENDS, id="backend-select")
            else:
                yield Static("Aucun backend disponible.", classes="omega-hint")

            yield Static("Commentaire (optionnel)", classes="omega-subtitle")
            yield Input(id="comment-input")

            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button("Bannir", id="launch", variant="primary")
                with Container(classes="omega-btn-frame"):
                    yield Button("Retour", id="back")
        yield Footer()

    def _browse_options(self) -> list[tuple[str, str]]:
        if not os.path.exists(str(BLOCKLIST_DIR)):
            return []
        files = [f for f in sorted(os.listdir(str(BLOCKLIST_DIR))) if os.path.isfile(os.path.join(str(BLOCKLIST_DIR), f))]
        return [(f, f) for f in files]

    def _pinned_options(self) -> list[tuple[str, str]]:
        return [(p, p) for p in self._pinned_command.list_paths()]

    def on_mount(self) -> None:
        self.query_one("#pinned-actions", Horizontal).set_class(True, "omega-hidden")

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id != "source-select":
            return
        source = str(event.value)
        self.query_one("#manual-label", Static).set_class(source != _SRC_MANUAL, "omega-hidden")
        self.query_one("#manual-input", Input).set_class(source != _SRC_MANUAL, "omega-hidden")
        self.query_one("#browse-label", Static).set_class(source != _SRC_BROWSE, "omega-hidden")
        self.query_one("#browse-select", Select).set_class(source != _SRC_BROWSE, "omega-hidden")
        self.query_one("#pinned-label", Static).set_class(source != _SRC_PINNED, "omega-hidden")
        self.query_one("#pinned-select", Select).set_class(source != _SRC_PINNED, "omega-hidden")
        self.query_one("#pinned-actions", Horizontal).set_class(source != _SRC_PINNED, "omega-hidden")
        self.query_one("#custom-label", Static).set_class(source != _SRC_CUSTOM, "omega-hidden")
        self.query_one("#custom-input", Input).set_class(source != _SRC_CUSTOM, "omega-hidden")

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
        select = self.query_one("#pinned-select", Select)
        select.set_options(self._pinned_options())

    def _launch(self) -> None:
        source = str(self.query_one("#source-select", Select).value)
        extracted_ips: set[str] = set()
        source_label = ""

        if source == _SRC_MANUAL:
            raw = self.query_one("#manual-input", Input).value.strip()
            if not raw:
                self.app.notify("Saisissez au moins une IP.", severity="warning")
                return
            extracted_ips = _extract_valid_ips(raw)
            source_label = "Saisie manuelle"

        elif source == _SRC_DEFAULT:
            source_label = f"Fichier {DEFAULT_BLOCKLIST_FILE.name}"
            extracted_ips, err = _safe_extract_from_file(str(DEFAULT_BLOCKLIST_FILE))
            if err:
                self.app.notify(err, severity="error")
                return

        elif source == _SRC_F2B_DEFAULT:
            source_label = f"Fichier {DEFAULT_F2B_BLOCKLIST_FILE.name}"
            extracted_ips, err = _safe_extract_from_file(str(DEFAULT_F2B_BLOCKLIST_FILE))
            if err:
                self.app.notify(err, severity="error")
                return

        elif source == _SRC_BROWSE:
            selected_file = self.query_one("#browse-select", Select).value
            if selected_file is None or selected_file == Select.BLANK:
                self.app.notify("Choisissez un fichier.", severity="warning")
                return
            source_label = f"Fichier '{selected_file}'"
            extracted_ips, err = _safe_extract_from_file(os.path.join(str(BLOCKLIST_DIR), str(selected_file)))
            if err:
                self.app.notify(err, severity="error")
                return

        elif source == _SRC_PINNED:
            target_path = self.query_one("#pinned-select", Select).value
            if target_path is None or target_path == Select.BLANK:
                self.app.notify("Choisissez un fichier epingle (ou epinglez-en un).", severity="warning")
                return
            source_label = f"Epingle '{os.path.basename(str(target_path))}'"
            extracted_ips, err = _safe_extract_from_file(str(target_path))
            if err:
                self.app.notify(err, severity="error")
                return

        elif source == _SRC_CUSTOM:
            target_path = self.query_one("#custom-input", Input).value.strip()
            if not target_path:
                self.app.notify("Saisissez un chemin de fichier.", severity="warning")
                return
            source_label = f"Fichier libre '{os.path.basename(target_path)}'"
            extracted_ips, err = _safe_extract_from_file(target_path)
            if err:
                self.app.notify(err, severity="error")
                return

        unique_ips = sorted(extracted_ips)
        if not unique_ips:
            self.app.notify("Aucune adresse IP valide trouvee dans la source.", severity="warning")
            return

        if not self._supported_backends:
            self.app.notify("Aucun backend disponible pour le bannissement.", severity="error")
            return
        backend_choice = str(self.query_one("#backend-select", Select).value)
        target_backends = (
            list(self._supported_backends) if backend_choice == _ALL_BACKENDS else [backend_choice]
        )
        comment = self.query_one("#comment-input", Input).value.strip()

        self.app.push_screen(
            ConfirmScreen(
                title="CONFIRMER LE BANNISSEMENT",
                message=(
                    f"Source : {source_label}\nIPs a bannir : {len(unique_ips)}\n"
                    f"Backend(s) : {', '.join(target_backends)}"
                ),
            ),
            lambda confirmed: self._ban_if_confirmed(confirmed, unique_ips, source_label, target_backends, comment),
        )

    def _ban_if_confirmed(
        self, confirmed: bool | None, unique_ips: list[str], source_label: str,
        target_backends: list[str], comment: str,
    ) -> None:
        if not confirmed:
            return

        adapters: dict[str, object] = {}
        for name in target_backends:
            try:
                adapters[name] = self._container.get_firewall_port(name)
            except Exception:
                adapters[name] = None

        ban_repository = getattr(self._container, "ban_repository", None)
        result = BanIpToAllBackendsCommand(adapters, ban_repository).execute(
            BanIpAllBackendsRequest(ips=unique_ips, comment=comment, target_backends=target_backends)
        )

        for backend, outcome in result.outcomes.items():
            self.app.notify(
                f"{len(outcome.banned)} nouvelle(s), {len(outcome.already_banned)} deja bannie(s), "
                f"{len(outcome.errors)} erreur(s).",
                title=f"{backend} ({source_label})",
                severity="information" if not outcome.errors else "warning",
            )
            for failed_ip, reason in outcome.errors:
                self.app.notify(f"{failed_ip} : {reason}", title=backend, severity="error")

        log_action_result(self._container, _ACTION_TITLE, status="success" if result.success else "failure")
        self.dismiss()
