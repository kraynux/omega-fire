# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran de gestion des modeles (presets) de jail, utilise par
CreateJailScreen (4.4, mode "Modele/Preset"). Meme patron liste + CRUD
que PinnedPathsScreen (Phase 2), avec un formulaire d'ajout a 8 champs
au lieu d'un seul. Logique identique au sous-menu presets de
interfaces/cli/actions.py::action_4_4_create_jail."""
from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, DataTable, Footer, Header, Input, Static

from omega_fire.application.commands.manage_jail_presets import ManageJailPresetsCommand
from omega_fire.infrastructure.config.paths import RUNTIME_DIR
from omega_fire.infrastructure.storage.files.json_store import JsonStore
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.screens.log_library_screen import scroll_panel_home
from omega_fire.shared.i18n import _

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_FIELDS: tuple[tuple[str, str, str], ...] = (
    ("name", _("Nom du preset (identifiant)"), _("ex. my-app-access")),
    ("desc", _("Description courte"), ""),
    ("log", _("Chemin du fichier de log"), ""),
    ("port", _("Port(s) cible(s)"), _("ex. http,https ou ssh")),
    ("filter", _("Nom du filtre Fail2ban"), ""),
    ("retry", _("Tentatives max"), "5"),
    ("find", _("Findtime"), "10m"),
    ("ban", _("Bantime"), "1h"),
)


class JailPresetsScreen(OmegaScreen):
    """Gestion des modeles de jail reutilisables (menu 4.4)."""

    # Retour utilisateur 2026-10-28 : les 11 modeles livres n'apparaissaient pas (donc
    # impossibles a retirer) — le 1fr commun aux DataTable ecrasait le tableau a une ligne
    # (l'en-tete) dans la zone qui defile. Hauteur naturelle, plafonnee ; Retour hors
    # defilement.
    CSS = """
    JailPresetsScreen #presets-table {
        height: auto;
        max-height: 14;
    }

    JailPresetsScreen #presets-actions {
        width: 100%;
        height: auto;
        align: center middle;
        margin: 0;
    }
    """

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container
        self._command = ManageJailPresetsCommand(JsonStore(RUNTIME_DIR))
        self._selected_name: str | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(classes="omega-panel"):
            yield Static(_("MODÈLES DE JAIL"), classes="omega-title")
            yield DataTable(id="presets-table")
            with Horizontal(classes="omega-actions"), Container(classes="omega-btn-frame"):
                yield Button(_("Retirer la sélection"), id="remove", variant="error")

            yield Static(_("Ajouter un modèle"), classes="omega-subtitle")
            for key, label, placeholder in _FIELDS:
                yield Static(label, classes="omega-hint")
                yield Input(placeholder=placeholder, id=f"field-{key}")

            with Horizontal(classes="omega-actions"), Container(classes="omega-btn-frame"):
                yield Button(_("Ajouter"), id="add", variant="primary")
        with Horizontal(classes="omega-actions", id="presets-actions"), Container(classes="omega-btn-frame"):
            yield Button(_("Retour"), id="back")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#presets-table", DataTable)
        table.cursor_type = "row"
        table.add_columns(_("Nom"), _("Description"))
        self._refresh()
        scroll_panel_home(self)

    def _refresh(self) -> None:
        table = self.query_one("#presets-table", DataTable)
        table.clear()
        for p in self._command.list_presets():
            # Description livree (N_ dans DEFAULT_JAIL_PRESETS) traduite a l'affichage ; le fichier
            # var/runtime/jail_presets.json garde le texte source, une description saisie reste telle quelle.
            table.add_row(p["name"], _(p["desc"]) if p["desc"] else "", key=p["name"])

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        self._selected_name = str(event.row_key.value)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss()
            return
        if event.button.id == "add":
            self._add_preset()
            return
        if event.button.id == "remove":
            self._remove_selected()

    def _add_preset(self) -> None:
        new_preset: dict[str, str] = {}
        for key, label, _ignored in _FIELDS:
            value = self.query_one(f"#field-{key}", Input).value.strip()
            if not value:
                self.app.notify(_("Champ requis : {label}.").format(label=label), severity="warning")
                return
            new_preset[key] = value

        result = self._command.add_preset(new_preset)
        if result.success:
            self.app.notify(result.message)
            for key, _ignored, _ignored in _FIELDS:
                self.query_one(f"#field-{key}", Input).value = ""
            self._refresh()
        else:
            self.app.notify(result.message, severity="error")

    def _remove_selected(self) -> None:
        if self._selected_name is None:
            self.app.notify(_("Sélectionnez d'abord une ligne."), severity="warning")
            return
        result = self._command.remove_preset(self._selected_name)
        if result.success:
            self.app.notify(result.message)
        else:
            self.app.notify(result.message, severity="error")
        self._selected_name = None
        self._refresh()
