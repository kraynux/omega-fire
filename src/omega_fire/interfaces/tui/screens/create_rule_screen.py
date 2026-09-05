# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 3.1 — Creer une regle avancee (iptables/nftables). Le wizard a
15 prompts le plus profond du CLI, reduit ici a un seul formulaire avec
un champ conditionnel (le port de destination, pertinent seulement pour
tcp/udp) et une interface reseau choisie dans une liste detectee + repli
manuel. Logique identique a
interfaces/cli/actions.py::action_3_1_create_advanced_rule."""
from __future__ import annotations

import ipaddress
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Footer, Header, Input, Select, Static

from omega_fire.application.commands.create_rule_all_backends import (
    CreateRuleAllBackendsRequest,
    CreateRuleToAllBackendsCommand,
)
from omega_fire.infrastructure.probe.network_probe import list_network_interfaces
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.screens.confirm import ConfirmScreen
from omega_fire.interfaces.tui.support.action_audit import log_action_result

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ACTION_TITLE = "3.1 Creer une regle avancee"
_ALL_BACKENDS = "__all__"
_IFACE_ANY = "__any__"
_IFACE_MANUAL = "__manual__"


class CreateRuleScreen(OmegaScreen):
    """Formulaire de creation d'une regle de filtrage avancee."""

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container
        self._available_backends = self._detect_available_backends()
        self._detected_interfaces = list_network_interfaces() or []

    def _detect_available_backends(self) -> list[str]:
        available: list[str] = []
        registry = getattr(self._container, "capability_registry", None)
        if registry is not None:
            if registry.is_available("nftables"):
                available.append("nftables")
            if registry.is_available("iptables"):
                available.append("iptables")
        return available

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(classes="omega-form-panel"):
            yield Static("CREER UNE REGLE AVANCEE", classes="omega-title")

            if not self._available_backends:
                yield Static("Aucun backend firewall disponible (nftables/iptables non detectes).", classes="omega-hint")
                with Horizontal(classes="omega-actions"), Container(classes="omega-btn-frame"):
                    yield Button("Retour", id="back")
                yield Footer()
                return

            yield Static("Backend(s) cible(s)", classes="omega-subtitle")
            options = [("Tous les backends (recommande)", _ALL_BACKENDS)] + [
                (f"Uniquement {b} (diagnostic)", b) for b in self._available_backends
            ]
            yield Select(options, value=_ALL_BACKENDS, id="backend-select")

            yield Static("Nom de la regle", classes="omega-subtitle")
            yield Input(placeholder="ex. BLOCK_SSH_ATTACKS", id="name-input")

            yield Static("Description (optionnelle)", classes="omega-subtitle")
            yield Input(id="description-input")

            yield Static("Action", classes="omega-subtitle")
            yield Select(
                [("DROP (bloquer silencieusement)", "DROP"), ("REJECT (rejeter avec notification)", "REJECT"),
                 ("ACCEPT (autoriser)", "ACCEPT")],
                value="DROP",
                id="action-select",
            )

            yield Static("Chaine / Flux", classes="omega-subtitle")
            yield Select(
                [("INPUT (trafic entrant)", "INPUT"), ("FORWARD (trafic route/transitant)", "FORWARD"),
                 ("OUTPUT (trafic sortant)", "OUTPUT")],
                value="INPUT",
                id="chain-select",
            )

            yield Static("Protocole", classes="omega-subtitle")
            yield Select(
                [("TCP", "tcp"), ("UDP", "udp"), ("ICMP", "icmp"), ("ALL (tous protocoles)", "all")],
                value="tcp",
                id="protocol-select",
            )

            yield Static("IP/Subnet source (vide = ANY)", classes="omega-subtitle")
            yield Input(placeholder="ex. 192.168.1.50 ou 10.0.0.0/24", id="src-input")

            yield Static("IP/Subnet destination (vide = ANY)", classes="omega-subtitle")
            yield Input(placeholder="ex. 192.168.1.1", id="dst-input")

            yield Static("Port destination (vide = ANY)", id="port-label", classes="omega-subtitle")
            yield Input(placeholder="ex. 22, 80, 443", id="port-input")

            yield Static("Interface reseau", classes="omega-subtitle")
            iface_options = [("ANY (toutes interfaces)", _IFACE_ANY)] + [
                (name, name) for name in self._detected_interfaces
            ] + [("Saisie manuelle", _IFACE_MANUAL)]
            yield Select(iface_options, value=_IFACE_ANY, id="iface-select")
            yield Static("Nom de l'interface", id="iface-manual-label", classes="omega-subtitle omega-hidden")
            yield Input(id="iface-manual-input", classes="omega-hidden")

            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button("Creer", id="launch", variant="primary")
                with Container(classes="omega-btn-frame"):
                    yield Button("Retour", id="back")
        yield Footer()

    def on_mount(self) -> None:
        if self._available_backends:
            self._refresh_conditional_fields()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id in ("protocol-select", "iface-select"):
            self._refresh_conditional_fields()

    def _refresh_conditional_fields(self) -> None:
        protocol = str(self.query_one("#protocol-select", Select).value)
        port_relevant = protocol in ("tcp", "udp")
        self.query_one("#port-label", Static).set_class(not port_relevant, "omega-hidden")
        self.query_one("#port-input", Input).set_class(not port_relevant, "omega-hidden")

        iface = str(self.query_one("#iface-select", Select).value)
        is_manual = iface == _IFACE_MANUAL
        self.query_one("#iface-manual-label", Static).set_class(not is_manual, "omega-hidden")
        self.query_one("#iface-manual-input", Input).set_class(not is_manual, "omega-hidden")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss()
            return
        if event.button.id != "launch":
            return
        self._launch()

    def _launch(self) -> None:
        rule_name = self.query_one("#name-input", Input).value.strip().upper()
        if not rule_name:
            self.app.notify("Le nom de la regle ne peut pas etre vide.", severity="warning")
            return
        description = self.query_one("#description-input", Input).value.strip()

        backend_choice = str(self.query_one("#backend-select", Select).value)
        target_backends = (
            list(self._available_backends) if backend_choice == _ALL_BACKENDS else [backend_choice]
        )

        rule_action = str(self.query_one("#action-select", Select).value)
        rule_chain = str(self.query_one("#chain-select", Select).value)
        protocol = str(self.query_one("#protocol-select", Select).value)

        src_raw = self.query_one("#src-input", Input).value.strip()
        src_ip = None
        if src_raw:
            try:
                ipaddress.ip_network(src_raw, strict=False)
                src_ip = src_raw
            except ValueError:
                self.app.notify("Adresse IP/subnet source invalide.", severity="warning")
                return

        dst_raw = self.query_one("#dst-input", Input).value.strip()
        dst_ip = None
        if dst_raw:
            try:
                ipaddress.ip_network(dst_raw, strict=False)
                dst_ip = dst_raw
            except ValueError:
                self.app.notify("Adresse IP/subnet destination invalide.", severity="warning")
                return

        dst_port = None
        if protocol in ("tcp", "udp"):
            port_raw = self.query_one("#port-input", Input).value.strip()
            if port_raw:
                if port_raw.isdigit() and 1 <= int(port_raw) <= 65535:
                    dst_port = int(port_raw)
                else:
                    self.app.notify("Le port doit etre un entier valide entre 1 et 65535.", severity="warning")
                    return

        iface_choice = str(self.query_one("#iface-select", Select).value)
        if iface_choice == _IFACE_ANY:
            iface = None
        elif iface_choice == _IFACE_MANUAL:
            iface = self.query_one("#iface-manual-input", Input).value.strip() or None
        else:
            iface = iface_choice

        summary = (
            f"Nom : {rule_name}\nBackend(s) : {', '.join(target_backends)}\n"
            f"Action : {rule_action} | Chaine : {rule_chain} | Protocole : {protocol.upper()}\n"
            f"Source : {src_ip or 'ANY'} | Destination : {dst_ip or 'ANY'} | Port : {dst_port or 'ANY'}\n"
            f"Interface : {iface or 'ANY'}"
        )
        self.app.push_screen(
            ConfirmScreen(title="CONFIRMER LA CREATION", message=summary),
            lambda confirmed: self._create_if_confirmed(
                confirmed, rule_name, description, target_backends, rule_action,
                rule_chain, protocol, src_ip, dst_ip, dst_port, iface,
            ),
        )

    def _create_if_confirmed(
        self, confirmed: bool | None, rule_name: str, description: str, target_backends: list[str],
        rule_action: str, rule_chain: str, protocol: str, src_ip: str | None, dst_ip: str | None,
        dst_port: int | None, iface: str | None,
    ) -> None:
        if not confirmed:
            return

        request = CreateRuleAllBackendsRequest(
            name=rule_name, action=rule_action, chain=rule_chain, protocol=protocol,
            source_cidr=src_ip, dest_cidr=dst_ip, dst_port=dst_port, interface=iface,
            description=description, target_backends=target_backends,
        )
        adapters: dict[str, object] = {}
        for name in target_backends:
            try:
                adapters[name] = self._container.get_firewall_port(name)
            except Exception:
                adapters[name] = None

        result = CreateRuleToAllBackendsCommand(self._container.rule_repository, adapters).execute(request)

        app_logger = getattr(self._container, "app_logger", None)
        for outcome in result.outcomes:
            if app_logger:
                app_logger.info(
                    f"Regle '{rule_name}' ({rule_action} {protocol}/{dst_port or 'ANY'}) "
                    f"creee sur {outcome.backend} (appliquee: {outcome.applied})."
                )
            severity = "information" if (outcome.success and outcome.applied) else ("warning" if outcome.success else "error")
            self.app.notify(outcome.message, title=outcome.backend, severity=severity)

        log_action_result(self._container, _ACTION_TITLE, status="success" if result.outcomes else "failure")
        self.dismiss()
