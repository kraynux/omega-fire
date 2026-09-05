# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 7.2 — Restaurer un etat (liste principale). Patron #4 (liste +
CRUD) : DataTable des snapshots, selection de ligne -> ecran de detail
(SnapshotDetailScreen). Textual defile nativement, la pagination
manuelle par page de 8 du CLI n'est pas necessaire ici. Logique
identique a la boucle principale de
interfaces/cli/actions.py::action_7_2_restore_state."""
from __future__ import annotations

from typing import TYPE_CHECKING

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, DataTable, Footer, Header, Static

from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.screens.snapshot_detail_screen import SnapshotDetailScreen

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ORIGIN_LABELS = {"auto_preset": "AUTO-PROFIL", "manual": "MANUEL"}


class RestoreStateScreen(OmegaScreen):
    """Liste des snapshots d'etat disponibles pour restauration."""

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container
        self._snapshots_by_id: dict[str, object] = {}

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="omega-panel"):
            yield Static("RESTAURER UN ETAT", classes="omega-title")
            yield Static("", id="result-hint", classes="omega-hint")
            yield DataTable(id="snapshots-table")
            with Horizontal(classes="omega-actions"), Container(classes="omega-btn-frame"):
                yield Button("Retour", id="back")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#snapshots-table", DataTable)
        table.cursor_type = "row"
        table.add_columns("Date", "Origine", "Description", "Regles", "IPs", "Jails")
        self._refresh()

    def _refresh(self) -> None:
        table = self.query_one("#snapshots-table", DataTable)
        table.clear()
        hint = self.query_one("#result-hint", Static)
        self._snapshots_by_id = {}

        try:
            persistence_port = self._container.get_persistence_port()
            snapshots = persistence_port.list_snapshots()
        except Exception as e:
            hint.update(f"Impossible de lister les snapshots : {e}")
            return

        if not snapshots:
            hint.update("Aucun snapshot disponible. Utilisez d'abord le menu 7.1.")
            return

        hint.update(f"{len(snapshots)} snapshot(s) — selectionnez une ligne pour agir dessus.")
        for snap in snapshots:
            self._snapshots_by_id[snap.id] = snap
            origin = Text(_ORIGIN_LABELS.get(snap.origin, (snap.origin or "?").upper()))
            table.add_row(
                snap.created_at.strftime("%d/%m %H:%M"), origin, snap.description or "(aucune)",
                str(snap.rules_count), str(snap.blacklist_count), str(snap.jails_count),
                key=snap.id,
            )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        snapshot = self._snapshots_by_id.get(str(event.row_key.value))
        if snapshot is None:
            return
        self.app.push_screen(
            SnapshotDetailScreen(container=self._container, snapshot=snapshot),
            lambda _result: self._refresh(),
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss()
