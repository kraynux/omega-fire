# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Modale de confirmation generique (purges/suppressions irreversibles,
etc. — reutilisee par toutes les actions destructives de la Phase 3).
Portee depuis omega-check (D-008), meme mecanisme que le reste de la
suite omega-*."""
from __future__ import annotations

from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Center, Container, Horizontal, Middle, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static


class ConfirmScreen(ModalScreen[bool]):
    """Retourne True si confirme, False/None sinon. N'herite pas de
    OmegaScreen : `echap` doit annuler, pas dismiss(None) sans valeur."""

    BINDINGS: ClassVar[list[BindingType]] = [Binding("escape", "back", "Annuler", show=True)]

    def __init__(self, *, title: str, message: str) -> None:
        super().__init__()
        self._title = title
        self._message = message

    def compose(self) -> ComposeResult:
        with Middle(), Center(), Vertical(classes="omega-confirm-box"):
            yield Static(self._title, classes="omega-confirm-title")
            yield Static(self._message)
            with Horizontal(classes="omega-confirm-buttons"):
                with Container(classes="omega-btn-frame"):
                    yield Button("Confirmer", id="confirm", variant="error")
                with Container(classes="omega-btn-frame"):
                    yield Button("Annuler", id="cancel", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm")

    def action_back(self) -> None:
        self.dismiss(False)
