# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Modale de choix entre plusieurs options (retour utilisateur 2026-10-28 : avant de
vider un backend qui porte aussi les regles d'un autre outil, l'utilisateur choisit —
tout appliquer, seulement nftables, ou annuler). Meme style que ConfirmScreen ; les
options sont empilees (libelles longs, traduits), le message defile si besoin."""
from __future__ import annotations

from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Container, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from omega_fire.shared.i18n import _


class ChoiceScreen(ModalScreen[str | None]):
    """Retourne l'identifiant de l'option choisie, ou None (Annuler / echap)."""

    BINDINGS: ClassVar[list[BindingType]] = [Binding("escape", "back", _("Annuler"), show=True)]

    def __init__(self, *, title: str, message: str, choices: list[tuple[str, str, str]],
                 help_node: str | None = None) -> None:
        """choices : (libelle, identifiant, variante du bouton : error / warning / primary).
        help_node : action dont l'aide s'ouvre avec la touche `a`."""
        super().__init__()
        self._title = title
        self._message = message
        self._choices = choices
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
        with Vertical(classes="omega-confirm-box omega-choice-box"):
            yield Static(self._title, classes="omega-confirm-title omega-choice-title")
            with VerticalScroll(classes="omega-choice-message"):
                yield Static(self._message)
            with Vertical(classes="omega-choice-buttons"):
                for label, choice_id, variant in self._choices:
                    with Container(classes="omega-btn-frame"):
                        yield Button(label, id=f"choice-{choice_id}", variant=variant)
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Annuler"), id="cancel", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id or ""
        self.dismiss(button_id.removeprefix("choice-") if button_id.startswith("choice-") else None)

    def action_back(self) -> None:
        self.dismiss(None)
