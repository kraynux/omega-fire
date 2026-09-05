# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 4.1 — Analyse et Etat des jails. Patron #4 (liste + selection) :
tableau des jails, la selection d'une ligne affiche ses IPs bannies ;
un champ de recherche verifie si une IP donnee est presente dans un
jail. Logique identique a interfaces/cli/actions.py::action_4_1_jails_status
(sans le sous-menu clavier a 3 options — remplace par l'interaction
directe tableau + recherche, plus adaptee a une interface pointer/
clavier Textual).

La recuperation (get_jail_status -> fail2ban-client, jusqu'a 10s de
timeout si le service est present mais inactif) se fait en arriere-plan
(run_blocking, voir _base.py) plutot qu'a la construction de l'ecran :
la faire de facon synchrone dans __init__/compose() gelait TOUTE l'app
au clic sur 4.1 des que Fail2ban ne repondait pas immediatement (retour
utilisateur reel, mode degrade)."""
from __future__ import annotations

import ipaddress
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, DataTable, Footer, Header, Input, Static

from omega_fire.application.queries.jail_status import JailStatusResult, get_jail_status
from omega_fire.interfaces.tui.screens._base import OmegaScreen

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer


class JailsStatusScreen(OmegaScreen):
    """Vue d'ensemble des jails Fail2ban et de leurs IPs bannies."""

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container
        self._result: JailStatusResult | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="omega-panel"):
            yield Static("ANALYSE ET ETAT DES JAILS", classes="omega-title")
            yield Static("Chargement de l'etat des jails...", id="status-hint", classes="omega-hint")

            yield DataTable(id="jails-table", classes="omega-hidden")
            yield Static(
                "Selectionnez une ligne pour voir les IPs bannies de ce jail.",
                id="ips-hint", classes="omega-hint omega-hidden",
            )

            yield Static("Rechercher une IP dans tous les jails", id="search-title", classes="omega-subtitle omega-hidden")
            yield Input(placeholder="ex. 192.168.1.10", id="search-input", classes="omega-hidden")
            with Horizontal(classes="omega-actions omega-hidden", id="search-row"):
                with Container(classes="omega-btn-frame"):
                    yield Button("Rechercher", id="search")
            with Horizontal(classes="omega-actions"), Container(classes="omega-btn-frame"):
                yield Button("Retour", id="back")
        yield Footer()

    def on_mount(self) -> None:
        def _fetch() -> JailStatusResult:
            try:
                fail2ban_port = self._container.get_fail2ban_port()
            except Exception:
                fail2ban_port = None
            return get_jail_status(fail2ban_port=fail2ban_port)

        self.run_blocking(_fetch, self._on_loaded, busy_message="Chargement de l'etat des jails...")

    def _on_loaded(self, result: JailStatusResult) -> None:
        self._result = result
        hint = self.query_one("#status-hint", Static)

        if not result.jails:
            hint.update(result.message or "Impossible de communiquer avec le service Fail2ban.")
            return

        hint.set_class(True, "omega-hidden")

        table = self.query_one("#jails-table", DataTable)
        table.set_class(False, "omega-hidden")
        table.cursor_type = "row"
        table.add_columns("Nom", "Statut", "Bannis", "Filtre", "Log Path", "Max Retry", "Ban Time")
        for jail in result.jails:
            status = "Actif" if jail.active else "Inactif"
            table.add_row(
                jail.name, status, str(jail.banned_count), jail.filter or "N/A",
                jail.log_path or "N/A", str(jail.max_retry), f"{jail.ban_time}s",
                key=jail.name,
            )

        self.query_one("#ips-hint", Static).set_class(False, "omega-hidden")
        self.query_one("#search-title", Static).set_class(False, "omega-hidden")
        self.query_one("#search-input", Input).set_class(False, "omega-hidden")
        self.query_one("#search-row").set_class(False, "omega-hidden")

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if self._result is None:
            return
        jail_name = str(event.row_key.value)
        jail = next((j for j in self._result.jails if j.name == jail_name), None)
        hint = self.query_one("#ips-hint", Static)
        if jail is None:
            return
        ips = [str(ip) for ip in jail.banned_ips]
        if not ips:
            hint.update(f"Aucune IP actuellement bannie dans '{jail_name}'.")
        else:
            hint.update(f"IP(s) bannie(s) dans '{jail_name}' ({len(ips)}) : " + ", ".join(ips))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss()
            return
        if event.button.id != "search" or self._result is None:
            return

        target_ip = self.query_one("#search-input", Input).value.strip()
        if not target_ip:
            self.app.notify("Saisissez une adresse IP.", severity="warning")
            return
        try:
            ipaddress.ip_address(target_ip)
        except ValueError:
            self.app.notify("Format d'adresse IP invalide.", severity="warning")
            return

        found_in = [
            jail.name for jail in self._result.jails
            if any(str(ip) == target_ip for ip in jail.banned_ips)
        ]
        hint = self.query_one("#ips-hint", Static)
        if found_in:
            hint.update(f"{target_ip} trouvee dans {len(found_in)} jail(s) : {', '.join(found_in)} — utilisez 4.2 pour la retirer.")
        else:
            hint.update(f"{target_ip} n'a ete trouvee dans aucun jail actif.")
