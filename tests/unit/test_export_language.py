# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Langue des exports (OMEGA-FIRE_PLAN-DETAILLE_I18N.md, lot N, Q3) : reglage dans Reglages,
traduction le temps d'un export seulement (sans toucher l'interface ni les autres fils),
modeles .j2 traduits au rendu, lang/dir du document."""
from __future__ import annotations

import asyncio
import gettext
import re
import tempfile
import threading
import unittest
from pathlib import Path

from textual.widgets import Button, Select

from omega_fire.application.commands.select_language import (
    EXPORT_LANGUAGE_KEY,
    export_language_override,
    load_export_language,
    select_export_language,
)
from omega_fire.application.exceptions import UnknownLanguageError
from omega_fire.infrastructure.config.paths import TEMPLATES_DIR
from omega_fire.infrastructure.exporters.html_exporter import HtmlExporter
from omega_fire.infrastructure.i18n.gettext_language_catalog import DEFAULT_LOCALE_DIR, GettextLanguageCatalog
from omega_fire.interfaces.tui.export_language import export_translation
from omega_fire.interfaces.tui.screens.settings_screen import SettingsScreen
from omega_fire.ports.language_catalog import LanguageCatalogError
from omega_fire.shared.i18n import STATE, _, html_dir, html_lang, translating_as

from .i18n_helpers import FakeContainer, HostApp, MemorySettings, write_mo

_J2_CALL = re.compile(r'_\(\s*"((?:[^"\\]|\\.)*)"\s*\)')
_RULESET = {"generated_at": "2026-10-28 10:00:00", "filter_label": "f", "total_rules": 0,
            "total_groups": 0, "groups": []}


class TranslatingAsTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.locale = Path(self._tmp.name)
        write_mo(self.locale / "de" / "LC_MESSAGES" / "omega-fire.mo", {"Bonjour": "Hallo"}, "validated")
        self.catalog = GettextLanguageCatalog(self.locale)
        STATE.reset()

    def tearDown(self) -> None:
        STATE.reset()
        self._tmp.cleanup()

    def test_only_inside_the_block(self) -> None:
        state = load_export_language(self.catalog, "de")
        self.assertEqual(_("Bonjour"), "Bonjour")
        with translating_as(state):
            self.assertEqual(_("Bonjour"), "Hallo")
            self.assertEqual((html_lang(), html_dir()), ("de", "ltr"))
        self.assertEqual(_("Bonjour"), "Bonjour")
        self.assertEqual(html_lang(), "fr")

    def test_none_keeps_interface_language(self) -> None:
        with translating_as(None):
            self.assertEqual(_("Bonjour"), "Bonjour")

    def test_other_threads_keep_interface_language(self) -> None:
        """L'interface (fil principal) continue de s'afficher pendant un export en thread."""
        seen: list[str] = []
        inside, done = threading.Event(), threading.Event()

        def export() -> None:
            with translating_as(load_export_language(self.catalog, "de")):
                seen.append(_("Bonjour"))
                inside.set()
                done.wait(5)

        worker = threading.Thread(target=export)
        worker.start()
        inside.wait(5)
        seen.append(_("Bonjour"))
        done.set()
        worker.join(5)
        self.assertEqual(seen, ["Hallo", "Bonjour"])

    def test_missing_or_broken_catalog_refused(self) -> None:
        (self.locale / "it" / "LC_MESSAGES").mkdir(parents=True)
        (self.locale / "it" / "LC_MESSAGES" / "omega-fire.mo").write_bytes(b"pas un catalogue")
        for code in ("es", "it"):
            with self.subTest(code=code), self.assertRaises(LanguageCatalogError):
                load_export_language(self.catalog, code)


class ExportLanguageSettingTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        write_mo(self.root / "locale" / "de" / "LC_MESSAGES" / "omega-fire.mo", {"Bonjour": "Hallo"}, "validated")
        self.settings = MemorySettings()
        self.container = FakeContainer(self.settings, self.root)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_override_only_when_set_and_different(self) -> None:
        self.assertIsNone(export_language_override(self.settings, "fr"))
        self.settings.values[EXPORT_LANGUAGE_KEY] = "de"
        self.assertEqual(export_language_override(self.settings, "fr"), "de")
        self.assertIsNone(export_language_override(self.settings, "de"))

    def test_select_saves_code_like_interface_saved_empty_unknown_refused(self) -> None:
        catalog = self.container.language_catalog
        select_export_language(settings_store=self.settings, catalog=catalog, language_code="de")
        self.assertEqual(self.settings.values[EXPORT_LANGUAGE_KEY], "de")
        select_export_language(settings_store=self.settings, catalog=catalog, language_code="")
        self.assertEqual(self.settings.values[EXPORT_LANGUAGE_KEY], "")
        with self.assertRaises(UnknownLanguageError):
            select_export_language(settings_store=self.settings, catalog=catalog, language_code="es")

    def test_broken_catalog_exports_in_interface_language_and_says_so(self) -> None:
        self.settings.values[EXPORT_LANGUAGE_KEY] = "de"
        (self.root / "locale" / "de" / "LC_MESSAGES" / "omega-fire.mo").write_bytes(b"abime")
        notes: list[str] = []

        class Screen:
            class app:  # noqa: N801 - imite screen.app.notify
                @staticmethod
                def notify(message, **_kwargs):
                    notes.append(str(message))

        self.assertIsNone(export_translation(Screen(), self.container))
        self.assertEqual(len(notes), 1)
        self.assertIn("Deutsch", notes[0])

    def _run(self, steps) -> HostApp:
        app = HostApp(SettingsScreen(container=self.container))

        async def scenario() -> None:
            async with app.run_test(size=(80, 24)) as pilot:
                await pilot.pause()
                await steps(app, pilot)

        asyncio.run(scenario())
        return app

    def test_settings_screen_offers_like_interface_then_languages_and_apply_saves(self) -> None:
        async def steps(app, pilot):
            select = app.screen.query_one("#export-language-select", Select)
            self.assertEqual(select.value, "__interface__")
            select.value = "de"
            app.screen.query_one("#apply", Button).press()
            await pilot.pause()
        self._run(steps)
        self.assertEqual(self.settings.values[EXPORT_LANGUAGE_KEY], "de")

    def test_settings_screen_like_interface_saved_empty(self) -> None:
        self.settings.values[EXPORT_LANGUAGE_KEY] = "de"

        async def steps(app, pilot):
            select = app.screen.query_one("#export-language-select", Select)
            self.assertEqual(select.value, "de")
            select.value = "__interface__"
            app.screen.query_one("#apply", Button).press()
            await pilot.pause()
        self._run(steps)
        self.assertEqual(self.settings.values[EXPORT_LANGUAGE_KEY], "")


class ShippedTemplatesTest(unittest.TestCase):
    """Modeles livres et catalogues livres (src/omega_fire/locale)."""

    def setUp(self) -> None:
        STATE.reset()
        self.catalog = GettextLanguageCatalog()
        self._tmp = tempfile.TemporaryDirectory()
        self.out = Path(self._tmp.name) / "ruleset.html"

    def tearDown(self) -> None:
        STATE.reset()
        self._tmp.cleanup()

    def _render(self, state) -> str:
        with translating_as(state):
            HtmlExporter(TEMPLATES_DIR).export_data(_RULESET, self.out, template_name="ruleset.html.j2")
        return self.out.read_text(encoding="utf-8")

    def test_french_by_default(self) -> None:
        page = self._render(None)
        self.assertIn('<html lang="fr" dir="ltr">', page)
        self.assertIn("Synthèse des règles firewall", page)

    def test_arabic_export_is_translated_and_right_to_left(self) -> None:
        page = self._render(load_export_language(self.catalog, "ar"))
        self.assertIn('<html lang="ar" dir="rtl">', page)
        self.assertNotIn("Synthèse des règles firewall", page)
        self.assertIn(load_export_language(self.catalog, "ar").gettext("Synthèse des règles firewall"), page)

    def test_every_template_phrase_translated_in_every_catalog(self) -> None:
        msgids = sorted({m.group(1) for path in TEMPLATES_DIR.glob("*.j2")
                         for m in _J2_CALL.finditer(path.read_text(encoding="utf-8"))})
        self.assertGreater(len(msgids), 100)
        for code in self.catalog.available():
            with (DEFAULT_LOCALE_DIR / code / "LC_MESSAGES" / "omega-fire.mo").open("rb") as handle:
                known = gettext.GNUTranslations(handle)._catalog  # type: ignore[attr-defined]
            missing = [m for m in msgids if not known.get(m)]
            with self.subTest(code=code):
                self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
