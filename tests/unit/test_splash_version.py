# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Splash : la barre de version affiche la version de l'application (2026-11-11 : « version 3.5 » etait
ecrit en dur alors que l'application etait en 3.6.1)."""
from __future__ import annotations

import unittest
from unittest import mock

from omega_fire.core.constants import OMEGA_FIRE_VERSION
from omega_fire.interfaces.tui.widgets import splash_hero


class SplashVersionTest(unittest.TestCase):
    def test_barre_avec_la_version_courante(self) -> None:
        bar = splash_hero._version_bar()
        self.assertIn(f"version {OMEGA_FIRE_VERSION}", bar)
        self.assertEqual(len(bar), 34)
        self.assertIn(bar, splash_hero._LOGO_LINES)

    def test_meme_dessin_qu_avant_pour_3_5(self) -> None:
        with mock.patch.object(splash_hero, "OMEGA_FIRE_VERSION", "3.5"):
            self.assertEqual(splash_hero._version_bar(), "█░▒▓████▓▒░version 3.5░▒▓█████▓▒░█")


if __name__ == "__main__":
    unittest.main()
