# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran d'accueil : menu principal vers les 8 sections + Quitter. Adapte
du patron screens/home.py d'omega-check (D-008) — a la difference de
CHECK (actions independantes), les items pointent vers des SECTIONS de
menu (1-8), chacune peuplee action par action en Phase 3 de la feuille de
route. Tant qu'une section n'a pas encore d'ecran (avant sa vague dans la
Phase 3), le clic notifie plutot que d'echouer silencieusement."""
from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Center, Container, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header

from omega_fire.interfaces.cli.renderers.icons import menu_icon
from omega_fire.interfaces.tui.screens.quit_confirm import QuitConfirmScreen
from omega_fire.interfaces.tui.screens.section_screen import SectionScreen
from omega_fire.interfaces.tui.screens.settings_screen import SettingsScreen
from omega_fire.interfaces.tui.section_registry import SECTIONS
from omega_fire.interfaces.tui.widgets.home_wordmark import HomeWordmark

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

# Designations reprises de menu_builder.py (sans la precision entre
# parentheses, trop longue pour un bouton — voir `description` du node
# pour cette precision). Quitter n'est PAS un bouton ici : deja
# accessible par raccourci global (footer, voir app.py — `q`), un
# doublon dans la liste n'apportait rien (retour utilisateur reel).
# Reglages (9) EST un bouton malgre le raccourci global (`s`) : retire
# une premiere fois pour la meme raison que Quitter, mais le raccourci
# seul le rendait introuvable sans le savoir a l'avance — retour
# utilisateur reel ("Menu reglages a disparu").
_MENU_ITEMS: tuple[tuple[str, str], ...] = (
    ("1", "ÉTAT DES CAPACITÉS & DIAGNOSTICS"),
    ("2", "GESTION DES IPs"),
    ("3", "GESTION DES RÈGLES"),
    ("4", "GESTION FAIL2BAN"),
    ("5", "GESTION DES LOGS"),
    ("6", "EXPORTS & RAPPORTS"),
    ("7", "SYSTÈME & PERSISTANCE"),
    ("8", "MONITORING & STATISTIQUES"),
    ("9", "RÉGLAGES"),
)

_SETTINGS_ITEM_ID = "9"


def _widget_id(item_id: str) -> str:
    """Textual interdit les id de widget commencant par un chiffre — les
    section id ("1".."8") sont donc prefixes uniquement pour le widget,
    jamais utilises tels quels ailleurs (menu_builder.py garde "1".."8")."""
    return f"section-{item_id}" if item_id.isdigit() else item_id


def _section_id(widget_id: str | None) -> str | None:
    if widget_id and widget_id.startswith("section-"):
        return widget_id.removeprefix("section-")
    return widget_id


class HomeScreen(Screen[None]):
    """Menu principal, racine de la pile de navigation. N'herite pas de
    OmegaScreen : `echap` ici demande confirmation de sortie, pas un
    dismiss() (rien "en dessous" de cet ecran)."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "back", "Retour", show=True),
        Binding("up", "focus_previous_item", "Monter", show=False),
        Binding("down", "focus_next_item", "Descendre", show=False),
    ]

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="omega-home-root"):
            with Center():
                yield HomeWordmark()
            with Center():
                with Vertical(classes="omega-home-menu") as menu:
                    for item_id, label in _MENU_ITEMS:
                        # "9" (Reglages) n'est pas une section du CLI d'origine,
                        # menu_icon() n'a donc pas d'entree pour elle (renverrait
                        # le repli "[?]") - icone dediee au lieu d'emprunter celle
                        # (deja utilisee) de la section 3.
                        icon = "⚙" if item_id == _SETTINGS_ITEM_ID else menu_icon(item_id)
                        with Container(classes="omega-btn-frame"):
                            yield Button(f"{item_id}. {icon} {label}", id=_widget_id(item_id))
                menu.border_title = "MENU PRINCIPAL"
        yield Footer()

    def help_content(self) -> tuple[str, str]:
        return (
            "MENU PRINCIPAL",
            "Choisissez une section (1-8) ou Reglages (9). Quitter (`q`) "
            "est accessible par raccourci global, voir le pied d'ecran. "
            "Appuyez sur `a` a nouveau dans une section pour voir le detail "
            "des actions qu'elle contient.",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        section_id = _section_id(event.button.id)
        if section_id == _SETTINGS_ITEM_ID:
            self.app.push_screen(SettingsScreen(container=self._container))
            return
        screen = self._screen_for(section_id)
        if screen is not None:
            self.app.push_screen(screen)
        else:
            self.app.notify(
                "Cet ecran n'est pas encore migre (voir la feuille de route, Phase 3).",
                title=f"Section {section_id}",
                severity="information",
            )

    def action_back(self) -> None:
        self.app.push_screen(QuitConfirmScreen(), self._quit_if_confirmed)

    def action_focus_previous_item(self) -> None:
        self.focus_previous()

    def action_focus_next_item(self) -> None:
        self.focus_next()

    def _quit_if_confirmed(self, confirmed: bool | None) -> None:
        if confirmed:
            self.app.exit()

    def _screen_for(self, item_id: str | None) -> Screen[None] | None:
        section = SECTIONS.get(item_id or "")
        if section is None:
            return None
        title, items = section
        return SectionScreen(container=self._container, section_id=item_id, title=title, items=items)
