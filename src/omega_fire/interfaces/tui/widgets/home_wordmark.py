# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Bandeau texte OMEGA-FIRE affiche en haut de screens/home.py — repris
tel quel de interfaces/cli/app.py::MAIN_MENU_LOGO_LINES (meme banniere
que le menu principal Rich actuel, caracteres non modifies). Couleur par
jetons de theme Rich/Textual (`$accent`/`$foreground`) directement dans
le markup — pas des couleurs hex figees a la construction (meme
mecanisme que widgets/splash_hero.py : reactif au changement de theme),
meme technique que omega-check/widgets/home_wordmark.py (D-008)."""
from __future__ import annotations

from textual.widgets import Static

_WORDMARK_LINES = (
    "┌╦═══╦┐ ┌╦═╦═╦┐ ┌╦═══╦┐ ┌╦═══╦┐ ┌╦═══╦┐   ┌╦═══╦┐ ┌═╤╦╤═┐ ┌╦═══╦┐ ┌╦═══╦┐",
    "│║   ║│ │║ ║ ║│ ├╬══    │║  ═╦┐ ├╬═══╬┤ ═ ├╬══      │║│   │╠══╦╩┘ ├╬══   ",
    "└╩═══╩┘ └╩   ╩┘ └╩═══╩┘ └╩═══╩┘ └╩   ╩┘   └╩      └═╧╩╧═┘ └╩  ╚═┘ └╩═══╩┘",
)
"""OMEGA-FIRE en un seul bandeau de lettres, identique a
interfaces/cli/app.py::MAIN_MENU_LOGO_LINES, caracteres non modifies."""

_MARKUP = "\n".join((
    f"[$accent]{_WORDMARK_LINES[0]}[/]",
    f"[$foreground]{_WORDMARK_LINES[1]}[/]",
    f"[$accent]{_WORDMARK_LINES[2]}[/]",
))


class HomeWordmark(Static):
    """Bandeau decoratif centre en haut de screens/home.py."""

    def __init__(self) -> None:
        super().__init__(_MARKUP, classes="omega-home-wordmark")
