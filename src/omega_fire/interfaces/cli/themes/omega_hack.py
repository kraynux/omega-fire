# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Omega Hack Theme.

A retro terminal theme inspired by classic matrix/green-screen monitors.
"""
from rich.style import Style
from rich.theme import Theme
from omega_fire.interfaces.cli.themes.base import Theme as ThemeBase

class OmegaHackTheme(ThemeBase):
    @property
    def name(self) -> str: return "omega-hack"
    @property
    def display_name(self) -> str: return "Omega Hack (Retro Matrix)"
    @property
    def prefers_emojis(self) -> bool: return False  # Fallback to [OK], [!!], [X]
    @property
    def supports_live_rendering(self) -> bool: return True

    def get_rich_theme(self) -> Theme:
        return Theme({
            "bg.deep": "#000000", "bg.card": "#001100", "bg.header": "#000a00",
            "text.main": "#00ff00", "text.muted": "#008800", "text.heading": "#00ff00",
            "text.link": "#00ff00 underline", "border.default": "#004400", "border.accent": "#00ff00",
            "status.available": "bold #00ff00", "status.degraded": "bold #aaaa00",
            "status.missing": "bold #ff0000", "status.disqualified": "dim #ff0000",
            "backend.nftables": "bold #00ff00", "backend.iptables": "bold #00cc00",
            "backend.fail2ban": "bold #aaaa00", "backend.conntrack": "bold #00ff00",
            "menu.title": "bold #00ff00", "menu.enabled": "#00ff00",
            "menu.disabled": "dim #004400", "menu.selected": "reverse bold #00ff00",
            "table.header": "bold #00ff00", "table.border": "#004400", "table.row.hover": "#001100",
            "action.success": "#00ff00", "action.warning": "#aaaa00", "action.error": "#ff0000", "action.info": "#00ff00",
            "text.info": "#00ff00", "text.danger": "#ff0000", "text.warning": "#aaaa00",
            "border.primary": "#00ff00", "menu.item": "#00ff00",  # = text.main (thème monochrome vert dès l'origine)
            "footer.key": "bold #00ff00", "footer.label": "#508050",  # = text.heading (identique à border.accent sur ce thème délibérément monochrome)
            "footer.separator": "#00ff00", "footer.context": "bold #90ff90",
        })

    def get_style(self, style_name: str) -> Style:
        return self.get_rich_theme().styles.get(style_name, Style(color="#00ff00"))


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
        return "bold #00ff00"

    @property
    def footer_label_style(self) -> str:
        return "#508050"

    @property
    def footer_separator_style(self) -> str:
        return "#1a3a1a"

    @property
    def footer_context_style(self) -> str:
        return "bold #90ff90"

# <-- INFO DEV ---------------------------------------------------------
# Rôle : Thème rétro "Matrix" (fond noir pur, texte vert phosphorescent).
# Cible : Tous les terminaux, très léger, nostalgie hacker.
# Points clés : Pas d'emojis (pour garder l'esthétique ASCII pure), vert #00ff00 dominant.
#---------------------------------------------------------------------->
