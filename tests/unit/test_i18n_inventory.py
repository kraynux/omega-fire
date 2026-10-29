# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Inventaire i18n tenu a jour (OMEGA-FIRE_PLAN-DETAILLE_I18N.md §4.6) : tout nouveau texte doit
etre classe (traduire ou non) au moment ou il est ecrit ; les contrats machine ne sont jamais
classes a traduire ; l'ancienne interface --legacy-cli reste hors inventaire (Q1)."""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
DECISIONS = PROJECT.parent / "I18N_DECISIONS.md"


def _load_tool():
    spec = importlib.util.spec_from_file_location("i18n_inventory", PROJECT / "tools" / "i18n_inventory.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["i18n_inventory"] = module
    spec.loader.exec_module(module)
    return module


tool = _load_tool()


@unittest.skipUnless(DECISIONS.is_file(), "decisions de l'inventaire absentes (hors poste de developpement)")
class InventoryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.entries, _skipped, cls.missing = tool.scan()
        tool.apply_decisions(cls.entries, tool.load_rule_decisions(DECISIONS), {})

    def test_sources_found(self) -> None:
        self.assertEqual(self.missing, [])

    def test_every_text_is_classified(self) -> None:
        undecided = [f"{e.file}:{e.line} {e.text!r} ({e.reason})" for e in self.entries
                     if e.category in (tool.A_DECIDER, tool.PROBABLE)]
        self.assertEqual(undecided, [], "nouveau texte a classer : relancer tools/i18n_inventory.py")

    def test_machine_contracts_never_translated(self) -> None:
        for e in self.entries:
            if e.category == tool.TRADUIRE and "texte d'aide citant" not in e.reason:
                for marker, _why in tool.MACHINE_CONTRACTS:
                    self.assertNotIn(marker, e.text, f"{e.file}:{e.line}")

    def test_language_selector_label_never_translated(self) -> None:
        labels = [e for e in self.entries if e.text == "Langue / Language"]
        self.assertTrue(labels)
        self.assertTrue(all(e.category == tool.NE_PAS for e in labels))

    def test_legacy_cli_is_out_of_scope(self) -> None:
        files = {e.file for e in self.entries}
        self.assertNotIn("interfaces/cli/actions.py", files)
        self.assertIn("interfaces/cli/help_text.py", files)
