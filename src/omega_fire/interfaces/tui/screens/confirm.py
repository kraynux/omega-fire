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
from omega_fire.shared.i18n import _


class ConfirmScreen(ModalScreen[bool]):
    """Retourne True si confirme, False/None sinon. N'herite pas de
    OmegaScreen : `echap` doit annuler, pas dismiss(None) sans valeur."""

    BINDINGS: ClassVar[list[BindingType]] = [Binding("escape", "back", _("Annuler"), show=True)]

    def __init__(self, *, title: str, message: str, help_node: str | None = None) -> None:
        super().__init__()
        self._title = title
        self._message = message
        self._help_node = help_node

    def help_content(self) -> tuple[str, str] | None:
        """Touche `a` depuis la modale : aide de l'action qui l'a ouverte (help_node),
        dont le message renvoie aux consequences detaillees."""
        if not self._help_node:
            return None
        from omega_fire.interfaces.cli.help_text import get_help_entry
        from omega_fire.interfaces.tui.screens._base import format_help_entry

        entry = get_help_entry(self._help_node)
        if entry is None:
            return None
        return _("Action {node_id}").format(node_id=self._help_node), format_help_entry(entry)

    def compose(self) -> ComposeResult:
        with Middle(), Center(), Vertical(classes="omega-confirm-box"):
            yield Static(self._title, classes="omega-confirm-title")
            yield Static(self._message)
            with Horizontal(classes="omega-confirm-buttons"):
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Confirmer"), id="confirm", variant="error")
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Annuler"), id="cancel", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm")

    def action_back(self) -> None:
        self.dismiss(False)
