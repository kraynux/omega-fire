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

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_DIRECTIVES: dict[CapabilityStatus, tuple[str, str]] = {
    CapabilityStatus.AVAILABLE: (
        "Cette capacite est pleinement operationnelle et disponible.", "status-available"
    ),
    CapabilityStatus.DEGRADED: (
        "Capacite partiellement fonctionnelle. Verifiez la configuration des dependances.", "status-degraded"
    ),
    CapabilityStatus.MISSING: (
        "Composant systeme manquant. Veuillez installer le package/outil requis.", "status-missing"
    ),
    CapabilityStatus.DISQUALIFIED: (
        "Capacite disqualifiee par la politique systeme. Verifiez les prerequis.", "status-disqualified"
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
            yield Static("DETAIL D'UNE CAPACITE", classes="omega-title")
            yield Static("", id="detail-body")
            with Horizontal(classes="omega-actions"), Container(classes="omega-btn-frame"):
                yield Button("Retour", id="back")
        yield Footer()

    def on_mount(self) -> None:
        body = self.query_one("#detail-body", Static)
        cap = self._container.capability_registry.get(self._capability_id)
        if cap is None:
            body.update(f"Capacite '{self._capability_id}' introuvable dans le registre.")
            return

        lines = [
            f"[b]Identifiant :[/b] {cap.id.upper()}",
            f"[b]Statut actuel :[/b] {cap.status.value.upper()}",
        ]
        if cap.reason:
            lines.append(f"[b]Raison / cause :[/b] {cap.reason}")
        if cap.detail:
            lines.append(f"[b]Details techniques :[/b] {cap.detail}")
        if cap.last_checked:
            dt = cap.last_checked.strftime("%Y-%m-%d %H:%M:%S") if hasattr(cap.last_checked, "strftime") else str(cap.last_checked)
            lines.append(f"[b]Dernier scan :[/b] {dt}")

        directive_text, variable = _DIRECTIVES.get(cap.status, ("", "foreground"))
        color = self.app.get_css_variables().get(variable, "")
        lines.append("")
        lines.append(f"[{color}]{directive_text}[/]" if color else directive_text)

        body.update("\n".join(lines))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss()
