# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Installation de la langue AVANT tout autre import de l'interface
(OMEGA-FIRE_PLAN-DETAILLE_I18N.md §5, repris d'omega_serv/bootstrap/early_language.py).

La langue ne change jamais en cours de processus (changer = redemarrer l'interface). En
l'installant avant d'importer le conteneur et la TUI, toute phrase traduite au chargement
d'un module (menus, sections, aide) est deja dans la bonne langue. Ce module ne charge
volontairement que le strict minimum (reglages, catalogues, choix de la langue)."""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from omega_lib.i18n.models import LanguageChoice
from omega_lib.infrastructure.terminal.detector import SystemTerminalDetector

from omega_fire.application.commands.select_language import install_interface_language
from omega_fire.infrastructure.config.paths import RUNTIME_DIR
from omega_fire.infrastructure.i18n.gettext_language_catalog import GettextLanguageCatalog
from omega_fire.infrastructure.storage.files.json_settings_store import JsonSettingsStore


def install_language_early(environ: Mapping[str, str], runtime_dir: Path = RUNTIME_DIR) -> LanguageChoice:
    return install_interface_language(
        settings_store=JsonSettingsStore(runtime_dir / "settings.json"),
        catalog=GettextLanguageCatalog(),
        environ=environ,
        terminal_family=SystemTerminalDetector().detect().family,
    )
