# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Titres d'action de l'historique d'audit traduits a l'affichage (retour utilisateur
2026-10-28 : export d'audit montrant des titres en francais et en polonais)."""
from __future__ import annotations

import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from omega_fire.application.commands.select_language import load_export_language
from omega_fire.application.queries.audit_report.activity_section import collect_journal_summary
from omega_fire.infrastructure.i18n.gettext_language_catalog import GettextLanguageCatalog
from omega_fire.interfaces.tui.support.action_titles import ActionTitleTranslator
from omega_fire.shared.i18n import STATE, action_title, set_action_title_translator, translating_as

from .i18n_helpers import write_mo

_DE = {"Nettoyage avancé": "Erweiterte Bereinigung", "RAPPORT STATISTIQUE — 30 JOURS": "STATISTIKBERICHT — 30 TAGE"}
_PL = {"RAPPORT STATISTIQUE — 30 JOURS": "RAPORT STATYSTYCZNY — 30 DNI"}


class ActionTitleTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        locale = Path(self._tmp.name)
        write_mo(locale / "de" / "LC_MESSAGES" / "omega-fire.mo", _DE, "validated")
        write_mo(locale / "pl" / "LC_MESSAGES" / "omega-fire.mo", _PL, "validated")
        self.catalog = GettextLanguageCatalog(locale)
        STATE.reset()
        set_action_title_translator(ActionTitleTranslator(
            {"5.7": "Nettoyage avancé"}, lambda: self.catalog.available().keys(), self.catalog.translated_phrases))
        self.de = load_export_language(self.catalog, "de")

    def tearDown(self) -> None:
        set_action_title_translator(None)
        STATE.reset()
        self._tmp.cleanup()

    def test_numbered_title_uses_translated_menu_label(self) -> None:
        self.assertEqual(action_title("5.7 Nettoyage Avance"), "5.7 Nettoyage avancé")
        with translating_as(self.de):
            self.assertEqual(action_title("5.7 Nettoyage Avance"), "5.7 Erweiterte Bereinigung")

    def test_translatable_title_and_title_saved_in_another_language(self) -> None:
        with translating_as(self.de):
            self.assertEqual(action_title("RAPPORT STATISTIQUE — 30 JOURS"), "STATISTIKBERICHT — 30 TAGE")
            self.assertEqual(action_title("RAPORT STATYSTYCZNY — 30 DNI"), "STATISTIKBERICHT — 30 TAGE")
        self.assertEqual(action_title("RAPORT STATYSTYCZNY — 30 DNI"), "RAPPORT STATISTIQUE — 30 JOURS")

    def test_unknown_title_unchanged_and_no_translator_means_unchanged(self) -> None:
        self.assertEqual(action_title("9.9 Action inconnue"), "9.9 Action inconnue")
        set_action_title_translator(None)
        self.assertEqual(action_title("RAPORT STATYSTYCZNY — 30 DNI"), "RAPORT STATYSTYCZNY — 30 DNI")

    def test_audit_journal_summary_counts_same_action_together_in_export_language(self) -> None:
        when = datetime(2026, 10, 28)
        entries = [SimpleNamespace(action=a, success=True, timestamp=when) for a in
                   ("RAPPORT STATISTIQUE — 30 JOURS", "RAPORT STATYSTYCZNY — 30 DNI",
                    "RAPORT STATYSTYCZNY — 30 DNI", "5.7 Nettoyage Avance")]
        logger = SimpleNamespace(get_all_since=lambda since: entries)
        with translating_as(self.de):
            summary = collect_journal_summary(logger, None)
        self.assertEqual(summary.top_events, [("STATISTIKBERICHT — 30 TAGE", 3), ("5.7 Erweiterte Bereinigung", 1)])


class RenumberedMenuTest(unittest.TestCase):
    """Menu 5 renumerote en 3.5 : une ancienne entree « 5.2 Analyser les IPs (Top N) » ne doit
    pas s'afficher sous le nouveau libelle de 5.2 (« Favoris »)."""

    def setUp(self) -> None:
        STATE.reset()
        set_action_title_translator(ActionTitleTranslator(
            {"5.2": "Favoris", "5.4": "Analyser les IPs (Top N)", "5.7": "Restaurer un backup"},
            lambda: [], lambda code: {},
            renumbered={"5.2": ["Analyser les IPs (Top N)"], "5.7": ["Nettoyage avancé"]},
        ))

    def tearDown(self) -> None:
        set_action_title_translator(None)
        STATE.reset()

    def test_ancien_numero_garde_son_libelle(self) -> None:
        self.assertEqual(action_title("5.2 Analyser les IPs (Top N)"), "5.2 Analyser les IPs (Top N)")
        self.assertEqual(action_title("5.7 Nettoyage Avance"), "5.7 Nettoyage avancé")

    def test_nouveau_numero_utilise_le_libelle_actuel(self) -> None:
        self.assertEqual(action_title("5.2 favoris"), "5.2 Favoris")
        self.assertEqual(action_title("5.4 Analyser les IPs (Top N)"), "5.4 Analyser les IPs (Top N)")

    def test_libelle_inconnu_reste_tel_quel(self) -> None:
        self.assertEqual(action_title("5.2 Autre chose"), "5.2 Autre chose")


if __name__ == "__main__":
    unittest.main()
