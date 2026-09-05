# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran de section generique : un seul patron reutilise pour les 8
sections du menu (1 a 8), plutot que 8 fichiers quasi-identiques — meme
raison que CapabilitiesScreen pour 1.1/1.4. Chaque bouton correspond a un
SectionItem (voir section_registry.py) : soit un ecran deja migre
(`screen_factory`), soit une action directe sans formulaire
(`direct_action`, voir support/direct_actions.py), soit rien encore
(notify "pas encore migre", meme comportement que HomeScreen pour une
section entiere avant cet ecran)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static

from omega_fire.interfaces.cli.help_text import get_help_entry
from omega_fire.interfaces.tui.screens._base import OmegaScreen, format_help_entry
from omega_fire.interfaces.tui.screens.confirm import ConfirmScreen
from omega_fire.interfaces.tui.support.action_audit import log_action_result

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer


@dataclass(frozen=True)
class SectionItem:
    action_id: str  # ex. "1.1"
    label: str
    description: str
    screen_factory: Callable[["DependencyContainer"], Screen] | None = None
    direct_action: Callable[["DependencyContainer"], tuple[bool, str]] | None = None
    direct_action_title: str = ""
    # Si renseignes, direct_action passe d'abord par ConfirmScreen (patron
    # #1) avant d'executer — pour une action sans formulaire mais dont le
    # CLI actuel demande quand meme confirmation (ex. 1.3 Re-scanner).
    confirm_title: str = ""
    confirm_message: str = ""


def _widget_id(action_id: str) -> str:
    return f"action-{action_id.replace('.', '-')}"


class SectionScreen(OmegaScreen):
    """Sous-menu d'une section (ex. section "2" -> actions 2.1 a 2.10)."""

    def __init__(self, *, container: DependencyContainer, section_id: str, title: str, items: tuple[SectionItem, ...]) -> None:
        super().__init__()
        self._container = container
        self._section_id = section_id
        self._title = title
        self._items = items
        self._by_widget_id = {_widget_id(item.action_id): item for item in items}

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(classes="omega-panel omega-menu-panel"):
            yield Static(self._title, classes="omega-title")
            with Vertical(classes="omega-home-menu") as menu:
                for item in self._items:
                    with Container(classes="omega-btn-frame"):
                        yield Button(
                            f"{item.action_id}  {item.label}",
                            id=_widget_id(item.action_id),
                            tooltip=item.description or None,
                        )
                menu.border_title = f"SECTION {self._section_id}"
            with Horizontal(classes="omega-actions"), Container(classes="omega-btn-frame"):
                yield Button("Retour", id="back")
        yield Footer()

    def help_content(self) -> tuple[str, str]:
        # Aide COMPLETE de la section : la fiche detaillee de CHAQUE
        # action (interfaces/cli/help_text.py, meme contenu que le CLI),
        # pas seulement un resume d'une ligne — retour utilisateur reel,
        # l'aide par sous-section n'est consultable qu'APRES etre entre
        # dans son ecran (donc "trop tard" pour decider d'y entrer) tant
        # qu'on doit surligner un item pour voir son detail. Repli sur le
        # label/description court si aucune fiche n'a ete redigee pour
        # une action donnee — jamais une section entiere sans aucune aide.
        lines: list[str] = []
        section_entry = get_help_entry(self._section_id)
        if section_entry is not None:
            lines.append(format_help_entry(section_entry))
            lines.append("")
        lines.append("[b]Detail de chaque action :[/b]")
        for item in self._items:
            lines.append("")
            lines.append(f"[b]{item.action_id}  {item.label}[/b]")
            item_entry = get_help_entry(item.action_id)
            if item_entry is not None:
                lines.append(format_help_entry(item_entry))
            elif item.description:
                lines.append(item.description)
        return f"SECTION {self._section_id} — {self._title}", "\n".join(lines)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss()
            return
        item = self._by_widget_id.get(event.button.id or "")
        if item is None:
            return

        if item.screen_factory is not None:
            screen = item.screen_factory(self._container)
            if isinstance(screen, OmegaScreen):
                # Permet a OmegaScreen.help_content() (voir _base.py) de
                # retrouver l'aide detaillee de CETTE action precise sans
                # que chacun des ~52 ecrans d'action ait besoin de la
                # redefinir individuellement.
                screen.node_id = item.action_id
            self.app.push_screen(screen)
            return

        if item.direct_action is not None:
            if item.confirm_message:
                self.app.push_screen(
                    ConfirmScreen(title=item.confirm_title, message=item.confirm_message),
                    lambda confirmed: self._run_direct_action_if_confirmed(confirmed, item),
                )
                return
            self._run_direct_action(item)
            return

        self.app.notify(
            "Cet ecran n'est pas encore migre (voir la feuille de route, Phase 3).",
            title=item.action_id,
            severity="information",
        )

    def _run_direct_action_if_confirmed(self, confirmed: bool | None, item: SectionItem) -> None:
        if confirmed:
            self._run_direct_action(item)

    def _run_direct_action(self, item: SectionItem) -> None:
        assert item.direct_action is not None
        # Execute en arriere-plan (run_blocking) : direct_action() appelle
        # souvent fail2ban-client/subprocess/systemd (jusqu'a 10s de timeout
        # chacun) — en synchrone ici, ca gelerait TOUTE l'app le temps de
        # l'appel, pas seulement cet ecran (voir _base.py::run_blocking).
        def _execute() -> tuple[bool, str]:
            return item.direct_action(self._container)

        def _on_done(result: tuple[bool, str]) -> None:
            success, message = result
            self.app.notify(message, severity="information" if success else "error")
            log_action_result(
                self._container,
                item.direct_action_title or f"{item.action_id} {item.label}",
                status="success" if success else "failure",
                error=None if success else message,
            )

        def _on_error(error: Exception) -> None:
            self.app.notify(f"Echec de l'action : {error}", severity="error")
            log_action_result(
                self._container,
                item.direct_action_title or f"{item.action_id} {item.label}",
                status="failure",
                error=str(error),
            )

        self.run_blocking(
            _execute, _on_done,
            busy_message=f"{item.direct_action_title or item.label}...",
            on_error=_on_error,
        )
