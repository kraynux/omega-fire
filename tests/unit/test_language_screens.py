# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecrans du changement de langue (plan i18n lot 2) : selecteur « Langue / Language » dans
Reglages, confirmation, demande de redemarrage de l'interface, splash de la nouvelle langue."""
from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

from textual.widgets import Button, Select, Static

from omega_fire.application.commands.select_language import LANGUAGE_KEY, install_interface_language
from omega_fire.infrastructure.i18n.gettext_language_catalog import GettextLanguageCatalog
from omega_fire.interfaces.tui.screens.confirm import ConfirmScreen
from omega_fire.interfaces.tui.screens.language_changed_splash_screen import (
    LANGUAGE_LABEL,
    LanguageChangedSplashScreen,
)
from omega_fire.interfaces.tui.screens.settings_screen import SettingsScreen, language_options
from omega_fire.shared.i18n import DOMAIN, STATE

from .i18n_helpers import HostApp, MemorySettings, FakeContainer, write_mo


class LanguageScreensTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.locale = self.root / "locale"
        locale = self.locale
        write_mo(locale / "en" / "LC_MESSAGES" / f"{DOMAIN}.mo",
                 {"Cliquez ou appuyez sur une touche pour continuer...": "Click or press any key to continue..."})
        self.catalog = GettextLanguageCatalog(locale)

    def tearDown(self) -> None:
        STATE.reset()
        self._tmp.cleanup()

    def test_options_native_names_french_first_testing_mentioned(self) -> None:
        options = language_options(self.catalog)
        self.assertEqual(options[0], ("Français", "fr"))
        self.assertIn(("English (en test)", "en"), options)

    def test_choosing_a_language_confirms_then_requests_restart(self) -> None:
        container = FakeContainer(MemorySettings(), self.root, self.locale)
        app = HostApp(SettingsScreen(container=container))

        async def scenario() -> None:
            async with app.run_test() as pilot:
                await pilot.pause()
                labels = [str(w.render()) for w in app.screen.query(Static)]
                self.assertIn(LANGUAGE_LABEL, labels)
                app.screen.query_one("#language-select", Select).value = "en"
                await pilot.pause()
                self.assertIsInstance(app.screen, ConfirmScreen)
                app.screen.query_one("#confirm", Button).press()
                await pilot.pause()

        asyncio.run(scenario())
        self.assertEqual(container.settings_store.values[LANGUAGE_KEY], "en")
        self.assertIsNotNone(app.pending_restart)
        self.assertEqual(app.pending_restart.language_code, "en")

    def test_cancel_keeps_language_and_selector(self) -> None:
        container = FakeContainer(MemorySettings(), self.root, self.locale)
        app = HostApp(SettingsScreen(container=container))

        async def scenario() -> None:
            async with app.run_test() as pilot:
                await pilot.pause()
                app.screen.query_one("#language-select", Select).value = "en"
                await pilot.pause()
                app.screen.query_one("#cancel", Button).press()
                await pilot.pause()
                self.assertEqual(app.screen.query_one("#language-select", Select).value, "fr")

        asyncio.run(scenario())
        self.assertNotIn(LANGUAGE_KEY, container.settings_store.values)
        self.assertIsNone(app.pending_restart)

    def test_splash_shows_new_language_and_translated_prompt(self) -> None:
        install_interface_language(settings_store=MemorySettings({LANGUAGE_KEY: "en"}),
                                   catalog=self.catalog, environ={})
        app = HostApp(LanguageChangedSplashScreen(native_name=STATE.language.native_name))

        async def scenario() -> None:
            async with app.run_test() as pilot:
                await pilot.pause()
                self.assertEqual(str(app.screen.query_one("#language-name", Static).render()),
                                 "Langue / Language : English")
                self.assertEqual(str(app.screen.query_one("#language-prompt", Static).render()),
                                 "Click or press any key to continue...")

        asyncio.run(scenario())
