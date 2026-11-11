# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Sources de logs proposees par les ecrans qui choisissent un log (2026-11-09, demande utilisateur :
« ce qu'il y a dans la Bibliotheque doit pouvoir alimenter tous les modules de selection de log »,
comme omega-serv et omega-log).

Ordre : logs de la Bibliotheque (5.1 : omega-serv detecte, epingles, copies SSH) en tete, puis les
epingles partagees des menus 2 / 4 / 5 / 6 (blocklists comprises) absentes de la Bibliotheque, puis
« Chemin manuel ». Jamais de doublon : un chemin present aux deux endroits n'apparait qu'une fois."""
from __future__ import annotations

from collections.abc import Iterable

from omega_fire.interfaces.tui.screens.log_library_screen import library_command
from omega_fire.shared.i18n import _


def library_paths() -> list[str]:
    """Chemins de la Bibliotheque, dans son ordre ; liste vide si elle est illisible."""
    try:
        return [record.path for record in library_command().records()]
    except (OSError, ValueError):
        return []


def log_source_options(pinned: Iterable[str], manual_value: str | None) -> list[tuple[str, str]]:
    """(libelle, valeur) pour un Select : Bibliotheque, puis epingles, puis « Chemin manuel » (si
    `manual_value` n'est pas None)."""
    seen: set[str] = set()
    options: list[tuple[str, str]] = []
    for path in [*library_paths(), *pinned]:
        if path and path not in seen:
            seen.add(path)
            options.append((path, path))
    if manual_value is not None:
        options.append((_("Chemin manuel"), manual_value))
    return options
