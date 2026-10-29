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
from omega_fire.shared.i18n import _

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer


class SearchDiagnosticsScreen(OmegaScreen):
    """Recherche par mot-cle dans le registre de capacites."""

    # Retour utilisateur 2026-10-28 : le tableau des resultats, en pleine largeur (motifs
    # longs), annulait le centrage du formulaire — tout collait a gauche. Formulaire dans son
    # propre bloc centre, tableau en dessous sur toute la largeur.
    CSS = """
    SearchDiagnosticsScreen #search-form {
        width: 100%;
        height: auto;
        align-horizontal: center;
    }

    SearchDiagnosticsScreen #search-form > Input {
        width: 70;
        margin-bottom: 1;
    }

    SearchDiagnosticsScreen #search-form > .omega-actions {
        width: 70;
        align: center middle;
    }
    """

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="omega-form-panel"):
            with Vertical(id="search-form"):
                yield Static(_("RECHERCHER DANS LES DIAGNOSTICS"), classes="omega-title")
                yield Input(placeholder=_("Mot-clé (id, raison ou détails techniques)"), id="query-input")
                with Horizontal(classes="omega-actions"):
                    with Container(classes="omega-btn-frame"):
                        yield Button(_("Rechercher"), id="search", variant="primary")
                    with Container(classes="omega-btn-frame"):
                        yield Button(_("Retour"), id="back")
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
            hint.update(_("Aucun diagnostic ou composant ne correspond à '{keyword}'.").format(keyword=keyword) if keyword else _("Aucun diagnostic."))
        else:
            hint.update(_("{count} résultat(s) pour '{keyword}'.").format(count=len(capabilities), keyword=keyword) if keyword else _("{count} capacité(s).").format(count=len(capabilities)))
