# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 1.6 — Rechercher dans les diagnostics par mot-cle (id, raison ou
details techniques d'une capacite). Meme filtre que
interfaces/cli/renderers/capability_view.py::search_diagnostics().

Note portee au passage (pas corrigee ici, hors perimetre d'un portage
UI) : la branche "recherche dans le journal applicatif" de
action_1_6_search_diagnostics (CLI) est deja morte cote CLI —
`read_app_log()` renvoie une chaine formattee (`str`), pas un objet a
attribut `.entries`/`.logs` ni une liste, donc `raw_entries` reste
toujours vide quel que soit le contenu reel du journal. Cet ecran ne
porte donc que la partie recherche-capacites, la seule qui fonctionne
reellement aujourd'hui."""
from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Input, Static

from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.widgets.capabilities_table import CapabilitiesTable

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer


class SearchDiagnosticsScreen(OmegaScreen):
    """Recherche par mot-cle dans le registre de capacites."""

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="omega-form-panel"):
            yield Static("RECHERCHER DANS LES DIAGNOSTICS", classes="omega-title")
            yield Input(placeholder="Mot-cle (id, raison ou details techniques)", id="query-input")
            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button("Rechercher", id="search", variant="primary")
                with Container(classes="omega-btn-frame"):
                    yield Button("Retour", id="back")
            yield Static("", id="result-hint", classes="omega-hint")
            yield CapabilitiesTable(id="capabilities-table")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss()
            return
        if event.button.id != "search":
            return
        self._run_search()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "query-input":
            self._run_search()

    def _run_search(self) -> None:
        keyword = self.query_one("#query-input", Input).value.strip().lower()
        capabilities = self._container.capability_registry.list_all()
        if keyword:
            capabilities = [
                cap for cap in capabilities
                if keyword in cap.id.lower()
                or keyword in (cap.reason or "").lower()
                or keyword in str(getattr(cap, "detail", "") or "").lower()
            ]

        table = self.query_one(CapabilitiesTable)
        table.set_capabilities(capabilities)

        hint = self.query_one("#result-hint", Static)
        if not capabilities:
            hint.update(f"Aucun diagnostic ou composant ne correspond a '{keyword}'." if keyword else "Aucun diagnostic.")
        else:
            hint.update(f"{len(capabilities)} resultat(s) pour '{keyword}'." if keyword else f"{len(capabilities)} capacite(s).")
