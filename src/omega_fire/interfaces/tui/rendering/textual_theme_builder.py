# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Construction des objets textual.theme.Theme a partir de omega_lib.theme.policies,
etendue avec la palette omega-fire-specifique (theme_extensions.py — voir
Phase 0 de la feuille de route : couleurs de statut de capacite et
d'identite de backend, sans equivalent generique dans omega_lib.theme).
Seul fichier, avec le reste de interfaces/tui/, autorise a combiner
donnees de theme et API Textual. Porte depuis omega-check (D-008)."""
from __future__ import annotations

from omega_lib.theme.policies import TUI_THEMES, ThemeDefinition
from textual.theme import Theme as TextualTheme

from omega_fire.interfaces.tui.theme_extensions import get_theme_extension


def build_textual_theme(definition: ThemeDefinition) -> TextualTheme:
    """Traduit une palette de omega_lib.theme.policies en objet
    textual.theme.Theme. Textual distingue `primary` (obligatoire) et
    `accent` (optionnel) ; notre modele n'a que `accent` (couleur
    principale) et `secondary` — mappe `primary <- palette.accent` et
    laisse `accent` non renseigne.

    Les 8 couleurs d'extension omega-fire (statuts de capacite + identite
    de backend) sont exposees via `variables`, le mecanisme natif Textual
    pour des jetons CSS additionnels au-dela des champs fixes de Theme —
    consommables dans les .tcss sous la forme `$status-available`,
    `$backend-nftables`, etc. Re-evaluees automatiquement au changement
    de theme, comme les 9 jetons generiques."""
    palette = definition.palette
    extension = get_theme_extension(definition.name)
    return TextualTheme(
        name=definition.name,
        primary=palette.accent,
        secondary=palette.secondary,
        warning=palette.warning,
        error=palette.error,
        success=palette.success,
        foreground=palette.foreground,
        background=palette.background,
        surface=palette.surface,
        panel=palette.panel,
        dark=definition.dark,
        variables={
            "status-available": extension.status.available,
            "status-degraded": extension.status.degraded,
            "status-missing": extension.status.missing,
            "status-disqualified": extension.status.disqualified,
            "backend-nftables": extension.backend.nftables,
            "backend-iptables": extension.backend.iptables,
            "backend-fail2ban": extension.backend.fail2ban,
            "backend-conntrack": extension.backend.conntrack,
        },
    )


def build_all_textual_themes() -> tuple[TextualTheme, ...]:
    """Construit les 10 themes du catalogue, dans l'ordre de
    omega_lib.theme.policies::TUI_THEMES."""
    return tuple(build_textual_theme(definition) for definition in TUI_THEMES.values())
