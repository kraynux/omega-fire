# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 3.3 — Lister les regles de pare-feu detaillees. Synchronise
depuis les backends disponibles puis affiche le tableau complet, meme
logique que interfaces/cli/actions.py::action_3_3_list_rules. Colonne
Backend coloree via la palette d'extension omega-fire (backend-nftables/
iptables/fail2ban/conntrack, Phase 0)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, DataTable, Footer, Header, Static

from omega_fire.application.commands.sync_rules_from_backends import (
    SyncRulesFromBackendsCommand,
    SyncRulesRequest,
)
from omega_fire.application.queries.list_persisted_rules import ListPersistedRulesQuery
from omega_fire.domain.rules.ownership import rule_owner
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.shared.i18n import _

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_BACKEND_VARIABLE: dict[str, str] = {
    "nftables": "backend-nftables",
    "iptables": "backend-iptables",
    "ip6tables": "backend-iptables",
    "fail2ban": "backend-fail2ban",
    "conntrack": "backend-conntrack",
}


class ListRulesScreen(OmegaScreen):
    """Tableau global des regles (noyau + base de donnees)."""

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="omega-panel"):
            yield Static(_("LISTE DES RÈGLES"), classes="omega-title")
            yield Static("", id="sync-hint", classes="omega-hint")
            yield DataTable(id="rules-table")
            with Horizontal(classes="omega-actions"), Container(classes="omega-btn-frame"):
                yield Button(_("Retour"), id="back")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#rules-table", DataTable)
        table.add_columns(
            _("ID"), _("Backend"), _("Origine"), _("Nom / Description"), _("Chaîne"),
            _("Action"), _("Proto"), _("Port"), _("IP Source"), _("IP Dest."), _("État"),
        )

        hint = self.query_one("#sync-hint", Static)
        rule_repository = getattr(self._container, "rule_repository", None)
        if rule_repository is None:
            hint.update(_("Le conteneur ou le dépôt de règles n'est pas disponible."))
            return

        backends: dict[str, object] = {}
        for backend_name in ("nftables", "iptables", "ip6tables"):
            try:
                adapter = self._container.get_firewall_port(backend_name)
                if adapter is not None:
                    backends[backend_name] = adapter
            except Exception:
                continue

        if backends:
            sync_result = SyncRulesFromBackendsCommand(rule_repository).execute(
                SyncRulesRequest(backends=backends)
            )
            hint_text = sync_result.message
        else:
            hint_text = _("Aucun backend firewall disponible pour la synchronisation.")
        hint.update(hint_text)

        list_result = ListPersistedRulesQuery(rule_repository).execute()
        if not list_result.success:
            hint.update(list_result.message)
            return
        if not list_result.rules:
            hint.update(_("Aucune règle pare-feu enregistrée ou active sur le système."))
            return

        variables = self.app.get_css_variables()
        foreign_tools: dict[str, int] = {}
        for r in list_result.rules:
            chain_str = r.chain.value.upper() if hasattr(r.chain, "value") else str(r.chain or "INPUT").upper()
            action_str = r.action.value.upper() if hasattr(r.action, "value") else str(r.action or "ACCEPT").upper()
            proto_str = r.protocol.value.upper() if r.protocol and hasattr(r.protocol, "value") else "ALL"
            port_str = str(r.port_start) if r.port_start else "ANY"
            name_str = r.comment or _("Règle #{rule_id}").format(rule_id=r.rule_id)

            backend_color = variables.get(_BACKEND_VARIABLE.get(r.backend, ""), "")
            backend_cell = Text(r.backend, style=f"bold {backend_color}" if backend_color else "bold")

            error_color = variables.get("error", "")
            success_color = variables.get("success", "")
            warning_color = variables.get("warning", "")
            action_color = error_color if action_str in ("DROP", "REJECT") else success_color
            action_cell = Text(action_str, style=action_color)

            owner = rule_owner(r)
            if owner:
                foreign_tools[owner] = foreign_tools.get(owner, 0) + 1
            origin_cell = (
                Text(owner, style=f"italic {warning_color}") if owner
                else Text("SYSTEME", style=warning_color) if r.origin == "imported"
                else Text("OMEGA", style=success_color)
            )
            status_cell = Text(_("ACTIF"), style=success_color) if r.enabled else Text(_("INACTIF"))

            table.add_row(
                str(r.rule_id), backend_cell, origin_cell, name_str, chain_str,
                action_cell, proto_str, port_str, r.source_cidr or "ANY",
                r.dest_cidr or "ANY", status_cell,
                key=str(r.rule_id),
            )

        if foreign_tools:
            hint.update(hint_text + "\n" + _(
                "{count} règle(s) d'autres outils ({tools}) : affichées pour information, "
                "Omega-Fire ne les modifie pas."
            ).format(
                count=sum(foreign_tools.values()),
                tools=", ".join(f"{tool} {n}" for tool, n in sorted(foreign_tools.items())),
            ))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss()
