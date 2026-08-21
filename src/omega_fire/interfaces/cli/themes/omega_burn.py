# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Omega Burn Theme.

A fire-inspired theme with warm tones: vibrant orange, deep red, golden amber.
Dark background for contrast. Evokes the power and energy of the firewall.
"""
from rich.style import Style
from rich.theme import Theme
from omega_fire.interfaces.cli.themes.base import Theme as ThemeBase


class OmegaBurnTheme(ThemeBase):
    """Fire-inspired theme for Omega-Fire."""
    
    @property
    def name(self) -> str:
        return "omega-burn"
    
    @property
    def display_name(self) -> str:
        return "Omega Burn (Fire Style)"
    
    @property
    def prefers_emojis(self) -> bool:
        return True
    
    @property
    def supports_live_rendering(self) -> bool:
        return True
    
    def get_rich_theme(self) -> Theme:
        return Theme({
            "bg.deep": "#1a0505",
            "bg.card": "#2d0a0a",
            "bg.header": "#3d1010",
            "text.main": "#f0e0d0",
            "text.muted": "#a08070",
            "text.heading": "#ffaa00",
            "text.link": "#ff5500",
            "border.default": "#4d1515",
            "border.accent": "#ff5500",
            "status.available": "bold #ffaa00",
            "status.degraded": "bold #ff7700",
            "status.missing": "bold #ff2200",
            "status.disqualified": "dim #ff2200",
            "backend.nftables": "bold #ff5500",
            "backend.iptables": "bold #ffaa00",
            "backend.fail2ban": "bold #ff7700",
            "backend.conntrack": "bold #ffcc00",
            "menu.title": "bold #ff5500",
            "menu.enabled": "#ff5500",
            "menu.disabled": "dim #a08070",
            "menu.selected": "reverse bold #ff5500",
            "table.header": "bold #ffaa00",
            "table.border": "#4d1515",
            "table.row.hover": "#2d0a0a",
            "action.success": "#ffaa00",
            "action.warning": "#ff7700",
            "action.error": "#ff2200",
            "action.info": "#ff5500",

            "text.info": "#ff5500",
            "text.danger": "#ff2200",
            "text.warning": "#ff7700",
            "border.primary": "#ff5500",
            "menu.item": "#f0e0d0",  # = text.main (texte normal, pas d'accent)
            "footer.key": "bold #ffaa00",
            "footer.label": "#cc4444",
            "footer.separator": "#ff5500",
            "footer.context": "bold #ffd700",
        })
    
    def get_style(self, style_name: str) -> Style:
        return self.get_rich_theme().styles.get(style_name, Style(color="#f0e0d0"))



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
        return "bold #ff6b35"

    @property
    def footer_label_style(self) -> str:
        return "#cc4444"

    @property
    def footer_separator_style(self) -> str:
        return "#3a1a0a"

    @property
    def footer_context_style(self) -> str:
        return "bold #ffd700"

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Thème inspiré du feu avec tons chauds (orange #ff5500, rouge #ff2200, ambre #ffaa00)
# - Fond très sombre (#1a0505) pour contraste maximal
# - Évoque la puissance et l'énergie du firewall
# Pourquoi dans interfaces/cli/themes/ (charte) :
# - C'est une définition pure de rendu, sans logique métier
# - Séparé du registry pour permettre l'ajout facile de nouveaux thèmes
# Ce qu'il ne contient PAS :
# ❌ Pas de logique de détection de terminal
# ❌ Pas de logique métier ou d'appels système
# Points clés :
# - Palette : fond #1a0505 (noir rougeâtre), texte #f0e0d0 (crème), accents #ff5500 (orange feu)
# - Statuts : available (#ffaa00 ambre), degraded (#ff7700 orange), missing (#ff2200 rouge)
# - Supporte les emojis et le rendu Live
# - get_style() fournit un fallback sécurisé (#f0e0d0) si un style est manquant
#---------------------------------------------------------------------->
