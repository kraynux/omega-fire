# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Point d'entree Textual de l'application, cable par le composition root
(app/bootstrap.py). Adapte du patron app.py d'omega-check (D-008)."""
from __future__ import annotations

import logging
import os
from collections.abc import Iterable
from pathlib import PurePath
from typing import TYPE_CHECKING, ClassVar, cast

from omega_lib.i18n.policies import language_for
from omega_lib.terminal.models import RenderProfile
from omega_lib.theme.policies import TUI_THEMES
from textual.app import App, SystemCommand
from textual.binding import Binding, BindingType
from textual.notifications import SeverityLevel

from omega_fire.application.commands.select_language import (
    LANGUAGE_CHANGED_ENV_VAR,
    console_fallback_from,
)
from omega_fire.application.commands.select_theme import select_theme
from omega_fire.application.exceptions import UnknownThemeError
from omega_fire.application.queries.detect_terminal import detect_terminal
from omega_fire.interfaces.tui.controllers.startup_controller import (
    StartupState,
    resolve_startup_state,
)
from omega_fire.interfaces.tui.pending_interface_restart import PendingInterfaceRestart
from omega_fire.interfaces.tui.rendering.stylesheet_loader import load_paths_for
from omega_fire.interfaces.tui.rendering.textual_theme_builder import build_all_textual_themes
from omega_fire.interfaces.tui.screens.help_screen import HelpScreen
from omega_fire.interfaces.tui.screens.settings_screen import SettingsScreen
from omega_fire.interfaces.tui.screens.home import HomeScreen
from omega_fire.interfaces.tui.screens.language_changed_splash_screen import (
    LANGUAGE_LABEL,
    LanguageChangedSplashScreen,
)
from omega_fire.interfaces.tui.screens.quit_confirm import QuitConfirmScreen
from omega_fire.interfaces.tui.screens.scanning import ScanningScreen
from omega_fire.interfaces.tui.screens.splash import SplashScreen
from omega_fire.interfaces.tui.screens.terminal_warning import TerminalWarningScreen
from omega_fire.shared.i18n import STATE, _


def install_action_title_translator(container: DependencyContainer) -> None:
    """Titres de l'historique d'audit traduits a l'affichage (support/action_titles.py)."""
    from omega_fire.interfaces.tui.section_registry import AUDIT_TITLE_ALIASES, MENU_5_BEFORE_3_5, SECTIONS
    from omega_fire.interfaces.tui.support.action_titles import ActionTitleTranslator, menu_labels_by_action
    from omega_fire.shared.i18n import set_action_title_translator

    catalog = container.language_catalog
    set_action_title_translator(ActionTitleTranslator(
        menu_labels_by_action(SECTIONS), lambda: catalog.available().keys(), catalog.translated_phrases,
        renumbered=MENU_5_BEFORE_3_5, aliases=AUDIT_TITLE_ALIASES))

from omega_fire.core.constants import OMEGA_FIRE_VERSION

if TYPE_CHECKING:
    from textual.screen import Screen

    from omega_fire.app.dependency_container import DependencyContainer

TITLE = _("\U0001f6e1️ OMEGA-FIRE") + " " + _("version {version}").format(version=OMEGA_FIRE_VERSION)
"""Icone bouclier incluse DANS la chaine de titre (memes raisons que le
reste de la suite : HeaderIcon/HeaderTitle sont deux widgets Textual
distincts, les fondre dans une seule chaine les fait apparaitre comme une
unite)."""


