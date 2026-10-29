# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Retour utilisateur 2026-10-28 : les 11 modeles de jail livres (4.4 → Gérer les modeles)
n'apparaissaient pas, donc impossibles a retirer — le `DataTable { height: 1fr }` commun
ecrasait le tableau a une ligne (l'en-tete) dans une zone qui defile. Meme defaut trouve
par balayage sur la gestion des fichiers blocklist (et 4 autres ecrans, regle CSS commune).
Les feuilles de style reelles sont chargees : c'est la mise en page qui est testee."""
from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from omega_lib.terminal.models import RenderProfile
from textual.widgets import DataTable

from omega_fire.interfaces.tui.rendering.stylesheet_loader import load_paths_for
from omega_fire.interfaces.tui.screens import blocklist_files_screen, jail_presets_screen
from omega_fire.interfaces.tui.screens.blocklist_files_screen import BlocklistFilesScreen
from omega_fire.interfaces.tui.screens.jail_presets_screen import JailPresetsScreen

from .i18n_helpers import FakeContainer, HostApp, MemorySettings


class _StyledHost(HostApp):
    CSS_PATH = load_paths_for(RenderProfile.COMPLETE)


def _heights(screen_factory, size=(110, 34)) -> list[tuple[str, int, int]]:
    async def run() -> list[tuple[str, int, int]]:
        app = _StyledHost(screen_factory())
        async with app.run_test(size=size) as pilot:
            await pilot.pause()
            await pilot.pause()
            return [(t.id or "", t.row_count, t.region.height) for t in app.screen.query(DataTable)]
    return asyncio.run(run())


class TableHeightTest(unittest.TestCase):
    def test_modeles_de_jail_tous_visibles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(jail_presets_screen, "RUNTIME_DIR", Path(tmp)):
            container = FakeContainer(MemorySettings(), Path(tmp))
            (table_id, rows, height), = _heights(lambda: JailPresetsScreen(container=container))
        self.assertEqual(rows, 11)
        self.assertEqual(height, rows + 1, table_id)  # en-tete + chaque modele

    def test_fichiers_blocklist_tous_visibles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            blocklists = Path(tmp) / "blocklist"
            blocklists.mkdir()
            for name in ("a.txt", "b.txt", "c.txt"):
                (blocklists / name).write_text("10.0.0.1\n")
            with mock.patch.object(blocklist_files_screen, "BLOCKLIST_DIR", blocklists), \
                    mock.patch.object(blocklist_files_screen, "RUNTIME_DIR", Path(tmp) / "runtime"):
                container = FakeContainer(MemorySettings(), Path(tmp))
                tables = _heights(lambda: BlocklistFilesScreen(container=container))
        for table_id, rows, height in tables:
            self.assertGreater(rows, 0, table_id)
            self.assertEqual(height, rows + 1, table_id)


class FormCenteringTest(unittest.TestCase):
    """Retour utilisateur 2026-10-28 : 1.6 colle a gauche — un tableau de resultats en pleine
    largeur annulait le centrage du formulaire. Meme defaut sur 5.6 / 5.7 / 5.8 des que leur
    tableau apparaissait. Le titre ne doit pas bouger quand le tableau est rempli."""

    def test_titre_reste_centre_avec_le_tableau(self) -> None:
        from omega_fire.interfaces.tui.screens.purge_backups_screen import PurgeBackupsScreen
        from omega_fire.interfaces.tui.screens.restore_backup_screen import RestoreBackupScreen
        from omega_fire.interfaces.tui.screens.rotate_logs_screen import RotateLogsScreen
        from omega_fire.interfaces.tui.screens.search_diagnostics_screen import SearchDiagnosticsScreen

        async def run(cls, tmp: Path) -> tuple[int, int]:
            app = _StyledHost(cls(container=FakeContainer(MemorySettings(), tmp)))
            async with app.run_test(size=(120, 34)) as pilot:
                await pilot.pause()
                await pilot.pause()
                before = app.screen.query(".omega-title").first().region.x
                for table in app.screen.query(DataTable):
                    for node in table.ancestors_with_self:
                        if hasattr(node, "remove_class"):
                            node.remove_class("omega-hidden")
                    if not table.columns:
                        table.add_columns("a", "b")
                    for _row in range(3):
                        table.add_row(*["x" * 40] * len(table.columns))
                await pilot.pause()
                await pilot.pause()
                return before, app.screen.query(".omega-title").first().region.x

        for cls in (SearchDiagnosticsScreen, RotateLogsScreen, PurgeBackupsScreen, RestoreBackupScreen):
            with tempfile.TemporaryDirectory() as tmp:
                before, after = asyncio.run(run(cls, Path(tmp)))
            self.assertGreater(before, 10, cls.__name__)
            self.assertLessEqual(abs(after - before), 1, cls.__name__)


if __name__ == "__main__":
    unittest.main()
