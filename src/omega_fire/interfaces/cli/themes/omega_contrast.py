# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Omega Contrast Theme.

A high-accessibility theme designed for colorblind users and projection environments.
Features high contrast, thick borders, and colors distinguishable by all vision types.
"""
from rich.style import Style
from rich.theme import Theme
from omega_fire.interfaces.cli.themes.base import Theme as ThemeBase


class OmegaContrastTheme(ThemeBase):
    """High-contrast accessibility theme for Omega-Fire."""
    
    @property
    def name(self) -> str:
        return "omega-contrast"
    
    @property
    def display_name(self) -> str:
        return "Omega Contrast (High Accessibility)"
    
    @property
    def prefers_emojis(self) -> bool:
        return True
    
    @property
    def supports_live_rendering(self) -> bool:
        return True
    
    def get_rich_theme(self) -> Theme:
        return Theme({
            "bg.deep": "#1a1a2e",
            "bg.card": "#16213e",
            "bg.header": "#0f3460",
            "text.main": "#f0f0f0",
            "text.muted": "#a0a0a0",
            "text.heading": "#ffffff",
            "text.link": "#004ff9",
            "border.default": "#ffffff",
            "border.accent": "#ff6b35",
            "status.available": "bold #06ffa5",
            "status.degraded": "bold #ff9f1c",
            "status.missing": "bold #ff3535",
            "status.disqualified": "dim #ff3535",
            "backend.nftables": "bold #004ff9",
            "backend.iptables": "bold #ff6b35",
            "backend.fail2ban": "bold #ffd23f",
            "backend.conntrack": "bold #06ffa5",
            "menu.title": "bold #ffffff",
            "menu.enabled": "#004ff9",
            "menu.disabled": "dim #a0a0a0",
            "menu.selected": "reverse bold #ff6b35",
            "table.header": "bold #ffffff",
            "table.border": "#ffffff",
            "table.row.hover": "#16213e",
            "action.success": "#06ffa5",
            "action.warning": "#ff9f1c",
            "action.error": "#ff3535",
            "action.info": "#004ff9",

            "text.info": "#004ff9",
            "text.danger": "#ff3535",
            "text.warning": "#ff9f1c",
            "border.primary": "#ff6b35",
            "menu.item": "#f0f0f0",  # = text.main (texte normal, pas d'accent)
            "footer.key": "bold #ffffff",
            "footer.label": "white",
            "footer.separator": "#ff6b35",
            "footer.context": "bold yellow",
        })
    
    def get_style(self, style_name: str) -> Style:
        return self.get_rich_theme().styles.get(style_name, Style(color="#f0f0f0"))

    def is_compatible(self, terminal_info: dict) -> bool:
        """Check if terminal supports 24-bit colors."""
        colors = terminal_info.get("colors", "")
        return colors in ("24-bit", "truecolor")
    
    def get_fallback_theme(self) -> str:
        """Return omega-mono as fallback."""
        return "omega-mono"

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
        return "bold yellow"

    @property
    def footer_label_style(self) -> str:
        return "white"

    @property
    def footer_separator_style(self) -> str:
        return "#444444"

    @property
    def footer_context_style(self) -> str:
        return "bold yellow"

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Thème haute accessibilité pour daltoniens et projection
# - Couleurs vives avec contrastes élevés (WCAG AAA)
# - Bordures blanches épaisses pour séparer clairement les éléments
# Pourquoi dans interfaces/cli/themes/ (charte) :
# - C'est une définition pure de rendu, sans logique métier
# - Séparé du registry pour permettre l'ajout facile de nouveaux thèmes
# Ce qu'il ne contient PAS :
# ❌ Pas de logique de détection de terminal
# ❌ Pas de logique métier ou d'appels système
# Points clés :
# - Palette : fond #1a1a2e, texte #f0f0f0, accents #004ff9 (bleu), #ff6b35 (orange)
# - Statuts : available (#06ffa5 vert vif), degraded (#ff9f1c orange), missing (#ff3535 rouge)
# - Supporte les emojis et le rendu Live
# - Bordures blanches (#ffffff) pour contraste maximal
# - get_style() fournit un fallback sécurisé (#f0f0f0) si un style est manquant
#---------------------------------------------------------------------->

    
