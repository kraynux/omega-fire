# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 2.5 — Lister les IPs bannies, filtrable par backend. Logique
identique a interfaces/cli/actions.py::action_2_5_list_banned. Colonne
Backend coloree via la palette d'extension omega-fire (Phase 0)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, DataTable, Footer, Header, Select, Static

from omega_fire.interfaces.tui.screens._base import OmegaScreen

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ALL_BACKENDS = "__all__"
_BACKEND_VARIABLE: dict[str, str] = {
    "nftables": "backend-nftables",
    "iptables": "backend-iptables",
    "ip6tables": "backend-iptables",
    "fail2ban": "backend-fail2ban",
}


class ListBannedIpsScreen(OmegaScreen):
    """Liste des IPs bannies, agregee ou filtree par backend."""

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container
        self._supported_backends = self._detect_supported_backends()

    def _detect_supported_backends(self) -> list[str]:
        supported = ["nftables", "iptables", "ip6tables"]
        try:
            if self._container.get_firewall_port("fail2ban") is not None:
                supported.append("fail2ban")
        except Exception:
            pass
        return supported

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="omega-panel"):
            yield Static("IPs BANNIES", classes="omega-title")
            with Horizontal(classes="omega-actions"):
                options = [("Tous les backends", _ALL_BACKENDS)] + [
                    (name, name) for name in self._supported_backends
                ]
                yield Select(options, value=_ALL_BACKENDS, id="backend-select")
                with Container(classes="omega-btn-frame"):
                    yield Button("Filtrer", id="filter", variant="primary")
            yield Static("", id="result-hint", classes="omega-hint")
            yield DataTable(id="bans-table")
            with Horizontal(classes="omega-actions"), Container(classes="omega-btn-frame"):
                yield Button("Retour", id="back")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#bans-table", DataTable)
        table.add_columns("Adresse IP", "Backend", "Source / Commentaire")
        self._refresh(list(self._supported_backends))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss()
            return
        if event.button.id != "filter":
            return
        choice = str(self.query_one("#backend-select", Select).value)
        target = list(self._supported_backends) if choice == _ALL_BACKENDS else [choice]
        self._refresh(target)

    def _refresh(self, target_backends: list[str]) -> None:
        all_bans: list[dict] = []
        for b_name in target_backends:
            try:
                adapter = self._container.get_firewall_port(b_name)
                if not adapter:
                    continue
                bans = []
                if hasattr(adapter, "list_bans"):
                    bans = adapter.list_bans()
                elif hasattr(adapter, "list_banned_ips"):
                    bans = adapter.list_banned_ips()
                elif hasattr(adapter, "get_banned_ips"):
                    bans = adapter.get_banned_ips()

                for item in bans:
                    if isinstance(item, dict):
                        all_bans.append({"ip": item.get("ip", "Inconnu"), "backend": b_name,
                                          "comment": item.get("comment", "-") or item.get("source", "-")})
                    elif hasattr(item, "ip"):
                        all_bans.append({"ip": item.ip, "backend": b_name,
                                          "comment": getattr(item, "comment", "-") or "-"})
                    else:
                        all_bans.append({"ip": str(item), "backend": b_name, "comment": "-"})
            except Exception:
                continue

        table = self.query_one("#bans-table", DataTable)
        table.clear()
        hint = self.query_one("#result-hint", Static)
        if not all_bans:
            hint.update("Aucune IP bannie trouvee.")
            return
        hint.update(f"{len(all_bans)} IP(s) bannie(s).")

        variables = self.app.get_css_variables()
        for entry in all_bans:
            color = variables.get(_BACKEND_VARIABLE.get(entry["backend"], ""), "")
            backend_cell = Text(entry["backend"], style=f"bold {color}" if color else "bold")
            table.add_row(entry["ip"], backend_cell, entry["comment"])
