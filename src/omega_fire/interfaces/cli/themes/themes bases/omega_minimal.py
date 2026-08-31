# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Omega Minimal Theme.

A stripped-down theme using only the 8 basic ANSI colors.
No borders, no gradients, no visual effects.
Designed for slow SSH connections, basic terminals, and constrained environments.
"""
from rich.style import Style
from rich.theme import Theme
from omega_fire.interfaces.cli.themes.base import Theme as ThemeBase


class OmegaMinimalTheme(ThemeBase):
    """Minimal ANSI-only theme for Omega-Fire."""
    
    @property
    def name(self) -> str:
        return "omega-minimal"
    
    @property
    def display_name(self) -> str:
        return "Omega Minimal (8 ANSI colors)"
    
    @property
    def prefers_emojis(self) -> bool:
        return False
    
    @property
    def supports_live_rendering(self) -> bool:
        return False
    
    def get_rich_theme(self) -> Theme:
        return Theme({
            "bg.deep": "black",
            "bg.card": "black",
            "bg.header": "black",
            "text.main": "white",
            "text.muted": "white",
            "text.heading": "white",
            "text.link": "cyan",
            "border.default": "white",
            "border.accent": "white",
            "status.available": "green",
            "status.degraded": "yellow",
            "status.missing": "red",
            "status.disqualified": "red",
            "backend.nftables": "cyan",
            "backend.iptables": "blue",
            "backend.fail2ban": "magenta",
            "backend.conntrack": "green",
            "menu.title": "white",
            "menu.enabled": "cyan",
            "menu.disabled": "white",
            "menu.selected": "reverse",
            "table.header": "white",
            "table.border": "white",
            "table.row.hover": "black",
            "action.success": "green",
            "action.warning": "yellow",
            "action.error": "red",
            "action.info": "cyan",

            "text.info": "cyan",
            "text.danger": "red",
            "text.warning": "yellow",
            "border.primary": "white",
            "menu.item": "white",  # = text.main (texte normal, pas d'accent)
            "footer.key": "bold white",  # = text.heading (identique à border.accent sur ce thème délibérément minimal)
            "footer.label": "#aaaaaa",
            "footer.separator": "white",
            "footer.context": "bold white",
        })
    
    def get_style(self, style_name: str) -> Style:
        return self.get_rich_theme().styles.get(style_name, Style(color="white"))



    def is_compatible(self, terminal_info: dict) -> bool:
        """Always compatible (8 colors minimum)."""
        return True
    
    def get_fallback_theme(self) -> str:
        """No fallback, this is the last resort."""
        return "omega-minimal"

    @property
    def splash_header_style(self) -> str:
        return "bold cyan"

    @property
    def splash_logo_style(self) -> str:
        return "bold white"

    @property
    def splash_tagline_style(self) -> str:
        return "dim white"

    @property
    def footer_key_style(self) -> str:
        return "bold white"

    @property
    def footer_label_style(self) -> str:
        return "#aaaaaa"

    @property
    def footer_separator_style(self) -> str:
        return "#666666"

    @property
    def footer_context_style(self) -> str:
        return "bold white"

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Thème minimaliste utilisant uniquement les 8 couleurs ANSI standard
# - Aucune bordure, aucun gradient, aucun effet visuel
# - Conçu pour les connexions SSH lentes et terminaux basiques
# Pourquoi dans interfaces/cli/themes/ (charte) :
# - C'est une définition pure de rendu, sans logique métier
# - Séparé du registry pour permettre l'ajout facile de nouveaux thèmes
# Ce qu'il ne contient PAS :
# ❌ Pas de codes hexadécimaux (seulement couleurs ANSI : black, red, green, yellow, blue, magenta, cyan, white)
# ❌ Pas de logique de détection de terminal
# ❌ Pas de logique métier ou d'appels système
# Points clés :
# - Palette : uniquement 8 couleurs ANSI (pas de 256 couleurs, pas de 24-bit)
# - prefers_emojis = False : utilise des symboles ASCII ([OK], [X], [!!])
# - supports_live_rendering = False : utilise des affichages statiques
# - Pas de gras, pas de dim, pas de reverse (sauf pour menu.selected)
# - get_style() fournit un fallback sécurisé (white) si un style est manquant
#---------------------------------------------------------------------->
