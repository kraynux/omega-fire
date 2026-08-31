# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Omega Light Theme.

A clean, professional light theme with pale backgrounds and dark blue text.
Designed for terminals configured in light mode.
"""
from rich.style import Style
from rich.theme import Theme
from omega_fire.interfaces.cli.themes.base import Theme as ThemeBase


class OmegaLightTheme(ThemeBase):
    """Light theme for Omega-Fire."""
    
    @property
    def name(self) -> str:
        return "omega-light"
    
    @property
    def display_name(self) -> str:
        return "Omega Light (Clean Professional)"
    
    @property
    def prefers_emojis(self) -> bool:
        return True
    
    @property
    def supports_live_rendering(self) -> bool:
        return True
    
    def get_rich_theme(self) -> Theme:
        return Theme({
            "bg.deep": "#f8f9fa",
            "bg.card": "#ffffff",
            "bg.header": "#e9ecef",
            "text.main": "#212529",
            "text.muted": "#6c757d",
            "text.heading": "#343a40",
            "text.link": "#0d6efd",
            "border.default": "#dee2e6",
            "border.accent": "#0d6efd",
            "status.available": "bold #198754",
            "status.degraded": "bold #ffc107",
            "status.missing": "bold #dc3545",
            "status.disqualified": "dim #dc3545",
            "backend.nftables": "bold #0d6efd",
            "backend.iptables": "bold #6610f2",
            "backend.fail2ban": "bold #fd7e14",
            "backend.conntrack": "bold #198754",
            "menu.title": "bold #0d6efd",
            "menu.enabled": "#0d6efd",
            "menu.disabled": "dim #6c757d",
            "menu.selected": "reverse bold #0d6efd",
            "table.header": "bold #495057",
            "table.border": "#dee2e6",
            "table.row.hover": "#f8f9fa",
            "action.success": "#198754",
            "action.warning": "#ffc107",
            "action.error": "#dc3545",
            "action.info": "#0d6efd",

            "text.info": "#0d6efd",
            "text.danger": "#dc3545",
            "text.warning": "#ffc107",
            "border.primary": "#0d6efd",
            "menu.item": "#212529",
            "footer.key": "bold #343a40",
            "footer.label": "#4a5a6a",
            "footer.separator": "#0d6efd",
            "footer.context": "bold #1a3a5c",
        })
    
    def get_style(self, style_name: str) -> Style:
        return self.get_rich_theme().styles.get(style_name, Style(color="#212529"))



    def is_compatible(self, terminal_info: dict) -> bool:
        """Check if terminal supports at least 256 colors."""
        colors = terminal_info.get("colors", "")
        return colors in ("24-bit", "truecolor", "256")
    
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
        return "bold #0d6efd"

    @property
    def footer_label_style(self) -> str:
        return "#4a5a6a"

    @property
    def footer_separator_style(self) -> str:
        return "#dee2e6"

    @property
    def footer_context_style(self) -> str:
        return "bold #1a3a5c"

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Thème clair avec fond blanc/gris pâle (#f8f9fa, #ffffff)
# - Texte bleu foncé (#212529) et accents bleu vif (#0d6efd)
# - Conçu pour les terminaux configurés en mode light
# Pourquoi dans interfaces/cli/themes/ (charte) :
# - C'est une définition pure de rendu, sans logique métier
# - Séparé du registry pour permettre l'ajout facile de nouveaux thèmes
# Ce qu'il ne contient PAS :
# ❌ Pas de logique de détection de terminal
# ❌ Pas de logique métier ou d'appels système
# Points clés :
# - Palette : fond #f8f9fa, texte #212529, accent #0d6efd (Bootstrap primary)
# - Statuts : available (#198754 vert), degraded (#ffc107 jaune), missing (#dc3545 rouge)
# - Supporte les emojis et le rendu Live
# - get_style() fournit un fallback sécurisé (#212529) si un style est manquant
#---------------------------------------------------------------------->
