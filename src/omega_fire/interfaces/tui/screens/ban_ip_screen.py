# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 2.1 — Bannir une IP unique. Premier ecran de la Phase 2 de la
feuille de route migration Textual : valide le PATRON #2 ("formulaire
court inconditionnel") sur une action reelle. Logique metier identique a
interfaces/cli/actions.py::action_2_1_ban_ip — seule la couche
presentation change (sequence de prompts -> formulaire valide d'un
coup), meme technique que omega-check/screens/scan_setup.py (D-008) :
validation imperative au bouton, erreurs via notify(), confirmation
finale via ConfirmScreen (patron #1) avant execution.

Note portee au passage (pas corrigee ici, hors perimetre d'un portage
UI) : `container.get_firewall_port("fail2ban")` leve ValueError (seuls
nftables/iptables/ip6tables sont geres par cette methode) — la detection
ci-dessous reproduit donc fidelement le meme comportement que le CLI
actuel, ou fail2ban n'apparait jamais dans ce choix de backend malgre
2.1 le listant dans ses capacites requises (menu_builder.py,
requires_any=["nftables","iptables","fail2ban_client"])."""
from __future__ import annotations

import ipaddress
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Input, Select, Static

from omega_fire.application.commands.ban_ip_all_backends import (
    BanIpAllBackendsRequest,
    BanIpToAllBackendsCommand,
)
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.screens.confirm import ConfirmScreen
from omega_fire.interfaces.tui.support.action_audit import log_action_result

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ACTION_TITLE = "2.1 Bannir une IP"
_ALL_BACKENDS = "__all__"
_BACKEND_CANDIDATES = ("nftables", "iptables", "ip6tables", "fail2ban")


class BanIpScreen(OmegaScreen):
    """Formulaire de bannissement d'une IP unique sur les backends detectes."""

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
            yield Static("BANNIR UNE IP", classes="omega-title")

            yield Static("Adresse IP", classes="omega-subtitle")
            yield Input(placeholder="ex. 192.168.1.10", id="ip-input")

            yield Static("Backend(s) cible(s)", classes="omega-subtitle")
            if self._supported_backends:
                options = [("Tous les backends (recommande)", _ALL_BACKENDS)] + [
                    (f"Uniquement {name} (diagnostic)", name) for name in self._supported_backends
                ]
                yield Select(options, value=_ALL_BACKENDS, id="backend-select")
            else:
                yield Static("Aucun backend disponible.", classes="omega-hint")

            yield Static("Commentaire (optionnel)", classes="omega-subtitle")
            yield Input(placeholder="ex. tentative bruteforce SSH", id="comment-input")

            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button("Bannir", id="launch", variant="primary")
                with Container(classes="omega-btn-frame"):
                    yield Button("Retour", id="back")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss()
            return
        if event.button.id != "launch":
            return

        if not self._supported_backends:
            self.app.notify("Aucun backend disponible pour le bannissement.", severity="error")
            return

        raw_ip = self.query_one("#ip-input", Input).value.strip()
        if not raw_ip:
            self.app.notify("Saisissez une adresse IP.", severity="warning")
            return
        try:
            # Normalisation vers la forme canonique (referentiel §62),
            # meme raison que action_2_1_ban_ip : une IPv6 non normalisee
            # doit correspondre exactement a celle stockee en base par un
            # ban/unban anterieur (comparaison SQL "WHERE ip = ?").
            ip = str(ipaddress.ip_address(raw_ip))
        except ValueError:
            self.app.notify(f"Format d'adresse IP invalide : '{raw_ip}'.", severity="warning")
            return

        backend_choice = str(self.query_one("#backend-select", Select).value)
        target_backends = (
            list(self._supported_backends) if backend_choice == _ALL_BACKENDS else [backend_choice]
        )

        comment = self.query_one("#comment-input", Input).value.strip()

        backend_label = ", ".join(target_backends)
        self.app.push_screen(
            ConfirmScreen(
                title="CONFIRMER LE BANNISSEMENT",
                message=(
                    f"IP : {ip}\nBackend(s) : {backend_label}\n"
                    f"Commentaire : {comment or '(aucun)'}"
                ),
            ),
            lambda confirmed: self._ban_if_confirmed(confirmed, ip, target_backends, comment),
        )

    def _ban_if_confirmed(
        self, confirmed: bool | None, ip: str, target_backends: list[str], comment: str
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
            BanIpAllBackendsRequest(ips=[ip], comment=comment, target_backends=target_backends)
        )

        for backend, outcome in result.outcomes.items():
            if outcome.banned:
                self.app.notify(f"IP {ip} bannie avec succes.", title=backend, severity="information")
            elif outcome.already_banned:
                self.app.notify(f"IP {ip} deja bannie (aucun doublon ajoute).", title=backend, severity="warning")
            for failed_ip, reason in outcome.errors:
                self.app.notify(f"Echec pour {failed_ip} : {reason}", title=backend, severity="error")

        log_action_result(self._container, _ACTION_TITLE, status="success" if result.success else "failure")
        self.dismiss()
