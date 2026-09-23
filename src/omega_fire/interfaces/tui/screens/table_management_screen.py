# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 3.5 — Gestion des tables (retour utilisateur 2026-09-24, suite a
l'incident reel : perte totale de reseau apres application repetee de
profils, `nft flush ruleset` global necessaire pour recuperer l'acces
faute d'un equivalent controle dans Omega-Fire). Logique identique a
interfaces/cli/actions.py::action_3_5_table_management, meme 5 actions
(+ suppression complete de table en variante "avancee" du flush cible) :
diagnostic en lecture seule toujours affiche en premier
(application/commands/manage_tables.py::GetTablesStatusQuery), puis un
choix d'action (Select) qui revele/masque le choix de backend cible
(patron deja etabli par delete_rule_screen.py::on_select_changed)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, DataTable, Footer, Header, Select, Static

from omega_fire.application.commands.manage_tables import (
    DeleteTableCommand,
    FlushAllTablesSyncCommand,
    FlushBackendTableCommand,
    GetTablesStatusQuery,
    InitializeTablesCommand,
    ResetChainPoliciesCommand,
)
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.screens.confirm import ConfirmScreen
from omega_fire.interfaces.tui.support.action_audit import log_action_result

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ACTION_TITLE = "3.5 Gestion des tables"

_ACTION_INIT = "init"
_ACTION_RESET = "reset"
_ACTION_FLUSH_ONE = "flush_one"
_ACTION_FLUSH_ALL = "flush_all"
_ACTION_DELETE_TABLE = "delete_table"

# Actions qui ont besoin d'un backend cible explicite (Select revele) —
# init/flush_all agissent sur TOUS les backends detectes d'un coup,
# delete_table est nftables-only et n'a donc rien a choisir non plus.
_NEEDS_BACKEND_CHOICE = (_ACTION_RESET, _ACTION_FLUSH_ONE)


