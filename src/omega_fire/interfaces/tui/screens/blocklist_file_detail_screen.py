# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 2.7 (detail) — Actions sur un fichier blocklist gere : afficher
le contenu, ajouter/retirer une IP, renommer, supprimer, bannir le
contenu. Logique identique au sous-menu _file_submenu() de
interfaces/cli/actions.py::action_2_7_import_file."""
from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Footer, Header, Input, Select, Static

from omega_fire.application.commands.ban_ip_all_backends import (
    BanIpAllBackendsRequest,
    BanIpToAllBackendsCommand,
)
from omega_fire.application.commands.manage_blocklist_file import ManageBlocklistFileCommand
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.screens.confirm import ConfirmScreen
from omega_fire.interfaces.tui.support.action_audit import log_action_result
from omega_fire.shared.i18n import _

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ACTION_TITLE = "2.7 Gestion des fichiers Blocklist"
_ALL_BACKENDS = "__all__"
_BACKEND_CANDIDATES = ("nftables", "iptables", "ip6tables", "fail2ban")


class BlocklistFileDetailScreen(OmegaScreen):
    """CRUD sur un fichier blocklist choisi depuis BlocklistFilesScreen."""

    def __init__(self, *, container: DependencyContainer, manager: ManageBlocklistFileCommand, file_name: str) -> None:
        super().__init__()
        self._container = container
        self._manager = manager
        self._file_name = file_name
        self._renamed = False

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(classes="omega-panel"):
            yield Static(_("FICHIER : {file_name}").format(file_name=self._file_name), classes="omega-title", id="file-title")
            yield Static("", id="content-view")

            yield Static(_("Ajouter une IP / CIDR"), classes="omega-subtitle")
            yield Input(placeholder=_("ex. 192.168.1.10 ou 10.0.0.0/24"), id="add-ip-input")
            yield Input(placeholder=_("Commentaire (optionnel)"), id="add-comment-input")
            with Horizontal(classes="omega-actions"), Container(classes="omega-btn-frame"):
                yield Button(_("Ajouter"), id="add-ip")

            yield Static(_("Retirer une IP / CIDR"), classes="omega-subtitle")
            yield Input(placeholder=_("ex. 192.168.1.10"), id="remove-ip-input")
            with Horizontal(classes="omega-actions"), Container(classes="omega-btn-frame"):
                yield Button(_("Retirer"), id="remove-ip")

            yield Static(_("Renommer ce fichier"), classes="omega-subtitle")
            yield Input(placeholder="nouveau-nom.txt", id="rename-input")
            with Horizontal(classes="omega-actions"), Container(classes="omega-btn-frame"):
                yield Button(_("Renommer"), id="rename")

            yield Static(_("Bannir le contenu de ce fichier"), classes="omega-subtitle")
            options = [(_("Tous les backends (recommandé)"), _ALL_BACKENDS)] + [
                (name, name) for name in self._detect_supported_backends()
            ]
            yield Select(options, value=_ALL_BACKENDS, id="ban-backend-select")
            yield Input(placeholder=_("Commentaire (optionnel)"), id="ban-comment-input")
            with Horizontal(classes="omega-actions"), Container(classes="omega-btn-frame"):
                yield Button(_("Bannir le contenu"), id="ban-content", variant="error")

            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Supprimer ce fichier"), id="delete", variant="error")
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Retour"), id="back")
        yield Footer()

    def _detect_supported_backends(self) -> list[str]:
        supported: list[str] = []
        for name in _BACKEND_CANDIDATES:
            try:
                if self._container.get_firewall_port(name) is not None:
                    supported.append(name)
            except Exception:
                continue
        return supported

    def on_mount(self) -> None:
        self._refresh_content()

    def _refresh_content(self) -> None:
        content = self._manager.load_file(self._file_name)
        view = self.query_one("#content-view", Static)
        if not content.success:
            view.update(content.message)
            return
        lines = []
        if content.valid_ips:
            lines.append(_("[b]{count} IP/réseau valide(s)[/b] : ").format(count=len(content.valid_ips)) + ", ".join(content.valid_ips))
        else:
            lines.append(_("Aucune IP valide dans ce fichier."))
        if content.rejected_lines:
            lines.append(_("\n[b]{count} ligne(s) à corriger :[/b]").format(count=len(content.rejected_lines)))
            for rl in content.rejected_lines:
                lines.append(f"  L{rl.line_number} : {rl.raw!r} — {rl.reason or ''}")
        view.update("\n".join(lines))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss(self._file_name if self._renamed else None)
            return

        if event.button.id == "add-ip":
            ip = self.query_one("#add-ip-input", Input).value.strip()
            if not ip:
                self.app.notify(_("Saisissez une IP ou un CIDR."), severity="warning")
                return
            comment = self.query_one("#add-comment-input", Input).value.strip()
            result = self._manager.add_ip(self._file_name, ip, comment)
            self.app.notify(result.message, severity="information" if result.success else "error")
            if result.success:
                self.query_one("#add-ip-input", Input).value = ""
                self.query_one("#add-comment-input", Input).value = ""
                self._refresh_content()
            return

        if event.button.id == "remove-ip":
            ip = self.query_one("#remove-ip-input", Input).value.strip()
            if not ip:
                self.app.notify(_("Saisissez une IP ou un CIDR."), severity="warning")
                return
            result = self._manager.remove_ip(self._file_name, ip)
            self.app.notify(result.message, severity="information" if result.success else "error")
            if result.success:
                self.query_one("#remove-ip-input", Input).value = ""
                self._refresh_content()
            return

        if event.button.id == "rename":
            new_name = self.query_one("#rename-input", Input).value.strip()
            if not new_name:
                self.app.notify(_("Saisissez un nouveau nom."), severity="warning")
                return
            result = self._manager.rename_file(self._file_name, new_name)
            self.app.notify(result.message, severity="information" if result.success else "error")
            if result.success:
                self._file_name = new_name
                self._renamed = True
                self.query_one("#file-title", Static).update(_("FICHIER : {file_name}").format(file_name=self._file_name))
                self.query_one("#rename-input", Input).value = ""
                self._refresh_content()
            return

        if event.button.id == "delete":
            self.app.push_screen(
                ConfirmScreen(title=_("CONFIRMER LA SUPPRESSION"), message=_("Supprimer '{file_name}' ?").format(file_name=self._file_name)),
                self._delete_if_confirmed,
            )
            return

        if event.button.id == "ban-content":
            self._ban_content()

    def _delete_if_confirmed(self, confirmed: bool | None) -> None:
        if not confirmed:
            return
        result = self._manager.delete_file(self._file_name)
        self.app.notify(result.message, severity="information" if result.success else "error")
        if result.success:
            log_action_result(self._container, _ACTION_TITLE, status="success")
            self.dismiss("__deleted__")

    def _ban_content(self) -> None:
        content = self._manager.load_file(self._file_name)
        if not content.success or not content.valid_ips:
            self.app.notify(_("Aucune IP valide à bannir dans ce fichier."), severity="warning")
            return

        supported = self._detect_supported_backends()
        if not supported:
            self.app.notify(_("Aucun backend disponible pour le bannissement."), severity="error")
            return
        backend_choice = str(self.query_one("#ban-backend-select", Select).value)
        target_backends = list(supported) if backend_choice == _ALL_BACKENDS else [backend_choice]
        comment = self.query_one("#ban-comment-input", Input).value.strip()

        self.app.push_screen(
            ConfirmScreen(
                title=_("CONFIRMER LE BANNISSEMENT"),
                message=_("Bannir {count} IP(s) du fichier '{file_name}' sur : {value} ?").format(count=len(content.valid_ips), file_name=self._file_name, value=', '.join(target_backends)),
            ),
            lambda confirmed: self._ban_if_confirmed(confirmed, content.valid_ips, target_backends, comment),
        )

    def _ban_if_confirmed(self, confirmed: bool | None, valid_ips: list[str], target_backends: list[str], comment: str) -> None:
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
            BanIpAllBackendsRequest(ips=valid_ips, comment=comment, target_backends=target_backends)
        )
        for backend, outcome in result.outcomes.items():
            self.app.notify(
                _("{count} nouvelle(s), {count2} déjà bannie(s), {count3} erreur(s).").format(count=len(outcome.banned), count2=len(outcome.already_banned), count3=len(outcome.errors)),
                title=backend,
                severity="information" if not outcome.errors else "warning",
            )
        log_action_result(self._container, _ACTION_TITLE, status="success" if result.success else "failure")
