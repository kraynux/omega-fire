# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Use case : choisir et persister une surcharge manuelle du profil de
rendu (ou revenir a la detection automatique). Meme mecanisme que
select_theme.py, clef deja lue par
interfaces/tui/controllers/startup_controller.py::_effective_render_profile()."""
from __future__ import annotations

from omega_lib.terminal.models import RenderProfile

from omega_fire.ports.settings_store import SettingsStore

_RENDER_PROFILE_OVERRIDE_KEY = "render_profile_override"


def select_render_profile(*, settings_store: SettingsStore, profile_value: str) -> None:
    """`profile_value` vide = retour a la detection automatique ; sinon
    doit correspondre a une valeur de RenderProfile ("complete", etc.)."""
    if profile_value and profile_value not in {p.value for p in RenderProfile}:
        raise ValueError(f"Profil de rendu inconnu : {profile_value!r}")
    settings_store.set(_RENDER_PROFILE_OVERRIDE_KEY, profile_value)
