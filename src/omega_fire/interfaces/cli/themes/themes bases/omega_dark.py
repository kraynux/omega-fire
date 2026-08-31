# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Omega Dark Theme.

A professional, sober dark theme with balanced blue/green/cyan accents
on a deep blue-grey background. Designed for 256-color terminals.
"""
from rich.style import Style
from rich.theme import Theme
from omega_fire.interfaces.cli.themes.base import Theme as ThemeBase


class OmegaDarkTheme(ThemeBase):
    """Professional dark theme for Omega-Fire."""

    @property
    def name(self) -> str:
        return "omega-dark"

    @property
    def display_name(self) -> str:
        return "Omega Dark (Professional)"

    @property
    def prefers_emojis(self) -> bool:
        return True

    @property
    def supports_live_rendering(self) -> bool:
        return True

    def get_rich_theme(self) -> Theme:
        return Theme({
            # --- Backgrounds ---
            "bg.deep": "#1e1e2e",
            "bg.card": "#252535",
            "bg.header": "#2a2a3e",

            # --- Typography ---
            "text.main": "#d0d0e0",
            "text.muted": "#7a7a9a",
            "text.heading": "#e0e0f0",
            "text.link": "#6db3f2",

            # --- Borders ---
            "border.default": "#3a3a50",
            "border.accent": "#5b9bd5",

            # --- Capability status ---
            "status.available": "bold #7ec885",
            "status.degraded": "bold #e5b95c",
            "status.missing": "bold #e06060",
            "status.disqualified": "dim #e06060",

            # --- Backends ---
            "backend.nftables": "bold #5b9bd5",
            "backend.iptables": "bold #9b7ed8",
            "backend.fail2ban": "bold #e5b95c",
            "backend.conntrack": "bold #7ec885",

            # --- Menu ---
            "menu.title": "bold #6db3f2",
            "menu.enabled": "#6db3f2",
            "menu.disabled": "dim #7a7a9a",
            "menu.selected": "reverse bold #5b9bd5",

            # --- Tables ---
            "table.header": "bold #a0a0c0",
            "table.border": "#3a3a50",
            "table.row.hover": "#2a2a3e",

            # --- Actions ---
            "action.success": "#7ec885",
            "action.warning": "#e5b95c",
            "action.error": "#e06060",
            "action.info": "#5b9bd5",

            # --- Clés référencées ailleurs mais absentes jusqu'ici ---
            "text.info": "#5b9bd5",
            "text.danger": "#e06060",
            "text.warning": "#e5b95c",
            "border.primary": "#5b9bd5",
            "menu.item": "#d0d0e0",  # = text.main (texte normal, pas d'accent)
            "footer.key": "bold #e0e0f0",  # = text.heading (distinct du vif "|" des séparateurs)
            "footer.label": "#7a7a9a",
            "footer.separator": "#5b9bd5",  # = border.accent (demandé : "|" toujours vif)
            "footer.context": "bold #a0b0d0",
        })

    def get_style(self, style_name: str) -> Style:
        return self.get_rich_theme().styles.get(style_name, Style(color="#d0d0e0"))

    def is_compatible(self, terminal_info: dict) -> bool:
        """Check if terminal supports at least 256 colors."""
        colors = terminal_info.get("colors", "")
        return colors in ("24-bit", "truecolor", "256")

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
        return "bold #5b9bd5"

    @property
    def footer_label_style(self) -> str:
        return "#7a7a9a"

    @property
    def footer_separator_style(self) -> str:
        return "#2a2a3a"

    @property
    def footer_context_style(self) -> str:
        return "bold #a0b0d0"

# <-- INFO DEV ---------------------------------------------------------
