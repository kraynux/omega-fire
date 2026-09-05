# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 2.9 — Vider (Flush) la liste des IP bannies. Patron #2 + une
confirmation destructive (patron #1). Logique identique a
interfaces/cli/actions.py::action_2_9_flush_backends : collecte l'union
des IPs bannies sur les backends cibles, puis debannit tout via
UnbanIpToAllBackendsCommand."""
from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Select, Static

from omega_fire.application.commands.unban_ip_all_backends import (
    UnbanIpAllBackendsRequest,
    UnbanIpToAllBackendsCommand,
)
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.screens.confirm import ConfirmScreen
from omega_fire.interfaces.tui.support.action_audit import log_action_result

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ACTION_TITLE = "2.9 Vider les IP bannies"
_ALL_BACKENDS = "__all__"
_BACKEND_CANDIDATES = ("nftables", "iptables", "ip6tables", "fail2ban")


class FlushBackendsScreen(OmegaScreen):
    """Debannissement global (flush) sur un ou tous les backends."""

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
            yield Static("VIDER LES IP BANNIES", classes="omega-title")
            yield Static(
                "Attention : debannit TOUTES les IPs sur le(s) backend(s) choisi(s). "
                "Vos regles de filtrage principales (ports autorises, acces SSH, etc.) restent intactes.",
                classes="omega-hint",
            )
            if self._supported_backends:
                yield Static("Backend(s) cible(s)", classes="omega-subtitle")
                options = [("Tous les backends (recommande)", _ALL_BACKENDS)] + [
                    (f"Uniquement {name} (diagnostic)", name) for name in self._supported_backends
                ]
                yield Select(options, value=_ALL_BACKENDS, id="backend-select")
            else:
                yield Static("Aucun backend disponible pour le flush.", classes="omega-hint")

            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button("Vider", id="launch", variant="error")
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
            self.app.notify("Aucun backend disponible pour le flush.", severity="error")
            return

        choice = str(self.query_one("#backend-select", Select).value)
        target_backends = (
            list(self._supported_backends) if choice == _ALL_BACKENDS else [choice]
        )
        self.app.push_screen(
            ConfirmScreen(
                title="CONFIRMER LE VIDAGE",
                message=f"Debannir TOUTES les IPs sur : {', '.join(target_backends)} ?",
            ),
            lambda confirmed: self._flush_if_confirmed(confirmed, target_backends),
        )

    def _flush_if_confirmed(self, confirmed: bool | None, target_backends: list[str]) -> None:
        if not confirmed:
            return

        adapters: dict[str, object] = {}
        for name in target_backends:
            try:
                adapters[name] = self._container.get_firewall_port(name)
            except Exception:
                adapters[name] = None

        all_banned_ips: set[str] = set()
        for name in target_backends:
            adapter = adapters.get(name)
            if adapter is None:
                continue
            try:
                raw_bans = []
                if hasattr(adapter, "list_bans"):
                    raw_bans = adapter.list_bans()
                elif hasattr(adapter, "list_banned_ips"):
                    raw_bans = adapter.list_banned_ips()
                for item in raw_bans:
                    ip = item.get("ip") if isinstance(item, dict) else getattr(item, "ip", None)
                    if ip:
                        all_banned_ips.add(str(ip).split("/")[0].strip())
            except Exception:
                continue

        if not all_banned_ips:
            self.app.notify("Aucune IP bannie trouvee sur les backends cibles.")
            self.dismiss()
            return

        ban_repository = getattr(self._container, "ban_repository", None)
        result = UnbanIpToAllBackendsCommand(adapters, ban_repository).execute(
            UnbanIpAllBackendsRequest(ips=sorted(all_banned_ips), target_backends=target_backends)
        )

        flushed_count = 0
        for backend, outcome in result.outcomes.items():
            if outcome.unbanned:
                self.app.notify(f"{len(outcome.unbanned)} IP(s) debannie(s).", title=backend, severity="information")
                flushed_count += 1
            elif outcome.already_free and not outcome.errors:
                self.app.notify("Aucune IP a debannir (deja vide).", title=backend, severity="information")
                flushed_count += 1
            for failed_ip, reason in outcome.errors:
                self.app.notify(f"Echec pour {failed_ip} : {reason}", title=backend, severity="error")

        if flushed_count > 0:
            self.app.notify(f"Purge effectuee sur {flushed_count}/{len(target_backends)} backend(s).")
        else:
            self.app.notify("Echec : aucun backend n'a ete vide.", severity="error")

        log_action_result(self._container, _ACTION_TITLE, status="success" if flushed_count else "failure")
        self.dismiss()
