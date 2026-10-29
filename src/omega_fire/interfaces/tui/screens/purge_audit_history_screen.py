# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Sous-ecran de gestion/purge du journal d'audit (bouton 'Gerer/Purger'
de l'ecran 7.3). Meme 4 modes que action_7_3_action_history::_do_purge_menu
(30 jours / 120 jours / date precise / N entrees les plus anciennes),
formulaire a champs conditionnels (patron #3) au lieu du sous-menu
numerote du CLI, confirmation via ConfirmScreen avant toute suppression
(irreversible, meme raison que le reste de l'appli)."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Input, Select, Static

from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.screens.confirm import ConfirmScreen
from omega_fire.interfaces.tui.support.action_audit import log_action_result
from omega_fire.shared.i18n import _

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ACTION_TITLE = "7.3 Gestion du journal d'audit"


class PurgeAuditHistoryScreen(OmegaScreen):
    """Purge du journal d'audit selon 4 modes (patron #3)."""

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container
        self._pending: dict | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="omega-form-panel"):
            yield Static(_("GESTION DU JOURNAL D'AUDIT"), classes="omega-title")
            yield Static(
                _("Choisissez un mode de purge. Opération irréversible, confirmation demandée."),
                classes="omega-hint",
            )
            yield Select(
                [
                    (_("Plus de 30 jours"), "30d"),
                    (_("Plus de 120 jours"), "120d"),
                    (_("Date précise"), "date"),
                    (_("N entrées les plus anciennes"), "count"),
                ],
                value="30d",
                id="mode-select",
            )
            yield Input(placeholder=_("Date limite (JJ/MM/AAAA)"), id="date-input", classes="omega-hidden")
            yield Input(placeholder=_("Nombre d'entrées les plus anciennes à supprimer"), id="count-input", classes="omega-hidden")
            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Supprimer"), id="launch", variant="error")
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Retour"), id="back")
        yield Footer()

    def on_mount(self) -> None:
        self._sync_conditional_fields()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "mode-select":
            self._sync_conditional_fields()

    def _sync_conditional_fields(self) -> None:
        mode = self.query_one("#mode-select", Select).value
        self.query_one("#date-input", Input).set_class(mode != "date", "omega-hidden")
        self.query_one("#count-input", Input).set_class(mode != "count", "omega-hidden")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss()
            return
        if event.button.id == "launch":
            self._validate_and_confirm()

    def _validate_and_confirm(self) -> None:
        mode = self.query_one("#mode-select", Select).value

        older_than = None
        count = None
        removal_label = ""

        if mode == "30d":
            older_than = datetime.now() - timedelta(days=30)
            removal_label = _("les entrées de plus de 30 jours")
        elif mode == "120d":
            older_than = datetime.now() - timedelta(days=120)
            removal_label = _("les entrées de plus de 120 jours")
        elif mode == "date":
            raw_date = self.query_one("#date-input", Input).value.strip()
            if not raw_date:
                self.app.notify(_("Saisissez une date limite."), severity="warning")
                return
            try:
                older_than = datetime.strptime(raw_date, "%d/%m/%Y")
            except ValueError:
                self.app.notify(_("Format de date invalide (attendu : JJ/MM/AAAA)."), severity="error")
                return
            removal_label = _("les entrées antérieures au {raw_date}").format(raw_date=raw_date)
        elif mode == "count":
            raw_count = self.query_one("#count-input", Input).value.strip()
            if not raw_count.isdigit() or int(raw_count) <= 0:
                self.app.notify(_("Nombre invalide."), severity="warning")
                return
            count = int(raw_count)
            removal_label = _("les {count} entrées d'audit les plus anciennes").format(count=count)

        self._pending = {"mode": mode, "older_than": older_than, "count": count}
        self.app.push_screen(
            ConfirmScreen(title=_("CONFIRMER LA SUPPRESSION"), message=_("Vous allez supprimer {removal_label}.").format(removal_label=removal_label)),
            self._delete_if_confirmed,
        )

    def _delete_if_confirmed(self, confirmed: bool | None) -> None:
        if not confirmed or self._pending is None:
            self._pending = None
            return

        try:
            audit_port = self._container.get_audit_port()
        except Exception as e:
            self.app.notify(_("Registre d'audit indisponible : {e}").format(e=e), severity="error")
            self._pending = None
            return

        try:
            if self._pending["mode"] == "count":
                removed = audit_port.delete_oldest(self._pending["count"])
            else:
                removed = audit_port.clear(older_than=self._pending["older_than"])
        except Exception as e:
            self.app.notify(_("Erreur lors de la suppression : {e}").format(e=e), severity="error")
            log_action_result(self._container, _ACTION_TITLE, status="failure", error=str(e))
            self._pending = None
            return

        self.app.notify(_("{removed} entrée(s) supprimée(s).").format(removed=removed))
        log_action_result(self._container, _ACTION_TITLE, status="success")
        self._pending = None
        self.dismiss()
