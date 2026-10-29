# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Retour utilisateur 2026-10-28 : rapport d'audit exporte en allemand (interface en
francais) avec les motifs des capacites restes en francais — rediges au scan dans la langue
de l'interface. LazyText garde la source et les valeurs pour les recomposer a l'export."""
from __future__ import annotations

import unittest
from pathlib import Path

from omega_fire.application.commands.select_language import load_export_language
from omega_fire.core.capability import create_capability
from omega_fire.core.enums import CapabilityStatus
from omega_fire.infrastructure.i18n.gettext_language_catalog import GettextLanguageCatalog
from omega_fire.shared.i18n import N_, lazy, retranslate, translating_as

LOCALE = Path(__file__).resolve().parents[2] / "src" / "omega_fire" / "locale"


@unittest.skipUnless((LOCALE / "de" / "LC_MESSAGES" / "omega-fire.mo").is_file(), "catalogues compiles absents")
class LazyTextTest(unittest.TestCase):
    def setUp(self) -> None:
        self.de = load_export_language(GettextLanguageCatalog(LOCALE), "de")

    def test_motif_recompose_dans_la_langue_de_l_export(self) -> None:
        inner = lazy(N_("Service « {service_name} » introuvable"), service_name="fail2ban")
        reason = lazy(N_("Service non installé sur le système ({message})"), message=inner)
        self.assertEqual(reason, "Service non installé sur le système (Service « fail2ban » introuvable)")
        capability = create_capability(capability_id="fail2ban_service", status=CapabilityStatus.MISSING,
                                       reason=reason, category="service")
        with translating_as(self.de):
            german = capability.to_dict()["reason"]
        self.assertNotIn("Service non installé", german)
        self.assertIn("fail2ban", german)
        self.assertEqual(retranslate("texte brut"), "texte brut")


if __name__ == "__main__":
    unittest.main()
