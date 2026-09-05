# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Composition ASCII de l'ecran de demarrage. Logo repris tel quel de
interfaces/cli/renderers/splash.py::OMEGA_FIRE_LOGO_LINES (bouclier +
banniere OMEGA-FIRE, 23 lignes) — caracteres non modifies, seul le
mecanisme de coloration change (jetons de theme Rich/Textual directement
dans le markup au lieu de Rich Text par caractere, meme technique que
omega-check/widgets/splash_hero.py, D-008).

Regles de couleur reprises de la version Rich actuelle (meme fichier,
_render_omega_fire_logo()) :
- cadres "LINUX FIREWALL SUITE"/barre de version/cadre OMEGA-FIRE :
  $foreground (normal), texte "LINUX FIREWALL SUITE" et decorations
  "▄▄▄" : $accent (vif).
- banniere OMEGA-FIRE (3 lignes dans son cadre) : haut/bas $accent
  (vif), milieu $foreground (normal) — cadre "│" toujours $foreground.
- corps du bouclier : $foreground, omega incruste ("▒") en heading —
  simplifie ici en $foreground (dans omega_dark, text.heading #e0e0f0
  et menu.item #d0d0e0 sont deja tres proches ; Textual n'a pas de
  jeton "heading" distinct de foreground/primary/secondary).
- angle du bouclier (ligne 14) : coins "▀█"/"█▀" en $accent (renfort).
- tagline finale : "|" vifs ($accent), mots normaux ($foreground) —
  MEME sens que la version Rich actuelle d'omega-fire (pas celui de
  CHECK, qui l'a delibarement inverse pour lui-meme)."""
from __future__ import annotations

from textual.widgets import Static

_WIDTH = 77
"""Largeur du cadre OMEGA-FIRE (l'element le plus large) : axe de
centrage commun a tout le logo, meme technique que omega-check."""

_LOGO_LINES = (
    "┌────────────────────────┐",
    "│  LINUX FIREWALL SUITE  │",
    "▄▄▄ └────────────────────────┘ ▄▄▄",
    "█░▒▓████████▓▒░v3.0░▒▓████████▓▒░█",
    "┌───────────────────────────────────────────────────────────────────────────┐",
    "│ ┌╦═══╦┐ ┌╦═╦═╦┐ ┌╦═══╦┐ ┌╦═══╦┐ ┌╦═══╦┐   ┌╦═══╦┐ ┌═╤╦╤═┐ ┌╦═══╦┐ ┌╦═══╦┐ │",
    "│ │║   ║│ │║ ║ ║│ ├╬══    │║  ═╦┐ ├╬═══╬┤ ═ ├╬══      │║│   │╠══╦╩┘ ├╬══    │",
    "│ └╩═══╩┘ └╩   ╩┘ └╩═══╩┘ └╩═══╩┘ └╩   ╩┘   └╩      └═╧╩╧═┘ └╩  ╚═┘ └╩═══╩┘ │",
    "└───────────────────────────────────────────────────────────────────────────┘",
    "█░▒▓██████████████████████████▓▒░█",
    "█░▒▓████████▒▒▒▒▒▒▒▒▒▒████████▓▒░█",
    "█░▒▓███████▒▒████████▒▒███████▓▒░█",
    "█░▒▓███████▒▒████████▒▒███████▓▒░█",
    "█░▒▓███████▒▒████████▒▒███████▓▒░█",
    "▀█░▒▓████████▒▒████▒▒████████▓▒░█▀",
    "▀█░▒▓████▒▒▒▒████▒▒▒▒████▓▒░█▀",
    "▀█░▒▓████████████████▓▒░█▀",
    "▀█░▒▓████████████▓▒░█▀",
    "▀█░▒▓████████▓▒░█▀",
    "▀█░▒▓████▓▒░█▀",
    "▀▀▀▀▀▀▀▀▀▀",
    "FIREWALL | RULES | BAN & IP CONTROL | ORCHESTRATION | LOGS",
    "INTER-OPERABILITE | AUDIT | EXPORT | BACKUP | MONITORING",
)

_LFS_BOX = (0, 2)
_VERSION_BAR = 3
_OMEGA_BOX = (4, 8)
_OMEGA_LOGO_ROWS = (5, 7)
_SHIELD_ANGLE_LINE = 14
_SHIELD = (9, 20)
_TAGLINE_START = 21


def _centered(line: str) -> str:
    return line.center(_WIDTH)


def _escape(ch: str) -> str:
    return "[" if ch == "[" else ch


def _lfs_line(line: str) -> str:
    """Cadre en $foreground, texte/decorations "▄▄▄" en $accent."""
    out = []
    for ch in line:
        color = "$foreground" if ch in "┌┐└┘─│" else "$accent"
        out.append(f"[{color}]{_escape(ch)}[/]")
    return "".join(out)


def _omega_row(line: str, color: str) -> str:
    """Ligne de la banniere OMEGA-FIRE : cadre "│" en $foreground,
    contenu dans `color` (vif haut/bas, normal au milieu)."""
    prefix, _, rest = line.partition("│")
    inner, _, suffix = rest.rpartition("│")
    return f"{prefix}[$foreground]│[/][{color}]{inner}[/][$foreground]│{suffix}[/]"


def _shield_angle(line: str) -> str:
    n = len(line)
    out = []
    for idx, ch in enumerate(line):
        if idx < 2 or idx >= n - 2:
            color = "$accent"
        else:
            color = "$foreground"
        out.append(f"[{color}]{_escape(ch)}[/]")
    return "".join(out)


def _tagline(line: str) -> str:
    parts = line.split("|")
    colored = [f"[$foreground]{part}[/]" for part in parts]
    return "[$accent]|[/]".join(colored)


def _build_markup() -> str:
    lines: list[str] = []
    for i, raw in enumerate(_LOGO_LINES):
        centered = _centered(raw)
        if _LFS_BOX[0] <= i <= _LFS_BOX[1]:
            lines.append(_lfs_line(centered))
        elif i == _VERSION_BAR:
            lines.append(f"[$foreground]{centered}[/]")
        elif i in _OMEGA_BOX:
            lines.append(f"[$foreground]{centered}[/]")
        elif _OMEGA_LOGO_ROWS[0] <= i <= _OMEGA_LOGO_ROWS[1]:
            row_color = "$accent" if i != _OMEGA_LOGO_ROWS[0] + 1 else "$foreground"
            lines.append(_omega_row(centered, row_color))
        elif i == _SHIELD_ANGLE_LINE:
            lines.append(_shield_angle(centered))
        elif i == _SHIELD[1]:
            lines.append(f"[$accent]{centered}[/]")
        elif _SHIELD[0] <= i <= _SHIELD[1]:
            lines.append(f"[$foreground]{centered}[/]")
        elif i >= _TAGLINE_START:
            lines.append(_tagline(centered))
        else:
            lines.append(f"[$foreground]{centered}[/]")
    return "\n".join(lines)


_MARKUP = _build_markup()


class SplashHero(Static):
    """Bloc decoratif de l'ecran de demarrage (screens/splash.py)."""

    def __init__(self) -> None:
        super().__init__(_MARKUP, classes="omega-splash-hero")
