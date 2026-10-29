# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran REGLAGES (accessible depuis l'accueil, hors des 8 sections du
CLI — le CLI n'avait qu'un cycle de theme a la touche 't', pas d'ecran
dedie). Regroupe : langue de l'interface (plan i18n, lot 2 : changement
applique par redemarrage de l'interface), langue des exports (lot N), dossiers d'exports et de captures
d'ecran modifiables avec leur vidage (comme le reste de la suite omega-*), choix du theme (parmi les 10 themes omega-*, pas les
themes Textual natifs — voir la note de base.tcss sur les variables
d'extension), et surcharge du profil de rendu (ou retour a la detection
automatique). Retour utilisateur reel : demande explicite d'un vrai
ecran de reglages plutot que de ne dependre que de la touche 't'."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, cast

from omega_lib.i18n.models import LanguageStatus
from omega_lib.i18n.policies import PSEUDO_LANGUAGE_CODE
from omega_lib.terminal.models import RenderProfile
from omega_lib.theme.policies import TUI_THEMES
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Input, Select, Static

from omega_fire.application.commands.clear_directory import ClearResult, clear_directory
from omega_fire.application.commands.select_language import (
    EXPORT_LANGUAGE_KEY,
    available_languages,
    select_export_language,
    select_language,
)
from omega_fire.application.commands.select_render_profile import select_render_profile
from omega_fire.application.commands.select_theme import select_theme
from omega_fire.application.exceptions import UnknownLanguageError, UnknownThemeError
from omega_fire.interfaces.tui.pending_interface_restart import PendingInterfaceRestart
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.screens.confirm import ConfirmScreen
from omega_fire.interfaces.tui.screens.language_changed_splash_screen import LANGUAGE_LABEL
from omega_fire.shared.i18n import STATE, _

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer
    from omega_fire.interfaces.tui.app import OmegaFireApp
    from omega_fire.ports.language_catalog import LanguageCatalogPort

_EXPORTS_DIR_KEY = "exports_dir_override"
_SCREENSHOTS_DIR_KEY = "screenshots_dir_override"
_AUTO_PROFILE = ""
_EXPORT_LIKE_INTERFACE = "__interface__"
_PROFILE_LABELS: dict[str, str] = {
    _AUTO_PROFILE: _("Automatique (détection terminal)"),
    RenderProfile.COMPLETE.value: _("Complet"),
    RenderProfile.STANDARD.value: _("Standard"),
    RenderProfile.REDUCED.value: _("Réduit"),
    RenderProfile.MONO.value: _("Mono (ASCII seul)"),
}


def language_options(catalog: LanguageCatalogPort) -> list[tuple[str, str]]:
    """Libelles du selecteur de langue : chaque langue dans SA langue, « Français » toujours
    en tete (omega-lib), mention « en test » tant qu'une langue n'est pas validee."""
    options: list[tuple[str, str]] = []
    for language in available_languages(catalog):
        label = language.native_name
        if language.status is LanguageStatus.TESTING and language.code != PSEUDO_LANGUAGE_CODE:
            label = _("{label} ({value})").format(label=label, value=_("en test"))
        options.append((label, language.code))
    return options


