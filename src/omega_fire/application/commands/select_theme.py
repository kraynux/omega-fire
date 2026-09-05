# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Use case : choisir et persister le theme actif (migration TUI Textual)."""
from __future__ import annotations

from omega_lib.theme.policies import TUI_THEMES

from omega_fire.application.exceptions import UnknownThemeError
from omega_fire.ports.settings_store import SettingsStore

_THEME_KEY = "theme"


def select_theme(*, settings_store: SettingsStore, theme_name: str) -> None:
    if theme_name not in TUI_THEMES:
        raise UnknownThemeError(theme_name)
    settings_store.set(_THEME_KEY, theme_name)
