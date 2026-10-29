# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Modale de cases a cocher (version 3.5) : choisir plusieurs elements d'une liste —
presets de chemins a epingler (« Gérer les épingles »), IPs d'un export Top N a retirer
des logs (5.5). Meme style que ChoiceScreen ; retourne les valeurs cochees, ou None
(Annuler / echap)."""
from __future__ import annotations

from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, SelectionList, Static

from omega_fire.shared.i18n import _


class CheckListScreen(ModalScreen[list[str] | None]):
    """items : (libelle, valeur) ; checked : valeurs cochees a l'ouverture."""

    BINDINGS: ClassVar[list[BindingType]] = [Binding("escape", "back", _("Annuler"), show=True)]

    def __init__(self, *, title: str, message: str, items: list[tuple[str, str]],
                 checked: set[str] | None = None, confirm_label: str | None = None) -> None:
        super().__init__()
        self._title = title
        self._message = message
        self._items = items
        self._checked = checked or set()
        self._confirm_label = confirm_label or _("Valider")

    def compose(self) -> ComposeResult:
        with Vertical(classes="omega-confirm-box omega-choice-box"):
            yield Static(self._title, classes="omega-confirm-title omega-choice-title")
            yield Static(self._message, classes="omega-hint")
            yield SelectionList[str](
                *[(label, value, value in self._checked) for label, value in self._items],
                id="checklist",
            )
            with Horizontal(classes="omega-actions omega-checklist-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button(self._confirm_label, id="confirm", variant="primary")
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Tout cocher"), id="all")
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Annuler"), id="cancel")

    def on_mount(self) -> None:
        self.query_one("#checklist", SelectionList).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        checklist = self.query_one("#checklist", SelectionList)
        if event.button.id == "all":
            if len(checklist.selected) == len(self._items):
                checklist.deselect_all()
            else:
                checklist.select_all()
        elif event.button.id == "confirm":
            # Ordre de la liste (rang Top N), pas l'ordre des clics.
            selected = set(checklist.selected)
            self.dismiss([value for _label, value in self._items if value in selected])
        else:
            self.dismiss(None)

    def action_back(self) -> None:
        self.dismiss(None)
