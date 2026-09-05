# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran d'avertissement : terminal trop petit ou profil de rendu degrade.
Porte depuis omega-check (D-008), meme mecanisme que le reste de la
suite omega-*."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Center, Container, Horizontal, Middle
from textual.screen import Screen
from textual.widgets import Button, Static


class TerminalWarningScreen(Screen[None]):
    """Affiche avant HomeScreen quand le profil de rendu resolu est MONO,
    ou que la taille du terminal est sous le seuil minimal. Jamais un
    blocage, seulement un avis."""

    def __init__(self, *, message: str) -> None:
        super().__init__()
        self._message = message

    def compose(self) -> ComposeResult:
        with Middle(), Center():
            yield Static("TERMINAL LIMITE", classes="omega-title")
            yield Static(self._message, classes="omega-subtitle")
            with Horizontal(classes="omega-actions"), Container(classes="omega-btn-frame"):
                yield Button("Continuer quand meme", id="continue", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "continue":
            self.dismiss()
