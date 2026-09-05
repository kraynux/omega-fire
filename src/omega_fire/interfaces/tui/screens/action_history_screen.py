# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 7.3 — Historique des actions (audit), pagine. Meme source de
donnees qu'action_7_3_action_history (ReadAuditHistoryQuery, limite de
lecture 500), meme filtre par mot-cle — DataTable + Input remplacent la
boucle de saisie sequentielle du CLI. Taille de page calculee sur la
hauteur reelle du tableau (retour utilisateur reel : une page fixe de 12
laissait la moitie de l'ecran vide en plein ecran) plutot qu'une valeur
en dur, meme technique que logs_live.py::visible_rows() cote CLI. La
gestion/purge (4 modes) est un sous-ecran dedie (purge_audit_history_screen.py,
patron #3), pousse depuis le bouton 'Gerer/Purger' comme PinnedPathsScreen
l'est ailleurs, avec rafraichissement au retour."""
from __future__ import annotations

from typing import TYPE_CHECKING

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, DataTable, Footer, Header, Input, Static

from omega_fire.application.queries.read_audit_history import (
    ReadAuditHistoryQuery,
    ReadAuditHistoryRequest,
)
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.screens.purge_audit_history_screen import PurgeAuditHistoryScreen

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ACTION_TITLE = "7.3 Historique des actions (audit)"
_MIN_PAGE_SIZE = 8


class ActionHistoryScreen(OmegaScreen):
    """7.3 — journal d'audit pagine, filtrable, avec gestion/purge."""

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container
        self._keyword = ""
        self._page = 0

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="omega-panel"):
            yield Static("HISTORIQUE DES ACTIONS", classes="omega-title")
            yield Input(placeholder="Filtrer par mot-cle (vide = aucun filtre)", id="filter-input")
            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button("Filtrer", id="filter")
                with Container(classes="omega-btn-frame"):
                    yield Button("Gerer / Purger", id="manage", variant="error")
                with Container(classes="omega-btn-frame"):
                    yield Button("Retour", id="back")

            yield DataTable(id="history-table")
            yield Static("", id="page-hint", classes="omega-hint")

            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button("< Page precedente", id="prev")
                with Container(classes="omega-btn-frame"):
                    yield Button("Page suivante >", id="next")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#history-table", DataTable).add_columns("Heure", "Action", "Acteur", "Resultat", "Details")
        # call_after_refresh (pas un appel direct) : tant que la mise en
        # page initiale n'a pas eu lieu, `#history-table`.size.height
        # renvoie une valeur provisoire trop petite (avant que le CSS
        # `height: 1fr` soit resolu) — _page_size() calculerait une page
        # bien plus petite que l'espace reellement disponible.
        self.call_after_refresh(self._refresh)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "back":
            self.dismiss()
            return
        if button_id == "filter":
            self._keyword = self.query_one("#filter-input", Input).value.strip()
            self._page = 0
            self._refresh()
            return
        if button_id == "manage":
            self.app.push_screen(PurgeAuditHistoryScreen(container=self._container), self._on_purge_closed)
            return
        if button_id == "prev":
            if self._page > 0:
                self._page -= 1
                self._refresh()
            return
        if button_id == "next":
            self._page += 1
            self._refresh()

    def _on_purge_closed(self, _result: None) -> None:
        self._page = 0
        self._refresh()

    def _colors(self) -> dict[str, str]:
        v = self.app.get_css_variables()
        return {"available": v.get("status-available", ""), "danger": v.get("error", "")}

    def _page_size(self) -> int:
        table = self.query_one("#history-table", DataTable)
        # Hauteur du tableau moins l'en-tete de colonnes (1 ligne) ;
        # repli sur une valeur minimale tant que la mise en page n'a pas
        # encore attribue de taille reelle au widget (premier appel).
        return max(_MIN_PAGE_SIZE, (table.size.height or 0) - 1)

    def _refresh(self) -> None:
        colors = self._colors()
        try:
            audit_port = self._container.get_audit_port()
        except Exception as e:
            self.query_one("#page-hint", Static).update(f"Registre d'audit indisponible : {e}")
            return

        result = ReadAuditHistoryQuery(audit_port).execute(
            ReadAuditHistoryRequest(limit=500, keyword=self._keyword)
        )
        table = self.query_one("#history-table", DataTable)
        table.clear()

        if not result.success:
            self.query_one("#page-hint", Static).update(result.message)
            return

        entries = result.entries
        if not entries:
            filter_suffix = f" (filtre : '{self._keyword}')" if self._keyword else ""
            self.query_one("#page-hint", Static).update(f"Aucune entree d'audit trouvee.{filter_suffix}")
            self._update_nav_buttons(page=0, total_pages=0)
            return

        page_size = self._page_size()
        total_pages = (len(entries) + page_size - 1) // page_size
        self._page = max(0, min(self._page, total_pages - 1))
        start_idx = self._page * page_size
        page_entries = entries[start_idx:start_idx + page_size]

        for entry in page_entries:
            badge = Text("OK", style=colors["available"]) if entry.success else Text("ECHEC", style=colors["danger"])
            parts = []
            if entry.target and entry.target != "N/A":
                parts.append(f"cible: {entry.target}")
            if entry.error_message:
                parts.append(f"erreur: {entry.error_message}")
            details = " | ".join(parts) if parts else "-"
            table.add_row(
                entry.timestamp.strftime("%d/%m %H:%M:%S"),
                entry.action,
                entry.actor,
                badge,
                details,
            )

        filter_label = f" — Filtre : '{self._keyword}'" if self._keyword else ""
        self.query_one("#page-hint", Static).update(
            f"Page {self._page + 1}/{total_pages}{filter_label}  │  "
            f"{len(entries)} entree(s) au total (limite de lecture : 500)."
        )
        self._update_nav_buttons(page=self._page, total_pages=total_pages)

    def _update_nav_buttons(self, *, page: int, total_pages: int) -> None:
        self.query_one("#prev", Button).disabled = page <= 0
        self.query_one("#next", Button).disabled = page >= total_pages - 1