class TableManagementScreen(OmegaScreen):
    """Diagnostic + 5 actions de gestion des tables firewall."""

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container
        self._adapters: dict[str, object] = {}
        self._available_backends: list[str] = []
        self._detect_backends()

    def _detect_backends(self) -> None:
        for name in ("nftables", "iptables", "ip6tables"):
            try:
                self._adapters[name] = self._container.get_firewall_port(name)
            except Exception:
                self._adapters[name] = None
        self._available_backends = [n for n, a in self._adapters.items() if a is not None]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="omega-panel"):
            yield Static("GESTION DES TABLES", classes="omega-title")

            if not self._available_backends:
                yield Static(
                    "Aucun backend firewall disponible (nftables, iptables et ip6tables non détectés).",
                    classes="omega-hint",
                )
                with Horizontal(classes="omega-actions"), Container(classes="omega-btn-frame"):
                    yield Button("Retour", id="back")
                yield Footer()
                return

            yield DataTable(id="status-table")
            yield Static("", id="divergence-hint", classes="omega-hint")

            yield Static("Action", classes="omega-subtitle")
            action_options = [
                ("Initialiser les tables (nftables, première utilisation)", _ACTION_INIT),
                ("Réinitialiser les politiques à ACCEPT sur un backend", _ACTION_RESET),
                ("Vider un backend spécifique", _ACTION_FLUSH_ONE),
                ("Vider TOUS les backends détectés (synchronisé)", _ACTION_FLUSH_ALL),
                ("[AVANCÉ] Supprimer complètement la table nftables", _ACTION_DELETE_TABLE),
            ]
            yield Select(action_options, value=_ACTION_INIT, id="action-select", allow_blank=False)

            yield Static("Backend cible", id="backend-label", classes="omega-subtitle omega-hidden")
            backend_options = [(name, name) for name in self._available_backends]
            yield Select(
                backend_options,
                value=self._available_backends[0],
                id="backend-select",
                classes="omega-hidden",
                allow_blank=False,
            )

            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button("Exécuter", id="launch", variant="error")
                with Container(classes="omega-btn-frame"):
                    yield Button("Rafraîchir", id="refresh")
                with Container(classes="omega-btn-frame"):
                    yield Button("Retour", id="back")
        yield Footer()

    def on_mount(self) -> None:
        if not self._available_backends:
            return
        table = self.query_one("#status-table", DataTable)
        table.add_columns("Backend", "Table", "INPUT", "OUTPUT", "FORWARD", "Règles")
        self._refresh_status()

    def _policy_cell(self, policies: dict, chain: str) -> Text:
        policy = policies.get(chain) or policies.get(chain.upper())
        if policy is None:
            return Text("—", style="dim")
        return Text(policy.upper(), style="green" if policy.lower() == "accept" else "red")

    def _refresh_status(self) -> None:
        table = self.query_one("#status-table", DataTable)
        table.clear()
        result = GetTablesStatusQuery(self._adapters).execute()
        for entry in result.entries:
            if not entry.available:
                table.add_row(entry.backend, "—", "—", "—", "—", "—")
                continue
            if entry.error:
                table.add_row(entry.backend, Text(f"erreur : {entry.error}", style="red"), "—", "—", "—", "—")
                continue
            table_cell = Text("présente", style="green") if entry.table_exists else Text("absente", style="yellow")
            table.add_row(
                entry.backend, table_cell,
                self._policy_cell(entry.policies, "input"),
                self._policy_cell(entry.policies, "output"),
                self._policy_cell(entry.policies, "forward"),
                str(entry.rule_count),
            )

        hint = self.query_one("#divergence-hint", Static)
        if result.policy_divergences:
            hint.update(
                Text("Divergence(s) de politique entre backends : " + " ; ".join(result.policy_divergences), style="yellow")
            )
        else:
            hint.update("")

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id != "action-select":
            return
        needs_backend = str(event.value) in _NEEDS_BACKEND_CHOICE
        self.query_one("#backend-label", Static).set_class(not needs_backend, "omega-hidden")
        self.query_one("#backend-select", Select).set_class(not needs_backend, "omega-hidden")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss()
            return
        if event.button.id == "refresh":
            self._refresh_status()
            return
        if event.button.id != "launch" or not self._available_backends:
            return

        action = str(self.query_one("#action-select", Select).value)

        if action == _ACTION_INIT:
            if self._adapters.get("nftables") is None:
                self.app.notify("nftables n'est pas disponible — rien à initialiser.", severity="error")
                return
            self._run(lambda: InitializeTablesCommand(self._adapters["nftables"]).execute())
            return

        if action == _ACTION_DELETE_TABLE:
            if self._adapters.get("nftables") is None:
                self.app.notify("nftables n'est pas disponible — rien à supprimer.", severity="error")
                return
            self.app.push_screen(
                ConfirmScreen(
                    title="[AVANCÉ] SUPPRIMER LA TABLE",
                    message=(
                        "Supprime la table nftables ENTIÈRE (chaînes et hooks compris, pas "
                        "seulement les règles). Plus aucun filtrage actif sur ce backend tant "
                        "qu'elle n'est pas réinitialisée ensuite. Continuer ?"
                    ),
                ),
                lambda confirmed: self._run_if_confirmed(
                    confirmed, lambda: DeleteTableCommand(self._adapters["nftables"]).execute()
                ),
            )
            return

        if action == _ACTION_FLUSH_ALL:
            self.app.push_screen(
                ConfirmScreen(
                    title="CONFIRMER LE VIDAGE GLOBAL",
                    message=(
                        f"Va vider TOUTES les règles sur TOUS les backends détectés "
                        f"({', '.join(self._available_backends)}). Continuer ?"
                    ),
                ),
                lambda confirmed: self._run_if_confirmed(
                    confirmed, lambda: FlushAllTablesSyncCommand(self._adapters).execute()
                ),
            )
            return

        # RESET / FLUSH_ONE : besoin du backend choisi
        backend = str(self.query_one("#backend-select", Select).value)
        adapter = self._adapters.get(backend)
        if adapter is None:
            self.app.notify(f"{backend} n'est pas disponible.", severity="error")
            return

        if action == _ACTION_RESET:
            self.app.push_screen(
                ConfirmScreen(
                    title="CONFIRMER LA RÉINITIALISATION",
                    message=f"Remettre input/output/forward à ACCEPT sur {backend} ?",
                ),
                lambda confirmed: self._run_if_confirmed(
                    confirmed, lambda: ResetChainPoliciesCommand(adapter, backend).execute()
                ),
            )
            return

        if action == _ACTION_FLUSH_ONE:
            self.app.push_screen(
                ConfirmScreen(
                    title="CONFIRMER LE VIDAGE",
                    message=f"Vider (flush) toutes les règles de {backend} ?",
                ),
                lambda confirmed: self._run_if_confirmed(
                    confirmed, lambda: FlushBackendTableCommand(adapter, backend).execute()
                ),
            )
            return

    def _run_if_confirmed(self, confirmed: bool | None, execute) -> None:
        if not confirmed:
            return
        self._run(execute)

    def _run(self, execute) -> None:
        result = execute()
        self.app.notify(result.message, severity="information" if result.success else "error")
        log_action_result(self._container, _ACTION_TITLE, status="success" if result.success else "failure")
        self._refresh_status()


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Equivalent TUI de interfaces/cli/actions.py::action_3_5_table_management —
#   diagnostic (GetTablesStatusQuery) toujours affiché, puis 5 actions
#   (application/commands/manage_tables.py, retour utilisateur 2026-09-24).
#
# Pourquoi dans interfaces/tui/ (charte) :
# - Aucune logique metier ici — délègue entièrement aux commandes de
#   application/commands/manage_tables.py, comme tous les autres écrans.
#
# Points clés :
# - _NEEDS_BACKEND_CHOICE : seules "reset" et "flush_one" ont besoin d'un
#   Select backend explicite — "init"/"flush_all"/"delete_table" agissent
#   soit sur nftables uniquement (init/delete_table), soit sur tous les
#   backends détectés d'un coup (flush_all), jamais un choix à faire.
# - init et delete_table sont nftables-only (voir manage_tables.py) —
#   grisés via message d'erreur direct si nftables absent, jamais un
#   Select vide.
#---------------------------------------------------------------------->
