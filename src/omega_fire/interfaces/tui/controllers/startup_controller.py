# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Controller : resout theme et profil de rendu au demarrage du TUI.
Porte depuis omega-check (D-008), meme mecanisme que le reste de la
suite omega-*."""
from __future__ import annotations

from dataclasses import dataclass

from omega_lib.terminal.models import RenderProfile, TerminalProfile
from omega_lib.theme.models import AppliedTheme
from omega_lib.theme.policies import DEFAULT_TUI_THEME
from omega_lib.theme.service import resolve_applied_theme

from omega_fire.application.queries.detect_terminal import detect_terminal
from omega_fire.ports.settings_store import SettingsStore
from omega_fire.ports.terminal_detector import TerminalDetector

_THEME_KEY = "theme"
_RENDER_PROFILE_OVERRIDE_KEY = "render_profile_override"


@dataclass(frozen=True, slots=True)
class StartupState:
    """Etat resolu au demarrage : terminal detecte et theme effectivement
    applique, prets avant tout montage d'ecran par app.py."""

    terminal: TerminalProfile
    theme: AppliedTheme


def resolve_startup_state(
    *, terminal_detector: TerminalDetector, settings_store: SettingsStore
) -> StartupState:
    """Detecte le terminal (profil de rendu automatique, sauf surcharge
    manuelle persistee via select_render_profile) puis resout le theme
    persiste (ou le theme par defaut si inconnu/jamais choisi)."""
    terminal = detect_terminal(terminal_detector=terminal_detector)
    render_profile = _effective_render_profile(terminal, settings_store)

    requested_theme = settings_store.get(_THEME_KEY, DEFAULT_TUI_THEME) or DEFAULT_TUI_THEME
    theme = resolve_applied_theme(requested_theme, render_profile)
    if theme.fell_back_from is not None:
        settings_store.set(_THEME_KEY, theme.theme_name)

    return StartupState(terminal=terminal, theme=theme)


def _effective_render_profile(terminal: TerminalProfile, settings_store: SettingsStore) -> RenderProfile:
    override = settings_store.get(_RENDER_PROFILE_OVERRIDE_KEY, "")
    if override:
        return RenderProfile(override)
    return terminal.render_profile
