# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran REGLAGES (accessible depuis l'accueil, hors des 8 sections du
CLI — le CLI n'avait qu'un cycle de theme a la touche 't', pas d'ecran
dedie). Regroupe : choix du theme (parmi les 10 themes omega-*, pas les
themes Textual natifs — voir la note de base.tcss sur les variables
d'extension), et surcharge du profil de rendu (ou retour a la detection
automatique). Retour utilisateur reel : demande explicite d'un vrai
ecran de reglages plutot que de ne dependre que de la touche 't'."""
from __future__ import annotations

from typing import TYPE_CHECKING

from omega_lib.terminal.models import RenderProfile
from omega_lib.theme.policies import TUI_THEMES
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Select, Static

from omega_fire.application.commands.select_render_profile import select_render_profile
from omega_fire.application.commands.select_theme import select_theme
from omega_fire.application.exceptions import UnknownThemeError
from omega_fire.interfaces.tui.screens._base import OmegaScreen

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_AUTO_PROFILE = ""
_PROFILE_LABELS: dict[str, str] = {
    _AUTO_PROFILE: "Automatique (detection terminal)",
    RenderProfile.COMPLETE.value: "Complet",
    RenderProfile.STANDARD.value: "Standard",
    RenderProfile.REDUCED.value: "Reduit",
    RenderProfile.MONO.value: "Mono (ASCII seul)",
}


class SettingsScreen(OmegaScreen):
    """Theme actif et surcharge du profil de rendu."""

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="omega-form-panel"):
            yield Static("REGLAGES", classes="omega-title")

            yield Static("Theme", classes="omega-subtitle")
            yield Select(
                [(name, name) for name in TUI_THEMES.keys()],
                value=self.app.theme if self.app.theme in TUI_THEMES else next(iter(TUI_THEMES)),
                id="theme-select",
            )

            yield Static("Profil de rendu", classes="omega-subtitle")
            yield Select(
                [(label, value) for value, label in _PROFILE_LABELS.items()],
                value=self._current_profile_override(),
                id="profile-select",
            )
            yield Static(
                "Le profil de rendu determine la complexite visuelle (bordures, splash) "
                "selon les capacites du terminal — un changement ici prend effet au prochain lancement.",
                classes="omega-hint",
            )

            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button("Appliquer", id="apply", variant="primary")
                with Container(classes="omega-btn-frame"):
                    yield Button("Retour", id="back")
        yield Footer()

    def _current_profile_override(self) -> str:
        try:
            return self._container.settings_store.get("render_profile_override", _AUTO_PROFILE) or _AUTO_PROFILE
        except Exception:
            return _AUTO_PROFILE

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss()
            return
        if event.button.id != "apply":
            return

        theme_name = str(self.query_one("#theme-select", Select).value)
        try:
            select_theme(settings_store=self._container.settings_store, theme_name=theme_name)
            self.app.theme = theme_name
        except UnknownThemeError as e:
            self.app.notify(str(e), severity="error")
            return

        profile_value = str(self.query_one("#profile-select", Select).value)
        if profile_value == Select.BLANK:
            profile_value = _AUTO_PROFILE
        try:
            select_render_profile(settings_store=self._container.settings_store, profile_value=profile_value)
        except ValueError as e:
            self.app.notify(str(e), severity="error")
            return

        self.app.notify("Reglages enregistres.")
