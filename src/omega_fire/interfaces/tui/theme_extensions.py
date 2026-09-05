# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Palette d'extension omega-fire, complementaire a omega_lib.theme.policies.Palette.

omega_lib.theme.Palette ne porte que 9 tokens generiques d'interface
(background/surface/panel/foreground/accent/secondary/success/warning/error),
communs a toute la suite omega-*. omega-fire a en plus BESOIN de couleurs
semantiques qui n'ont pas d'equivalent generique et n'ont pas vocation a
etre promues dans omega_lib (aucun autre outil de la suite n'a de notion
de "backend pare-feu" ou de "statut de capacite") :

- 4 statuts de capacite (available/degraded/missing/disqualified)
- 4 identites de backend (nftables/iptables/fail2ban/conntrack)

Ces 8 valeurs sont portees telles quelles depuis les 10 fichiers de theme
Rich existants (interfaces/cli/themes/omega_*.py) — aucune nouvelle
couleur inventee ici, seulement un regroupement par nom de theme pour
etre consommees par rendering/textual_theme_builder.py (Phase 1) en plus
des 9 tokens generiques d'omega_lib.theme.

Les noms de theme correspondent exactement aux 10 entrees de
omega_lib.theme.policies.TUI_THEMES (meme catalogue, meme lignee).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CapabilityStatusColors:
    available: str
    degraded: str
    missing: str
    disqualified: str


@dataclass(frozen=True)
class BackendColors:
    nftables: str
    iptables: str
    fail2ban: str
    conntrack: str


@dataclass(frozen=True)
class ThemeExtension:
    status: CapabilityStatusColors
    backend: BackendColors


# Valeurs portees depuis interfaces/cli/themes/omega_*.py::get_rich_theme()
# (cles "status.*"/"backend.*"), sans modification.
THEME_EXTENSIONS: dict[str, ThemeExtension] = {
    "omega-base": ThemeExtension(
        status=CapabilityStatusColors("#b0f7b0", "#ffbc6e", "#ff5555", "#ff5555"),
        backend=BackendColors("#00d4ff", "#7e8aa2", "#ffbc6e", "#b0f7b0"),
    ),
    "omega-burn": ThemeExtension(
        status=CapabilityStatusColors("#ffaa00", "#ff7700", "#ff2200", "#ff2200"),
        backend=BackendColors("#ff5500", "#ffaa00", "#ff7700", "#ffcc00"),
    ),
    "omega-contrast": ThemeExtension(
        status=CapabilityStatusColors("#06ffa5", "#ff9f1c", "#ff3535", "#ff3535"),
        backend=BackendColors("#004ff9", "#ff6b35", "#ffd23f", "#06ffa5"),
    ),
    "omega-dark": ThemeExtension(
        status=CapabilityStatusColors("#7ec885", "#e5b95c", "#e06060", "#e06060"),
        backend=BackendColors("#5b9bd5", "#9b7ed8", "#e5b95c", "#7ec885"),
    ),
    "omega-hack": ThemeExtension(
        status=CapabilityStatusColors("#00ff00", "#aaaa00", "#ff0000", "#ff0000"),
        backend=BackendColors("#00ff00", "#00cc00", "#aaaa00", "#00ff00"),
    ),
    "omega-light": ThemeExtension(
        status=CapabilityStatusColors("#198754", "#ffc107", "#dc3545", "#dc3545"),
        backend=BackendColors("#0d6efd", "#6610f2", "#fd7e14", "#198754"),
    ),
    "omega-minimal": ThemeExtension(
        status=CapabilityStatusColors("green", "yellow", "red", "red"),
        backend=BackendColors("cyan", "blue", "magenta", "green"),
    ),
    "omega-mono": ThemeExtension(
        status=CapabilityStatusColors("green", "yellow", "red", "red"),
        backend=BackendColors("cyan", "blue", "magenta", "green"),
    ),
    "omega-neon": ThemeExtension(
        status=CapabilityStatusColors("#00ff9d", "#ffea00", "#ff0055", "#ff0055"),
        backend=BackendColors("#00ffff", "#ff00ff", "#ffea00", "#00ff9d"),
    ),
    "omega-pink": ThemeExtension(
        status=CapabilityStatusColors("#b0ffb0", "#ffd0a0", "#ff80a0", "#ff80a0"),
        backend=BackendColors("#ff80b0", "#b0b0ff", "#ffd0a0", "#b0ffb0"),
    ),
}


def get_theme_extension(theme_name: str) -> ThemeExtension:
    """Retourne la palette d'extension pour un theme, avec repli sur omega-dark."""
    return THEME_EXTENSIONS.get(theme_name, THEME_EXTENSIONS["omega-dark"])
