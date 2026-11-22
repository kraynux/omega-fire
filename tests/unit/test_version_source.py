# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""La version affichee (en-tete, splash, tableau de bord, contact et support) est lue dans
pyproject.toml, seule source (decision de l'auteur, 2026-11-22)."""
import re
import unittest
from pathlib import Path

from omega_fire.core.constants import OMEGA_FIRE_VERSION

ROOT = Path(__file__).resolve().parents[2]


class VersionSourceTest(unittest.TestCase):
    def test_version_affichee_egale_pyproject(self) -> None:
        text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        match = re.search(r'^version = "([^"]+)"$', text, re.MULTILINE)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), OMEGA_FIRE_VERSION)  # type: ignore[union-attr]

    def test_aucune_copie_dans_constants(self) -> None:
        constants = (ROOT / "src/omega_fire/core/constants.py").read_text(encoding="utf-8")
        self.assertIsNone(re.search(r'^OMEGA_FIRE_VERSION\s*=\s*"', constants, re.MULTILINE))


if __name__ == "__main__":
    unittest.main()
