# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Guide d'aide centralise (version 3.5, « comme omega-serv ») : toutes les fiches deja
redigees (help_text.py) dans l'ordre des menus, liens « Voir aussi », export HTML ; le
bouton « 10. AIDE » de l'accueil ouvre le guide."""
from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from textual.widgets import Button

from omega_fire.infrastructure.exporters.html_exporter import HtmlExporter
from omega_fire.interfaces.cli.help_text import HELP_ENTRIES
from omega_fire.interfaces.tui.section_registry import SECTIONS
from omega_fire.interfaces.tui.screens import guide_screens
from omega_fire.interfaces.tui.screens.guide_screens import GuideMenuScreen, guide_html_context
from omega_fire.interfaces.tui.screens.home import HomeScreen
from omega_fire.interfaces.tui.support.guide import guide_pages

from .i18n_helpers import FakeContainer, HostApp, MemorySettings

TEMPLATES = Path(__file__).resolve().parents[2] / "src" / "omega_fire" / "domain" / "reports" / "templates"


class GuideContentTest(unittest.TestCase):
    def test_chaque_section_et_action_a_sa_fiche(self) -> None:
        ids = [page.page_id for page in guide_pages()]
        self.assertEqual(len(ids), len(set(ids)))
        for section_id, (_title, items) in SECTIONS.items():
            self.assertIn(section_id, ids)
            for item in items:
                self.assertIn(item.action_id, ids)
                # Toute action du menu a une fiche redigee (pas seulement le libelle court).
                self.assertIn(item.action_id, HELP_ENTRIES, item.action_id)

    def test_liens_voir_aussi_valides(self) -> None:
        ids = {page.page_id for page in guide_pages()}
        for page in guide_pages():
            for ref in (page.entry.see_also if page.entry else []):
                self.assertIn(ref, ids, f"{page.page_id} -> {ref}")

    def test_export_html(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "guide.html"
            HtmlExporter(TEMPLATES).export_data(
                guide_html_context(guide_pages(), "omega-base", "2026-10-28 12:00:00"), path,
                template_name="guide.html.j2")
            html = path.read_text(encoding="utf-8")
        self.assertIn('id="p-5-1"', html)
        self.assertIn('href="#p-5-2"', html)       # « Voir aussi » de 5.1
        self.assertIn("Raccourcis clavier", html)
        self.assertEqual(html.count('<section class="guide-page"'), len(guide_pages()))

    def test_export_avec_faq_et_faq_seule(self) -> None:
        from omega_fire.interfaces.tui.support.guide_faq import faq_entries

        with tempfile.TemporaryDirectory() as tmp:
            exporter = HtmlExporter(TEMPLATES)
            full, faq_only = Path(tmp) / "g.html", Path(tmp) / "f.html"
            exporter.export_data(guide_html_context(guide_pages(), "omega-base", "t", faq=faq_entries()),
                                 full, template_name="guide.html.j2")
            exporter.export_data(guide_html_context([], "omega-base", "t", faq=faq_entries(), faq_only=True),
                                 faq_only, template_name="guide.html.j2")
            full_html, faq_html = full.read_text(encoding="utf-8"), faq_only.read_text(encoding="utf-8")
        count = len(faq_entries())
        self.assertGreaterEqual(count, 15)
        self.assertEqual(full_html.count('<section class="guide-page"'), len(guide_pages()) + count)
        self.assertEqual(faq_html.count('<section class="guide-page"'), count)
        self.assertIn(f'id="faq-{count}"', faq_html)


class GuideNavigationTest(unittest.TestCase):
    def test_bouton_aide_ouvre_le_guide_puis_une_fiche(self) -> None:
        async def run(tmp: Path) -> None:
            app = HostApp(HomeScreen(container=FakeContainer(MemorySettings(), tmp)))
            async with app.run_test(size=(110, 34)) as pilot:
                await pilot.pause()
                app.screen.query_one("#section-10", Button).press()
                await pilot.pause()
                self.assertIsInstance(app.screen, GuideMenuScreen)
                app.screen.query_one("#faq", Button).press()
                await pilot.pause()
                self.assertEqual(type(app.screen).__name__, "FaqScreen")
                await pilot.press("escape")
                await pilot.pause()
                await pilot.press("enter")
                await pilot.pause()
                self.assertEqual(type(app.screen).__name__, "GuideDetailScreen")

        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(guide_screens, "log_action_result", lambda *a, **k: None):
            asyncio.run(run(Path(tmp)))


class GuideExportLanguageTest(unittest.TestCase):
    """Retour utilisateur 2026-10-28 : guide et FAQ exportes restaient en francais alors que
    la « Langue des exports » etait l'allemand ou le portugais."""

    def test_export_suit_la_langue_des_exports(self) -> None:
        from omega_fire.application.commands.select_language import EXPORT_LANGUAGE_KEY

        locale = Path(__file__).resolve().parents[2] / "src" / "omega_fire" / "locale"
        if not (locale / "de" / "LC_MESSAGES" / "omega-fire.mo").is_file():
            self.skipTest("catalogues compiles absents")

        async def run(tmp: Path) -> Path:
            container = FakeContainer(MemorySettings({EXPORT_LANGUAGE_KEY: "de"}), tmp, locale=locale)
            app = HostApp(GuideMenuScreen(container=container))
            async with app.run_test(size=(110, 34)) as pilot:
                await pilot.pause()
                app.screen.query_one("#export-html", Button).press()
                for _attempt in range(50):
                    await pilot.pause(0.1)
                    found = list((tmp / "var" / "exports").glob("guide-aide_*.html"))
                    if found:
                        return found[0]
            self.fail("export absent")

        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(guide_screens, "log_action_result", lambda *a, **k: None):
            html = asyncio.run(run(Path(tmp))).read_text(encoding="utf-8")
        self.assertIn("Inhalt", html)                                  # Sommaire
        self.assertIn("Fähigkeitsregister anzeigen", html)             # fiche 1.1 (help_text)
        self.assertIn("FÄHIGKEITEN &amp; DIAGNOSEN", html)             # titre de section
        self.assertIn("Wie entferne ich", html)                        # FAQ
        self.assertNotIn("Comment l'utiliser", html)


if __name__ == "__main__":
    unittest.main()
