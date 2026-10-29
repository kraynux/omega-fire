# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Tableau des capacites systeme (menus 1.1/1.4). Colore chaque ligne par
statut via la palette d'extension omega-fire (theme_extensions.py,
Phase 0) — resolue a l'affichage via `App.get_css_variables()`, la seule
maniere de convertir un jeton CSS Textual ($status-available) en couleur
Rich concrete utilisable dans le contenu d'une cellule de DataTable (les
classes CSS ne s'appliquent qu'au widget entier, jamais par cellule)."""
from __future__ import annotations

from rich.text import Text
from textual.widgets import DataTable

from omega_fire.core.capability import Capability
from omega_fire.core.enums import CapabilityStatus
from omega_fire.shared.i18n import _

_STATUS_LABELS: dict[CapabilityStatus, str] = {
    CapabilityStatus.AVAILABLE: _("DISPONIBLE"),
    CapabilityStatus.DEGRADED: _("DÉGRADÉ"),
    CapabilityStatus.MISSING: _("MANQUANT"),
    CapabilityStatus.DISQUALIFIED: _("DISQUALIFIÉ"),
}

_STATUS_VARIABLE: dict[CapabilityStatus, str] = {
    CapabilityStatus.AVAILABLE: "status-available",
    CapabilityStatus.DEGRADED: "status-degraded",
    CapabilityStatus.MISSING: "status-missing",
    CapabilityStatus.DISQUALIFIED: "status-disqualified",
}


class CapabilitiesTable(DataTable[str]):
    """Une ligne par capacite systeme, statut colore."""

    def on_mount(self) -> None:
        self.cursor_type = "row"
        self.add_columns(_("Statut"), _("Capacité"), _("Raison"))

    def set_capabilities(self, capabilities: list[Capability]) -> None:
        self.clear()
        variables = self.app.get_css_variables()
        for cap in sorted(capabilities, key=lambda c: c.id):
            color = variables.get(_STATUS_VARIABLE[cap.status], "")
            badge = Text(_STATUS_LABELS[cap.status], style=f"bold {color}" if color else "bold")
            self.add_row(badge, cap.id.upper(), cap.reason or "—", key=cap.id)
