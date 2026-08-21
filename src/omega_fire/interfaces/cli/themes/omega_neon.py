# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Omega Neon Theme.

A cyberpunk-inspired theme with deep dark backgrounds and vibrant neon accents.
Requires 24-bit color support for optimal display.
"""
from rich.style import Style
from rich.theme import Theme
from omega_fire.interfaces.cli.themes.base import Theme as ThemeBase


class OmegaNeonTheme(ThemeBase):
    @property
    def name(self) -> str: return "omega-neon"
    @property
    def display_name(self) -> str: return "Omega Neon (Cyberpunk)"
    @property
    def prefers_emojis(self) -> bool: return True
    @property
    def supports_live_rendering(self) -> bool: return True

    def get_rich_theme(self) -> Theme:
        return Theme({
            "bg.deep": "#0a0a12", "bg.card": "#12121e", "bg.header": "#0f0f1a",
            "text.main": "#e0e0ff", "text.muted": "#6a6a8a", "text.heading": "#ffffff",
            "text.link": "#00ffff", "border.default": "#2a2a4a", "border.accent": "#ff00ff",
            "status.available": "bold #00ff9d", "status.degraded": "bold #ffea00",
            "status.missing": "bold #ff0055", "status.disqualified": "dim #ff0055",
            "backend.nftables": "bold #00ffff", "backend.iptables": "bold #ff00ff",
            "backend.fail2ban": "bold #ffea00", "backend.conntrack": "bold #00ff9d",
            "menu.title": "bold #ff00ff", "menu.enabled": "#00ffff",
            "menu.disabled": "dim #6a6a8a", "menu.selected": "reverse bold #ff00ff",
            "table.header": "bold #ffffff", "table.border": "#2a2a4a", "table.row.hover": "#1a1a2e",
            "action.success": "#00ff9d", "action.warning": "#ffea00", "action.error": "#ff0055", "action.info": "#00ffff",
            "text.info": "#00ffff", "text.danger": "#ff0055", "text.warning": "#ffea00",
            "border.primary": "#ff00ff", "menu.item": "#e0e0ff",
            "footer.key": "bold #ffffff", "footer.label": "#b080d0",
            "footer.separator": "#ff00ff", "footer.context": "bold #ff80ff",
        })

    def get_style(self, style_name: str) -> Style:
        return self.get_rich_theme().styles.get(style_name, Style(color="#e0e0ff"))
    
    def is_compatible(self, terminal_info: dict) -> bool:
        """Check if terminal supports 24-bit colors and emojis.
        
        Args:
            terminal_info: Dictionary from TerminalDetector
        
        Returns:
            True if terminal supports 24-bit colors
        """
        colorterm = terminal_info.get("COLORTERM", "")
        return colorterm in ("truecolor", "24bit")
    
    def get_fallback_theme(self) -> str:
        """Return omega-mono as fallback for incompatible terminals."""
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
        return "bold #ff00ff"

    @property
    def footer_label_style(self) -> str:
        return "#b080d0"

    @property
    def footer_separator_style(self) -> str:
        return "#3a1a3a"

    @property
    def footer_context_style(self) -> str:
        return "bold #ff80ff"

# <-- INFO DEV ---------------------------------------------------------
# Rôle : Thème cyberpunk avec fond très sombre et accents néon (rose #ff00ff, cyan #00ffff).
# Cible : Terminaux modernes 24-bit (Ghostty, Kitty, WezTerm).
# Points clés : 
# - is_compatible() : vérifie que COLORTERM est "truecolor" ou "24bit"
# - get_fallback_theme() : retourne "omega-mono" si incompatible
# - Supporte les emojis et le rendu Live
#---------------------------------------------------------------------->
