# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Tableau des fichiers epingles (blocklist_analysis_pinned_paths.json,
meme store que les 8 sites corriges en Phase 0 — 5.2/5.3/5.4/6.1/2.2/2.4/
2.8/4.3). Adapte du patron widgets/targets_table.py d'omega-check (D-008)."""
from __future__ import annotations

from textual.widgets import DataTable


class PinnedPathsTable(DataTable[str]):
    """Une ligne par chemin epingle."""

    def on_mount(self) -> None:
        self.cursor_type = "row"
        self.add_columns("Chemin epingle")

    def set_paths(self, paths: list[str]) -> None:
        self.clear()
        for path in paths:
            self.add_row(path, key=path)
