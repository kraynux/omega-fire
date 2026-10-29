# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Libelles traduits des types d'export (infrastructure/exporters/export_catalog.py) et
mise en forme commune a 5.5 (charger une liste d'IPs) et 6.5 (voir tous les exports)."""
from __future__ import annotations

from datetime import datetime

from omega_fire.infrastructure.exporters.export_catalog import ExportFile
from omega_fire.interfaces.tui.screens.log_library_screen import format_size
from omega_fire.shared.i18n import _


def kind_label(kind: str) -> str:
    labels = {
        "top_ips": _("Top IPs (5.4)"),
        "blacklist": _("Blacklist (6.1)"),
        "rules": _("Règles (6.2)"),
        "audit": _("Audit (6.3)"),
        "f2b": _("Fail2Ban (6.4)"),
        "jail": _("Jail (4.8)"),
        "state": _("État système"),
        "stats": _("Statistiques"),
        "conntrack": _("Conntrack"),
        "guide": _("Guide d'aide (10)"),
    }
    return labels.get(kind, _("Autre"))


def export_row(export: ExportFile) -> tuple[str, str, str, str]:
    """(type, nom, date, taille) pour un DataTable."""
    when = datetime.fromtimestamp(export.mtime).strftime("%Y-%m-%d %H:%M")
    return kind_label(export.kind), export.path.name, when, format_size(export.size)
