# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Dossiers d'exports et de captures (ecran Reglages, retour utilisateur 2026-10-27) : chemin
modifiable, vidage avec confirmation, garde-fous - omega-fire tourne en root."""
from __future__ import annotations

import asyncio
import os
import tempfile
import unittest
from pathlib import Path

from textual.widgets import Button, Input

from omega_fire.application.commands.clear_directory import check_clearable, clear_directory
from omega_fire.application.exceptions import UnsafeDirectoryError
from omega_fire.interfaces.tui.screens.confirm import ConfirmScreen
from omega_fire.interfaces.tui.screens.settings_screen import SettingsScreen

from .i18n_helpers import HostApp, MemorySettings, FakeContainer


class ClearDirectoryTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        self.project = self.base / "omega-fire"
        (self.project / "var").mkdir(parents=True)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_clears_content_keeps_folder_and_link_targets(self) -> None:
        target = self.base / "exports"
        (target / "sub").mkdir(parents=True)
        (target / "a.html").write_text("x")
        (target / "sub" / "b.txt").write_text("y")
        outside = self.base / "garder.txt"
        outside.write_text("z")
        (target / "lien").symlink_to(outside)
        result = clear_directory(target, self.project)
        self.assertEqual((result.removed, result.failed), (3, ()))
        self.assertTrue(target.is_dir())
        self.assertEqual(list(target.iterdir()), [])
        self.assertTrue(outside.exists())

    def test_undeletable_entry_reported_others_removed(self) -> None:
        target = self.base / "exports"
        locked = target / "verrou"
        locked.mkdir(parents=True)
        (locked / "f").write_text("x")
        (target / "libre.txt").write_text("x")
        locked.chmod(0o500)  # contenu non supprimable (hors root)
        try:
            result = clear_directory(target, self.project)
        finally:
            locked.chmod(0o700)
        self.assertFalse((target / "libre.txt").exists())
        if os.geteuid() != 0:
            self.assertEqual(result.removed, 1)
            self.assertEqual(len(result.failed), 1)
            self.assertIn("verrou", result.failed[0])

    def test_missing_folder_is_created(self) -> None:
        target = self.base / "nouveau"
        self.assertEqual(clear_directory(target, self.project).removed, 0)
        self.assertTrue(target.is_dir())

    def test_system_and_home_folders_refused(self) -> None:
        for path in ("/", "/etc", "/home", "/root", "/usr", "/var", "/home/quelquun"):
            with self.subTest(path=path), self.assertRaises(UnsafeDirectoryError):
                check_clearable(Path(path), self.project)

    def test_project_root_and_parents_refused(self) -> None:
        for path in (self.project, self.base):
            with self.subTest(path=path), self.assertRaises(UnsafeDirectoryError):
                check_clearable(path, self.project)

    def test_project_subfolder_allowed(self) -> None:
        self.assertEqual(check_clearable(self.project / "var" / "exports", self.project),
                         (self.project / "var" / "exports").resolve())

    def test_file_refused(self) -> None:
        f = self.base / "fichier"
        f.write_text("x")
        with self.assertRaises(UnsafeDirectoryError):
            check_clearable(f, self.project)


class EffectiveDirectoriesTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_default_then_absolute_then_relative_to_project(self) -> None:
        settings = MemorySettings()
        container = FakeContainer(settings, self.root)
        self.assertEqual(container.exports_dir, self.root / "var" / "exports")
        settings.values["exports_dir_override"] = "/srv/rapports"
        self.assertEqual(container.exports_dir, Path("/srv/rapports"))
        settings.values["screenshots_dir_override"] = "captures"
        self.assertEqual(container.screenshots_dir, self.root / "captures")


class SettingsScreenDirectoriesTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.settings = MemorySettings()
        self.container = FakeContainer(self.settings, self.root)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _run(self, steps) -> HostApp:
        app = HostApp(SettingsScreen(container=self.container))

        async def scenario() -> None:
            async with app.run_test(size=(80, 24)) as pilot:
                await pilot.pause()
                await steps(app, pilot)

        asyncio.run(scenario())
        return app

    def test_defaults_shown_short_and_not_saved(self) -> None:
        async def steps(app, pilot):
            self.assertEqual(app.screen.query_one("#exports-dir-input", Input).value, "var/exports")
            app.screen.query_one("#apply", Button).press()
            await pilot.pause()
        self._run(steps)
        self.assertEqual(self.settings.values["exports_dir_override"], "")
        self.assertEqual(self.settings.values["screenshots_dir_override"], "")

    def test_apply_saves_typed_folder(self) -> None:
        async def steps(app, pilot):
            app.screen.query_one("#exports-dir-input", Input).value = "/srv/rapports"
            app.screen.query_one("#apply", Button).press()
            await pilot.pause()
        self._run(steps)
        self.assertEqual(self.settings.values["exports_dir_override"], "/srv/rapports")

    def test_clear_asks_confirmation_with_path_then_empties_typed_folder(self) -> None:
        target = self.root / "mes-exports"
        target.mkdir()
        (target / "vieux.html").write_text("x")

        async def steps(app, pilot):
            app.screen.query_one("#exports-dir-input", Input).value = "mes-exports"
            app.screen.query_one("#clear-exports", Button).press()
            await pilot.pause()
            self.assertIsInstance(app.screen, ConfirmScreen)
            self.assertIn(str(target), str(app.screen._message))
            app.screen.query_one("#confirm", Button).press()
            await pilot.pause()
            await app.workers.wait_for_complete()
            await pilot.pause()
        app = self._run(steps)
        self.assertEqual(list(target.iterdir()), [])
        self.assertTrue(any("1 élément" in m for m in app.messages))

    def test_clear_cancelled_keeps_files(self) -> None:
        target = self.root / "var" / "screenshots"
        target.mkdir(parents=True)
        (target / "capture.svg").write_text("x")

        async def steps(app, pilot):
            app.screen.query_one("#clear-screenshots", Button).press()
            await pilot.pause()
            app.screen.query_one("#cancel", Button).press()
            await pilot.pause()
        self._run(steps)
        self.assertTrue((target / "capture.svg").exists())

    def test_clear_refuses_dangerous_folder(self) -> None:
        async def steps(app, pilot):
            app.screen.query_one("#exports-dir-input", Input).value = "/etc"
            app.screen.query_one("#clear-exports", Button).press()
            await pilot.pause()
            app.screen.query_one("#confirm", Button).press()
            await pilot.pause()
            await app.workers.wait_for_complete()
            await pilot.pause()
        app = self._run(steps)
        self.assertTrue(any("Dossier refusé" in m for m in app.messages))
