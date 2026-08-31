# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Omega Pink Theme.

A soft pastel theme with gentle pink, lavender, and mint tones.
Available in dark and light variants for comfortable viewing.
"""
from rich.style import Style
from rich.theme import Theme
from omega_fire.interfaces.cli.themes.base import Theme as ThemeBase


class OmegaPinkTheme(ThemeBase):
    """Pastel pink theme for Omega-Fire."""
    
    @property
    def name(self) -> str:
        return "omega-pink"
    
    @property
    def display_name(self) -> str:
        return "Omega Pink (Pastel Soft)"
    
    @property
    def prefers_emojis(self) -> bool:
        return True
    
    @property
    def supports_live_rendering(self) -> bool:
        return True
    
    def get_rich_theme(self) -> Theme:
        return Theme({
            "bg.deep": "#1a1015",
            "bg.card": "#2a1a25",
            "bg.header": "#3a2a35",
            "text.main": "#f0e0f0",
            "text.muted": "#a080a0",
            "text.heading": "#ffb0d0",
            "text.link": "#ff80b0",
            "border.default": "#4a3a45",
            "border.accent": "#ff80b0",
            "status.available": "bold #b0ffb0",
            "status.degraded": "bold #ffd0a0",
            "status.missing": "bold #ff80a0",
            "status.disqualified": "dim #ff80a0",
            "backend.nftables": "bold #ff80b0",
            "backend.iptables": "bold #b0b0ff",
            "backend.fail2ban": "bold #ffd0a0",
            "backend.conntrack": "bold #b0ffb0",
            "menu.title": "bold #ffb0d0",
            "menu.enabled": "#ff80b0",
            "menu.disabled": "dim #a080a0",
            "menu.selected": "reverse bold #ff80b0",
            "table.header": "bold #ffb0d0",
            "table.border": "#4a3a45",
            "table.row.hover": "#2a1a25",
            "action.success": "#b0ffb0",
            "action.warning": "#ffd0a0",
            "action.error": "#ff80a0",
            "action.info": "#ff80b0",

            "text.info": "#ff80b0",
            "text.danger": "#ff80a0",
            "text.warning": "#ffd0a0",
            "border.primary": "#ff80b0",
            "menu.item": "#f0e0f0",  # = text.main (texte normal, pas d'accent)
            "footer.key": "bold #ffb0d0",
            "footer.label": "#a080a0",
            "footer.separator": "#ff80b0",
            "footer.context": "bold #ffb0d0",
        })
    
    def get_style(self, style_name: str) -> Style:
        return self.get_rich_theme().styles.get(style_name, Style(color="#f0e0f0"))


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
        return "bold #ff80b0"

    @property
    def footer_label_style(self) -> str:
        return "#a080a0"

    @property
    def footer_separator_style(self) -> str:
        return "#4a3a45"

    @property
    def footer_context_style(self) -> str:
        return "bold #ffb0d0"

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Thème pastel avec nuances de rose doux (#ff80b0), lavande (#b0b0ff), menthe (#b0ffb0)
# - Fond sombre pastel (#1a1015) pour contraste modéré
# - Ambiance douce et apaisante
# Pourquoi dans interfaces/cli/themes/ (charte) :
# - C'est une définition pure de rendu, sans logique métier
# - Séparé du registry pour permettre l'ajout facile de nouveaux thèmes
# Ce qu'il ne contient PAS :
# ❌ Pas de logique de détection de terminal
# ❌ Pas de logique métier ou d'appels système
# Points clés :
# - Palette : fond #1a1015 (rose sombre), texte #f0e0f0 (rose pâle), accents #ff80b0 (rose vif)
# - Statuts : available (#b0ffb0 menthe), degraded (#ffd0a0 pêche), missing (#ff80a0 rose)
# - Supporte les emojis et le rendu Live
# - get_style() fournit un fallback sécurisé (#f0e0f0) si un style est manquant
#---------------------------------------------------------------------->
