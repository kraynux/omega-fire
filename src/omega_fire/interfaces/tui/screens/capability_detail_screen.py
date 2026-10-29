# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 1.2 (detail) — affiche les proprietes d'une capacite unique.
Logique identique a
interfaces/cli/renderers/capability_view.py::get_capability_detail :
identifiant, statut, raison, details techniques, dernier scan, directive
selon le statut (coloree via la palette d'extension omega-fire)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Static

from omega_fire.core.enums import CapabilityStatus
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.shared.i18n import _

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_DIRECTIVES: dict[CapabilityStatus, tuple[str, str]] = {
    CapabilityStatus.AVAILABLE: (
        _("Cette capacité est pleinement opérationnelle et disponible."), "status-available"
    ),
    CapabilityStatus.DEGRADED: (
        _("Capacité partiellement fonctionnelle. Vérifiez la configuration des dépendances."), "status-degraded"
    ),
    CapabilityStatus.MISSING: (
        _("Composant système manquant. Veuillez installer le package/outil requis."), "status-missing"
    ),
    CapabilityStatus.DISQUALIFIED: (
        _("Capacité disqualifiée par la politique système. Vérifiez les prérequis."), "status-disqualified"
    ),
}


class CapabilityDetailScreen(OmegaScreen):
    """Detail d'une capacite unique (poussee depuis CapabilityPickerScreen)."""

    def __init__(self, *, container: DependencyContainer, capability_id: str) -> None:
        super().__init__()
        self._container = container
        self._capability_id = capability_id

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="omega-panel"):
            yield Static(_("DÉTAIL D'UNE CAPACITÉ"), classes="omega-title")
            yield Static("", id="detail-body")
            with Horizontal(classes="omega-actions"), Container(classes="omega-btn-frame"):
                yield Button(_("Retour"), id="back")
        yield Footer()

    def on_mount(self) -> None:
        body = self.query_one("#detail-body", Static)
        cap = self._container.capability_registry.get(self._capability_id)
        if cap is None:
            body.update(_("Capacité '{capability_id}' introuvable dans le registre.").format(capability_id=self._capability_id))
            return

        lines = [
            _("[b]Identifiant :[/b] {value}").format(value=cap.id.upper()),
            _("[b]Statut actuel :[/b] {value}").format(value=cap.status.value.upper()),
        ]
        if cap.reason:
            lines.append(_("[b]Raison / cause :[/b] {reason}").format(reason=cap.reason))
        if cap.detail:
            lines.append(_("[b]Détails techniques :[/b] {detail}").format(detail=cap.detail))
        if cap.last_checked:
            dt = cap.last_checked.strftime("%Y-%m-%d %H:%M:%S") if hasattr(cap.last_checked, "strftime") else str(cap.last_checked)
            lines.append(_("[b]Dernier scan :[/b] {dt}").format(dt=dt))

        directive_text, variable = _DIRECTIVES.get(cap.status, ("", "foreground"))
        color = self.app.get_css_variables().get(variable, "")
        lines.append("")
        lines.append(f"[{color}]{directive_text}[/]" if color else directive_text)

        body.update("\n".join(lines))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss()
