# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 2.3 — Debannir une IP unique. Miroir de BanIpScreen (2.1, Phase
2) — meme patron #2, sans champ commentaire (le CLI n'en a pas non plus
pour le debannissement). Logique identique a
interfaces/cli/actions.py::action_2_3_unban_ip."""
from __future__ import annotations

import ipaddress
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Input, Select, Static

from omega_fire.application.commands.unban_ip_all_backends import (
    UnbanIpAllBackendsRequest,
    UnbanIpToAllBackendsCommand,
)
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.screens.confirm import ConfirmScreen
from omega_fire.interfaces.tui.support.action_audit import log_action_result
from omega_fire.shared.i18n import _

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ACTION_TITLE = "2.3 Debannir une IP"
_ALL_BACKENDS = "__all__"
_BACKEND_CANDIDATES = ("nftables", "iptables", "ip6tables", "fail2ban")


class UnbanIpScreen(OmegaScreen):
    """Formulaire de debannissement d'une IP unique sur les backends detectes."""

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container
        self._supported_backends: list[str] = self._detect_supported_backends()

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
            yield Static(_("DÉBANNIR UNE IP"), classes="omega-title")

            yield Static(_("Adresse IP"), classes="omega-subtitle")
            yield Input(placeholder=_("ex. 192.168.1.10"), id="ip-input")

            yield Static(_("Backend(s) cible(s)"), classes="omega-subtitle")
            if self._supported_backends:
                options = [(_("Tous les backends (recommandé)"), _ALL_BACKENDS)] + [
                    (_("Uniquement {name} (diagnostic)").format(name=name), name) for name in self._supported_backends
                ]
                yield Select(options, value=_ALL_BACKENDS, id="backend-select")
            else:
                yield Static(_("Aucun backend disponible."), classes="omega-hint")

            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Débannir"), id="launch", variant="primary")
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Retour"), id="back")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss()
            return
        if event.button.id != "launch":
            return

        if not self._supported_backends:
            self.app.notify(_("Aucun backend disponible pour le débannissement."), severity="error")
            return

        raw_ip = self.query_one("#ip-input", Input).value.strip()
        if not raw_ip:
            self.app.notify(_("Saisissez une adresse IP."), severity="warning")
            return
        try:
            ip = str(ipaddress.ip_address(raw_ip))
        except ValueError:
            self.app.notify(_("Format d'adresse IP invalide : '{raw_ip}'.").format(raw_ip=raw_ip), severity="warning")
            return

        backend_choice = str(self.query_one("#backend-select", Select).value)
        target_backends = (
            list(self._supported_backends) if backend_choice == _ALL_BACKENDS else [backend_choice]
        )

        self.app.push_screen(
            ConfirmScreen(
                title=_("CONFIRMER LE DÉBANNISSEMENT"),
                message=_("IP : {ip}\nBackend(s) : {value}").format(ip=ip, value=', '.join(target_backends)),
            ),
            lambda confirmed: self._unban_if_confirmed(confirmed, ip, target_backends),
        )

    def _unban_if_confirmed(self, confirmed: bool | None, ip: str, target_backends: list[str]) -> None:
        if not confirmed:
            return

        adapters: dict[str, object] = {}
        for name in target_backends:
            try:
                adapters[name] = self._container.get_firewall_port(name)
            except Exception:
                adapters[name] = None

        ban_repository = getattr(self._container, "ban_repository", None)
        result = UnbanIpToAllBackendsCommand(adapters, ban_repository).execute(
            UnbanIpAllBackendsRequest(ips=[ip], target_backends=target_backends)
        )

        for backend, outcome in result.outcomes.items():
            if outcome.unbanned:
                self.app.notify(_("IP {ip} débannie avec succès.").format(ip=ip), title=backend, severity="information")
            elif outcome.already_free:
                self.app.notify(_("IP {ip} n'était pas bannie (déjà libre).").format(ip=ip), title=backend, severity="warning")
            for failed_ip, reason in outcome.errors:
                self.app.notify(_("Échec pour {failed_ip} : {reason}").format(failed_ip=failed_ip, reason=reason), title=backend, severity="error")

        log_action_result(self._container, _ACTION_TITLE, status="success" if result.success else "failure")
        self.dismiss()