class OmegaFireApp(App[None]):
    """Application TUI d'omega-fire : resout theme/profil de rendu au
    demarrage, puis enchaine splash -> (avertissement terminal) -> accueil."""

    TITLE = TITLE
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("q", "quit", _("Quitter"), show=True),
        Binding("ctrl+q", "quit", _("Quitter"), show=False),
        Binding("t", "cycle_theme", _("Thème suivant"), show=True),
        Binding("r", "refresh_terminal", _("Rafraîchir"), show=True),
        Binding("a", "help", _("Aide"), show=True),
        Binding("s", "open_settings", _("Réglages"), show=True),
    ]

    def __init__(self, container: DependencyContainer) -> None:
        self._container = container
        install_action_title_translator(container)
        self._startup_state = resolve_startup_state(
            terminal_detector=container.terminal_detector,
            settings_store=container.settings_store,
        )
        css_path = cast(
            "list[str | PurePath]", load_paths_for(self._startup_state.theme.render_profile)
        )
        super().__init__(css_path=css_path)
        for theme in build_all_textual_themes():
            self.register_theme(theme)
        self.theme = self._startup_state.theme.theme_name
        self.pending_restart: PendingInterfaceRestart | None = None
        """Deposee par l'ecran Reglages apres un changement de langue, lue par
        app/bootstrap.py::bootstrap_tui() apres App.run() (os.execv)."""

    def notify(
        self,
        message: str,
        *,
        title: str = "",
        severity: SeverityLevel = "information",
        timeout: float | None = None,
        markup: bool = False,
    ) -> None:
        """Meme signature que App.notify() - seul le defaut de `markup`
        change (True -> False).

        Retour utilisateur 2026-09-24 : crash reel et trace (var/logs/app.log,
        textual.markup.MarkupError) chaque fois qu'un ecran notifie un texte
        d'erreur contenant des crochets non intentionnels - `CoreError`
        (voir core/exceptions.py) en produisait via son propre contexte
        (corrige separement), mais des crochets natifs Python
        (`[Errno 2] No such file or directory`, `FileNotFoundError`/`OSError`)
        restent un risque identique pour N'IMPORTE QUEL futur appel
        `self.notify(f"...{e}...")` (~35 sites deja recenses dans
        interfaces/tui/screens/). Aucun de ces appels n'utilise
        intentionnellement de balisage Rich (verifie : zero occurrence de
        `[bold]`/`[red]`/etc. dans un notify() de ce projet) - desactiver le
        markup par defaut est donc sans effet visible sur les notifications
        existantes, seulement un filet de securite. Un appelant qui aurait
        reellement besoin de markup peut toujours passer `markup=True`
        explicitement."""
        super().notify(message, title=title, severity=severity, timeout=timeout, markup=markup)

    def on_mount(self) -> None:
        if os.environ.pop(LANGUAGE_CHANGED_ENV_VAR, None) is not None:
            self.push_screen(LanguageChangedSplashScreen(native_name=STATE.language.native_name), self._after_splash)
        else:
            self.push_screen(SplashScreen(), self._after_splash)

    def _notify_language_fallbacks(self) -> None:
        if STATE.fell_back_from is not None:
            self.notify(
                _("Langue « {code} » indisponible : interface en français.").format(code=STATE.fell_back_from),
                title=LANGUAGE_LABEL, severity="warning", timeout=10,
            )
        fallback_code = console_fallback_from()
        if fallback_code is not None:
            self.notify(
                _("Ce terminal (console texte) ne peut pas afficher la langue « {name} » : interface en anglais pour cette session. Le réglage est conservé - la langue revient dans un terminal graphique.").format(name=language_for(fallback_code).native_name),
                title=LANGUAGE_LABEL, severity="warning", timeout=15,
            )

    def _after_splash(self, _result: None) -> None:
        self._notify_language_fallbacks()
        terminal = self._startup_state.terminal
        too_small = (
            terminal.signals.columns < 80 or terminal.signals.rows < 24
        )
        if terminal.render_profile == RenderProfile.MONO or too_small:
            message = (
                _("Terminal détecté : {family} ({columns}x{rows}). Rendu appliqué : {value}.").format(family=terminal.signals.family, columns=terminal.signals.columns, rows=terminal.signals.rows, value=terminal.render_profile.value)
            )
            self.push_screen(TerminalWarningScreen(message=message), self._run_scan)
        else:
            self._run_scan(None)

    def _run_scan(self, _result: None) -> None:
        self.push_screen(ScanningScreen(container=self._container), self._show_home)

    def _show_home(self, _result: None) -> None:
        self.push_screen(HomeScreen(container=self._container))

    def watch_theme(self, _theme_name: str) -> None:
        terminal = self._startup_state.terminal
        self.sub_title = _("{theme} | {columns}x{rows}").format(theme=self.theme, columns=terminal.signals.columns, rows=terminal.signals.rows)

    async def action_quit(self) -> None:
        """Surcharge : demande confirmation avant de fermer."""
        self.push_screen(QuitConfirmScreen(), self._quit_if_confirmed)

    def _quit_if_confirmed(self, confirmed: bool | None) -> None:
        if confirmed:
            self.exit()

    def action_cycle_theme(self) -> None:
        """Touche `t` : bascule vers le theme SUIVANT du catalogue, sans
        confirmation."""
        names = list(TUI_THEMES.keys())
        current_index = names.index(self.theme) if self.theme in names else 0
        next_name = names[(current_index + 1) % len(names)]
        try:
            select_theme(settings_store=self._container.settings_store, theme_name=next_name)
        except UnknownThemeError as exc:
            self.notify(str(exc), severity="error")
            return
        except OSError as exc:
            # Retour utilisateur (GROS BUG : "t" fermait l'application) -
            # JsonSettingsStore.set() (infrastructure/storage/files/
            # json_settings_store.py) ecrit reellement sur disque
            # (var/runtime/settings.json) sans jamais etre protege ici -
            # une simple erreur de persistance (permissions, disque
            # plein, systeme de fichiers en lecture seule) faisait
            # planter cette action sans aucun rattrapage, plutot que de
            # se degrader en simple notification. Le theme change quand
            # meme visuellement (self.theme = next_name plus bas) : seule
            # la PERSISTANCE du choix echoue, pas la fonctionnalite
            # immediate.
            self.notify(_("Thème appliqué mais non enregistré : {exc}").format(exc=exc), severity="warning")
        self.theme = next_name

    def action_refresh_terminal(self) -> None:
        """Touche `r` : redetecte taille/famille du terminal et met a
        jour le sous-titre du Header."""
        terminal = detect_terminal(terminal_detector=self._container.terminal_detector)
        self._startup_state = StartupState(terminal=terminal, theme=self._startup_state.theme)
        self.sub_title = _("{theme} | {columns}x{rows}").format(theme=self.theme, columns=terminal.signals.columns, rows=terminal.signals.rows)
        self.notify(
            _("{family} ({columns}x{rows})").format(family=terminal.signals.family, columns=terminal.signals.columns, rows=terminal.signals.rows),
            title=_("Terminal rafraîchi"),
        )

    def action_help(self) -> None:
        current = self.screen
        context = current.help_content() if hasattr(current, "help_content") else None
        self.push_screen(HelpScreen(context=context))

    def action_open_guide(self) -> None:
        """Guide d'aide centralise (menu 10 AIDE), aussi propose depuis l'aide generique."""
        from omega_fire.interfaces.tui.screens.guide_screens import GuideMenuScreen
        self.push_screen(GuideMenuScreen(container=self._container))

    def action_open_settings(self) -> None:
        self.push_screen(SettingsScreen(container=self._container))

    def get_system_commands(self, screen: Screen) -> Iterable[SystemCommand]:
        """Remplace la liste par defaut de Textual plutot que d'appeler
        `super()` (meme raisonnement que le reste de la suite)."""
        yield SystemCommand(_("Thème"), _("Changer le thème actif"), self.action_change_theme)
        yield SystemCommand(
            _("Quitter"), _("Quitter l'application (avec confirmation)"), self.action_quit
        )
        yield SystemCommand(
            _("Capture d'écran"),
            _("Enregistrer une capture SVG de l'écran courant"),
            self._deliver_screenshot_to_configured_dir,
        )

    def _deliver_screenshot_to_configured_dir(self) -> None:
        directory = self._container.screenshots_dir
        directory.mkdir(parents=True, exist_ok=True)
        self.deliver_screenshot(path=str(directory))

    def _handle_exception(self, error: Exception) -> None:
        """Filet de securite unique cote TUI : toute exception technique
        non prevue est journalisee puis affichee comme notification,
        sans jamais fermer l'application."""
        logging.getLogger("omega_fire").error("Exception non prevue", exc_info=error)
        self.notify(
            str(error) or type(error).__name__,
            title=_("Erreur inattendue"),
            severity="error",
            timeout=10,
        )