class SettingsScreen(OmegaScreen):
    """Theme actif et surcharge du profil de rendu."""

    CSS = """
    /* Barre Appliquer / Retour sous la zone qui defile (.omega-form-panel, height 1fr) et
       au-dessus du pied de page : toujours visible, meme en 80x24 quand la liste des
       reglages depasse la hauteur (retour utilisateur 2026-10-27 : les boutons
       disparaissaient sous le choix de la langue). */
    SettingsScreen #settings-actions {
        width: 100%;
        height: auto;
        align: center middle;
        margin: 0;
    }
    """

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="omega-form-panel"):
            yield Static(_("RÉGLAGES"), classes="omega-title")

            yield Static(_("Thème"), classes="omega-subtitle")
            yield Select(
                [(name, name) for name in TUI_THEMES.keys()],
                value=self.app.theme if self.app.theme in TUI_THEMES else next(iter(TUI_THEMES)),
                id="theme-select",
            )

            yield Static(_("Profil de rendu"), classes="omega-subtitle")
            yield Select(
                [(label, value) for value, label in _PROFILE_LABELS.items()],
                value=self._current_profile_override(),
                id="profile-select",
            )
            yield Static(
                _("Le profil de rendu détermine la complexité visuelle (bordures, splash) "
                "selon les capacités du terminal — un changement ici prend effet au prochain lancement."),
                classes="omega-hint",
            )

            # Sous le profil de rendu, comme omega-serv : theme et rendu vont ensemble
            # (terminal), la langue vient apres. Libelle bilingue jamais traduit.
            yield Static(LANGUAGE_LABEL, classes="omega-subtitle")
            yield Select(
                language_options(self._container.language_catalog),
                value=STATE.language.code,
                allow_blank=False,
                id="language-select",
            )

            yield Static(_("Exports"), classes="omega-subtitle")
            yield Input(value=self._dir_value(_EXPORTS_DIR_KEY, self._container.default_exports_dir),
                        placeholder="var/exports", id="exports-dir-input")

            # Langue des exports HTML/TXT (lot N, comme omega-serv) : un rapport se diffuse,
            # sa langue n'est pas forcement celle de l'interface. Enregistree par Appliquer.
            yield Static(_("Langue des exports"), classes="omega-subtitle")
            yield Select(
                [(_("Comme l'interface"), _EXPORT_LIKE_INTERFACE)] + language_options(self._container.language_catalog),
                value=self._export_language_value(),
                allow_blank=False,
                id="export-language-select",
            )

            yield Static(_("Captures d'écran"), classes="omega-subtitle")
            yield Input(value=self._dir_value(_SCREENSHOTS_DIR_KEY, self._container.default_screenshots_dir),
                        placeholder="var/screenshots", id="screenshots-dir-input")

            yield Static(_("Purge"), classes="omega-subtitle")
            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Vider les exports"), id="clear-exports", variant="error")
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Vider les captures"), id="clear-screenshots", variant="error")
        with Horizontal(classes="omega-actions", id="settings-actions"):
            with Container(classes="omega-btn-frame"):
                yield Button(_("Appliquer"), id="apply", variant="primary")
            with Container(classes="omega-btn-frame"):
                yield Button(_("Retour"), id="back")
        yield Footer()

    def _dir_value(self, key: str, default: Path) -> str:
        """Chemin enregistre, sinon le dossier par defaut ecrit depuis la racine du projet
        (var/exports, var/screenshots) : plus lisible qu'un chemin absolu coupe."""
        try:
            stored = self._container.settings_store.get(key, "") or ""
        except (OSError, ValueError):
            stored = ""
        if stored:
            return stored
        try:
            return str(default.relative_to(self._container.project_root))
        except ValueError:
            return str(default)

    def _export_language_value(self) -> str:
        try:
            stored = self._container.settings_store.get(EXPORT_LANGUAGE_KEY, "") or ""
        except (OSError, ValueError):
            stored = ""
        offered = {language.code for language in available_languages(self._container.language_catalog)}
        return stored if stored in offered else _EXPORT_LIKE_INTERFACE

    def _typed_dir(self, input_id: str, default: Path) -> Path:
        """Dossier saisi dans le champ (vide = dossier par defaut ; relatif = depuis la racine
        du projet, comme DependencyContainer.exports_dir)."""
        typed = self.query_one(f"#{input_id}", Input).value.strip()
        if not typed:
            return default
        path = Path(typed).expanduser()
        return path if path.is_absolute() else self._container.project_root / path

    def _save_dirs(self) -> None:
        for key, input_id, default in (
            (_EXPORTS_DIR_KEY, "exports-dir-input", self._container.default_exports_dir),
            (_SCREENSHOTS_DIR_KEY, "screenshots-dir-input", self._container.default_screenshots_dir),
        ):
            typed = self.query_one(f"#{input_id}", Input).value.strip()
            # Le dossier par defaut n'est pas enregistre : il suit l'installation si elle bouge.
            is_default = not typed or self._typed_dir(input_id, default).resolve() == default.resolve()
            self._container.settings_store.set(key, "" if is_default else typed)

    def _confirm_clear(self, input_id: str, default: Path, title: str) -> None:
        directory = self._typed_dir(input_id, default)
        self.app.push_screen(
            ConfirmScreen(
                title=title,
                message=_("Tout le contenu de ce dossier sera définitivement supprimé :\n{directory}").format(directory=directory),
            ),
            lambda confirmed: self._clear_if_confirmed(directory, confirmed),
        )

    def _clear_if_confirmed(self, directory: Path, confirmed: bool | None) -> None:
        if not confirmed:
            return
        # Dans un thread : un gros dossier ne doit jamais figer l'interface pendant la suppression.
        self.run_blocking(
            lambda: clear_directory(directory, self._container.project_root),
            self._on_cleared,
            busy_message=_("Suppression en cours..."),
            on_error=lambda exc: self.app.notify(str(exc), severity="error", timeout=10),
        )

    def _on_cleared(self, result: ClearResult) -> None:
        if not result.failed:
            self.app.notify(_("{removed} élément(s) supprimé(s) : {directory}").format(removed=result.removed, directory=result.directory))
            return
        shown = ", ".join(result.failed[:3]) + (" ..." if len(result.failed) > 3 else "")
        self.app.notify(
            _("{removed} élément(s) supprimé(s), {count} impossible(s) à supprimer : {shown}").format(removed=result.removed, count=len(result.failed), shown=shown),
            severity="warning", timeout=15,
        )

    def _current_profile_override(self) -> str:
        try:
            return self._container.settings_store.get("render_profile_override", _AUTO_PROFILE) or _AUTO_PROFILE
        except Exception:
            return _AUTO_PROFILE

    def on_select_changed(self, event: Select.Changed) -> None:
        """La langue s'applique des qu'elle est choisie (apres confirmation), independamment
        du bouton Appliquer : elle demande un redemarrage de l'interface."""
        if event.select.id != "language-select" or str(event.value) == STATE.language.code:
            return
        self._confirm_language(str(event.value))

    def _confirm_language(self, code: str) -> None:
        names = {language.code: language.native_name
                 for language in available_languages(self._container.language_catalog)}
        self.app.push_screen(
            ConfirmScreen(
                title=_("REDÉMARRER L'INTERFACE ?"),
                message=_(
                    "La langue « {name} » sera appliquée après le redémarrage de l'interface. "
                    "Les règles du pare-feu, fail2ban et les services ne sont pas touchés."
                ).format(name=names.get(code, code)),
            ),
            lambda confirmed: self._restart_for_language(code, confirmed),
        )

    def _restore_language_select(self) -> None:
        self.query_one("#language-select", Select).value = STATE.language.code

    def _restart_for_language(self, code: str, confirmed: bool | None) -> None:
        if not confirmed:
            self._restore_language_select()
            return
        try:
            select_language(settings_store=self._container.settings_store,
                            catalog=self._container.language_catalog, language_code=code)
        except (UnknownLanguageError, OSError) as exc:
            self.app.notify(str(exc), title=LANGUAGE_LABEL, severity="error")
            self._restore_language_select()
            return
        cast("OmegaFireApp", self.app).pending_restart = PendingInterfaceRestart(language_code=code)
        self.app.exit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss()
            return
        if event.button.id == "clear-exports":
            self._confirm_clear("exports-dir-input", self._container.default_exports_dir, _("VIDER LE DOSSIER D'EXPORTS ?"))
            return
        if event.button.id == "clear-screenshots":
            self._confirm_clear("screenshots-dir-input", self._container.default_screenshots_dir,
                                _("VIDER LE DOSSIER DE CAPTURES ?"))
            return
        if event.button.id != "apply":
            return

        theme_name = str(self.query_one("#theme-select", Select).value)
        try:
            select_theme(settings_store=self._container.settings_store, theme_name=theme_name)
            self.app.theme = theme_name
        except UnknownThemeError as e:
            self.app.notify(str(e), severity="error")
            return

        profile_value = str(self.query_one("#profile-select", Select).value)
        if profile_value == Select.BLANK:
            profile_value = _AUTO_PROFILE
        try:
            select_render_profile(settings_store=self._container.settings_store, profile_value=profile_value)
        except ValueError as e:
            self.app.notify(str(e), severity="error")
            return

        try:
            self._save_dirs()
        except OSError as e:
            self.app.notify(_("Dossiers non enregistrés : {e}").format(e=e), severity="error")
            return

        export_value = str(self.query_one("#export-language-select", Select).value)
        try:
            select_export_language(
                settings_store=self._container.settings_store, catalog=self._container.language_catalog,
                language_code="" if export_value == _EXPORT_LIKE_INTERFACE else export_value,
            )
        except (UnknownLanguageError, OSError) as e:
            self.app.notify(str(e), severity="error")
            return

        self.app.notify(_("Réglages enregistrés."))
