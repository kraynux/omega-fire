# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Omega Mono Theme.

A strictly monochrome theme using only 16 basic ANSI colors and ASCII symbols.
Designed for maximum compatibility with ancient terminals, TTY, and restricted SSH sessions.
"""
from rich.style import Style
from rich.theme import Theme
from omega_fire.interfaces.cli.themes.base import Theme as ThemeBase

class OmegaMonoTheme(ThemeBase):
    @property
    def name(self) -> str: return "omega-mono"
    @property
    def display_name(self) -> str: return "Omega Mono (ASCII / 16-colors)"
    @property
    def prefers_emojis(self) -> bool: return False
    @property
    def supports_live_rendering(self) -> bool: return True

    def get_rich_theme(self) -> Theme:
        return Theme({
            "bg.deep": "black", "bg.card": "black", "bg.header": "black",
            "text.main": "white", "text.muted": "bright_black", "text.heading": "bright_white",
            "text.link": "bright_white underline", "border.default": "bright_black", "border.accent": "white",
            "status.available": "bold green", "status.degraded": "bold yellow",
            "status.missing": "bold red", "status.disqualified": "dim red",
            "backend.nftables": "bold cyan", "backend.iptables": "bold blue",
            "backend.fail2ban": "bold magenta", "backend.conntrack": "bold green",
            "menu.title": "bold white", "menu.enabled": "bright_white",
            "menu.disabled": "dim bright_black", "menu.selected": "reverse bold white",
            "table.header": "bold white", "table.border": "bright_black", "table.row.hover": "black",
            "action.success": "green", "action.warning": "yellow", "action.error": "red", "action.info": "cyan",
            "text.info": "cyan", "text.danger": "red", "text.warning": "yellow",
            "border.primary": "white", "menu.item": "white",  # = text.main (texte normal, pas d'accent)
            "footer.key": "bold bright_white", "footer.label": "#888888",
            "footer.separator": "white", "footer.context": "bold white",
        })

    def get_style(self, style_name: str) -> Style:
        return self.get_rich_theme().styles.get(style_name, Style(color="white"))


    def is_compatible(self, terminal_info: dict) -> bool:
        """Check if terminal supports at least 16 colors."""
        colors = terminal_info.get("colors", "")
        return colors in ("24-bit", "truecolor", "256", "16")
    
    def get_fallback_theme(self) -> str:
        """Return omega-minimal as fallback."""
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
        return "#888888"

    @property
    def footer_separator_style(self) -> str:
        return "#444444"

    @property
    def footer_context_style(self) -> str:
        return "bold white"

# <-- INFO DEV ---------------------------------------------------------
# Rôle : Thème monochrome 16 couleurs, sans emojis (fallback ASCII `[OK]`, `[X]`).
# Cible : Linux TTY, xterm, urxvt, SSH ancien.
# Points clés : Utilise uniquement les couleurs ANSI de base (black, white, red, green, yellow, cyan, blue, magenta).
#---------------------------------------------------------------------->
