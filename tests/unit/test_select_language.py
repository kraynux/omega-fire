# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Langue de l'interface (plan i18n lot 2) : priorite au demarrage, replis vers le francais,
enregistrement, repli console, environnement du redemarrage de l'interface."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from omega_lib.i18n.models import LanguageStatus
from omega_lib.i18n.policies import PSEUDO_LANGUAGE_CODE

from omega_fire.app.bootstrap import build_execv_invocation, prepare_language_restart_environment
from omega_fire.application.commands.select_language import (
    LANGUAGE_CHANGED_ENV_VAR,
    LANGUAGE_ENV_VAR,
    LANGUAGE_KEY,
    available_languages,
    console_fallback_from,
    install_interface_language,
    select_language,
)
from omega_fire.application.exceptions import UnknownLanguageError
from omega_fire.infrastructure.i18n.gettext_language_catalog import GettextLanguageCatalog
from omega_fire.shared.i18n import DOMAIN, STATE, _, ngettext

from .i18n_helpers import MemorySettings, write_mo


class LanguageCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.locale = Path(self._tmp.name)
        write_mo(self.locale / "en" / "LC_MESSAGES" / f"{DOMAIN}.mo",
                 {"Retour": "Back", "{n} regle\0{n} regles": "{n} rule\0{n} rules"}, status="validated")
        self.catalog = GettextLanguageCatalog(self.locale)

    def tearDown(self) -> None:
        STATE.reset()
        self._tmp.cleanup()

    def install(self, settings: dict[str, str] | None = None, environ: dict[str, str] | None = None,
                terminal_family: str | None = None):
        return install_interface_language(settings_store=MemorySettings(settings), catalog=self.catalog,
                                          environ=environ or {}, terminal_family=terminal_family)


class StartupPriorityTest(LanguageCase):
    def test_french_by_default_text_unchanged(self) -> None:
        self.install()
        self.assertEqual(STATE.language.code, "fr")
        self.assertEqual(_("Retour"), "Retour")

    def test_setting_selects_language(self) -> None:
        self.install({LANGUAGE_KEY: "en"})
        self.assertEqual(_("Retour"), "Back")
        self.assertEqual(ngettext("{n} regle", "{n} regles", 3), "{n} rules")

    def test_environment_overrides_setting(self) -> None:
        self.install({LANGUAGE_KEY: "en"}, {LANGUAGE_ENV_VAR: "fr"})
        self.assertEqual(STATE.language.code, "fr")

    def test_system_lang_is_ignored(self) -> None:
        self.install(environ={"LANG": "en_US.UTF-8", "LC_ALL": "en_US.UTF-8"})
        self.assertEqual(STATE.language.code, "fr")

    def test_untranslated_phrase_stays_french(self) -> None:
        self.install({LANGUAGE_KEY: "en"})
        self.assertEqual(_("Phrase sans traduction"), "Phrase sans traduction")


class FallbackTest(LanguageCase):
    def test_unknown_language_falls_back_to_french(self) -> None:
        choice = self.install({LANGUAGE_KEY: "xx"})
        self.assertEqual(STATE.language.code, "fr")
        self.assertEqual(choice.fell_back_from, "xx")

    def test_corrupted_catalog_falls_back_to_french(self) -> None:
        bad = self.locale / "de" / "LC_MESSAGES" / f"{DOMAIN}.mo"
        bad.parent.mkdir(parents=True)
        bad.write_bytes(b"pas un catalogue")
        choice = self.install({LANGUAGE_KEY: "de"})
        self.assertEqual(STATE.language.code, "fr")
        self.assertEqual(choice.fell_back_from, "de")

    def test_unreadable_settings_start_in_french(self) -> None:
        class Broken(MemorySettings):
            def get(self, key, default=None):
                raise ValueError("json casse")
        install_interface_language(settings_store=Broken(), catalog=self.catalog, environ={})
        self.assertEqual(STATE.language.code, "fr")

    def test_linux_console_replaces_wide_script_by_english(self) -> None:
        write_mo(self.locale / "ja" / "LC_MESSAGES" / f"{DOMAIN}.mo", {"Retour": "戻る"})
        self.install({LANGUAGE_KEY: "ja"}, terminal_family="linux-tty")
        self.assertEqual(STATE.language.code, "en")
        self.assertEqual(console_fallback_from(), "ja")


class SelectorTest(LanguageCase):
    def test_french_first_then_present_catalogs(self) -> None:
        codes = [language.code for language in available_languages(self.catalog)]
        self.assertEqual(codes[0], "fr")
        self.assertIn("en", codes)

    def test_status_read_from_catalog(self) -> None:
        write_mo(self.locale / "es" / "LC_MESSAGES" / f"{DOMAIN}.mo", {"Retour": "Volver"})
        statuses = {language.code: language.status for language in available_languages(self.catalog)}
        self.assertEqual(statuses["en"], LanguageStatus.VALIDATED)
        self.assertEqual(statuses["es"], LanguageStatus.TESTING)

    def test_select_saves_setting_french_saved_as_empty(self) -> None:
        settings = MemorySettings()
        select_language(settings_store=settings, catalog=self.catalog, language_code="en")
        self.assertEqual(settings.values[LANGUAGE_KEY], "en")
        select_language(settings_store=settings, catalog=self.catalog, language_code="fr")
        self.assertEqual(settings.values[LANGUAGE_KEY], "")

    def test_select_unknown_language_refused(self) -> None:
        with self.assertRaises(UnknownLanguageError):
            select_language(settings_store=MemorySettings(), catalog=self.catalog, language_code="xx")

    def test_control_language_wraps_text(self) -> None:
        self.install({LANGUAGE_KEY: PSEUDO_LANGUAGE_CODE})
        self.assertEqual(_("Retour"), "⟦Retour⟧")


class RestartTest(unittest.TestCase):
    def test_execv_relaunches_same_python_same_module_same_args(self) -> None:
        path, argv = build_execv_invocation("/opt/omega-fire/.venv/bin/python", ["--x"])
        self.assertEqual(path, "/opt/omega-fire/.venv/bin/python")
        self.assertEqual(argv, ["/opt/omega-fire/.venv/bin/python", "-m", "omega_fire", "--x"])

    def test_restart_environment_requests_splash_and_drops_override(self) -> None:
        environ = {LANGUAGE_ENV_VAR: "fr", "PYTHONPATH": "/opt/omega-fire/src"}
        prepare_language_restart_environment(environ, "en")
        self.assertEqual(environ[LANGUAGE_CHANGED_ENV_VAR], "en")
        self.assertNotIn(LANGUAGE_ENV_VAR, environ)
        self.assertEqual(environ["PYTHONPATH"], "/opt/omega-fire/src")

    def test_launcher_preserves_language_override_through_sudo(self) -> None:
        launcher = Path(__file__).resolve().parents[2] / "omega-fire.sh"
        self.assertIn("OMEGA_FIRE_LANG", next(line for line in launcher.read_text().splitlines()
                                              if "exec sudo" in line))
