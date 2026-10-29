# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran affiche au lieu du splash normal quand l'interface vient d'etre relancee pour
appliquer une langue (OMEGA-FIRE_PLAN-DETAILLE_I18N.md §5, repris d'omega-serv) : le nom de
la langue et la phrase d'invite DEJA traduite sont la preuve visible que le changement est
applique. Meme interaction que le splash normal (touche ou clic, aucune temporisation)."""
from __future__ import annotations

from textual import events
from textual.app import ComposeResult
from textual.containers import Center, Middle
from textual.screen import Screen
from textual.widgets import Static

from omega_fire.interfaces.tui.widgets.splash_hero import SplashHero
from omega_fire.shared.i18n import _

LANGUAGE_LABEL = "Langue / Language"
"""Jamais traduit (plan §5) : reperable quelle que soit la langue affichee."""


class LanguageChangedSplashScreen(Screen[None]):
    def __init__(self, *, native_name: str) -> None:
        super().__init__()
        self._native_name = native_name

    def compose(self) -> ComposeResult:
        with Middle(classes="omega-splash-middle"):
            with Center():
                yield SplashHero()
            with Center():
                yield Static(f"{LANGUAGE_LABEL} : {self._native_name}", classes="omega-title", id="language-name")
            with Center():
                yield Static(_("Cliquez ou appuyez sur une touche pour continuer..."),
                             classes="omega-splash-prompt", id="language-prompt")

    def on_key(self, event: events.Key) -> None:
        event.stop()
        self.dismiss()

    def on_click(self, event: events.Click) -> None:
        event.stop()
        self.dismiss()
