# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran de demarrage : composition ASCII, se ferme sur une touche ou un clic.
Porte depuis omega-check (D-008), meme mecanisme que le reste de la
suite omega-*."""
from __future__ import annotations

from textual import events
from textual.app import ComposeResult
from textual.containers import Center, Middle
from textual.screen import Screen
from textual.widgets import Static

from omega_fire.interfaces.tui.widgets.splash_hero import SplashHero


class SplashScreen(Screen[None]):
    """Premier ecran affiche par app.py. Aucun appel a application/ ici :
    contenu statique. Pas de temporisation automatique : seule une action
    explicite (touche ou clic) fait passer a la suite."""

    def compose(self) -> ComposeResult:
        with Middle(classes="omega-splash-middle"):
            with Center():
                yield SplashHero()
            with Center():
                yield Static("Appuyez sur une touche pour continuer...", classes="omega-splash-prompt")

    def on_key(self, event: events.Key) -> None:
        event.stop()
        self.dismiss()

    def on_click(self, event: events.Click) -> None:
        event.stop()
        self.dismiss()
