# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Chargement des feuilles de style selon le profil de rendu deja decide.
Porte depuis omega-check (D-008), meme mecanisme que le reste de la
suite omega-*."""
from __future__ import annotations

from pathlib import Path

from omega_lib.terminal.models import RenderProfile

_STYLES_DIR = Path(__file__).parent.parent / "styles"

_PROFILE_STYLESHEETS: dict[RenderProfile, str] = {
    RenderProfile.COMPLETE: "complete.tcss",
    RenderProfile.STANDARD: "standard.tcss",
    RenderProfile.REDUCED: "reduced.tcss",
    RenderProfile.MONO: "mono.tcss",
}


def stylesheet_paths_for(profile: RenderProfile) -> tuple[Path, Path]:
    """Retourne (base.tcss, <profil>.tcss) — base toujours chargee en
    premier, le fichier du profil vient ensuite affiner/surcharger."""
    return (_STYLES_DIR / "base.tcss", _STYLES_DIR / _PROFILE_STYLESHEETS[profile])


def load_paths_for(profile: RenderProfile) -> list[str]:
    """Format attendu par `textual.app.App.CSS_PATH` (liste de chaines)."""
    return [str(path) for path in stylesheet_paths_for(profile)]
