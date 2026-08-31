# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Omega Base Theme (Kraynux Style).

Implements the default theme based on the kraynux.snake-mackarel.ts.net CSS.
Features deep night blue backgrounds, bright cyan accents (#00d4ff),
and carefully balanced muted tones for a professional, tech-oriented look.
"""
from rich.style import Style
from rich.theme import Theme
from omega_fire.interfaces.cli.themes.base import Theme as ThemeBase


class OmegaBaseTheme(ThemeBase):
    """The default Omega-Fire theme, inspired by the Kraynux web interface."""
    
    @property
    def name(self) -> str:
        return "omega-base"
    
    @property
    def display_name(self) -> str:
        return "Omega Base (Kraynux Style)"
    
    @property
    def prefers_emojis(self) -> bool:
        return True
    
    @property
    def supports_live_rendering(self) -> bool:
        return True
    
    def get_rich_theme(self) -> Theme:
        """Return the Rich Theme object with Kraynux-inspired styles."""
        return Theme({
            # --- Couleurs de base (extraites du CSS) ---
            "bg.deep": "#0a0e1a",       # body background
            "bg.card": "#13182a",       # menu-card background
            "bg.header": "#0f1320",     # container background
            
            # --- Typographie et texte ---
            "text.main": "#e0e0e0",     # body color
            "text.muted": "#8f9bb3",    # menu-desc, secondary text
            "text.heading": "#b4c2e0",  # h2, h3 colors
            "text.link": "#00d4ff",     # a (cyan links)
            
            # --- Bordures et séparateurs ---
            "border.default": "#2a2e3a",
            "border.accent": "#00d4ff",
            
            # --- Statuts de capacité (adaptés du CSS) ---
            "status.available": "bold #b0f7b0",  # .public (vert doux)
            "status.degraded": "bold #ffbc6e",   # .badge-auth (orange doux)
            "status.missing": "bold #ff5555",    # Rouge standard adapté au fond sombre
            "status.disqualified": "dim #ff5555",
            
            # --- Backends ---
            "backend.nftables": "bold #00d4ff",  # Cyan principal
            "backend.iptables": "bold #7e8aa2",  # Gris-bleu muted
            "backend.fail2ban": "bold #ffbc6e",  # Orange doux
            "backend.conntrack": "bold #b0f7b0", # Vert doux
            
            # --- Interface et Menu ---
            "menu.title": "bold #00d4ff",
            "menu.enabled": "#00d4ff",
            "menu.disabled": "dim #8f9bb3",
            "menu.selected": "reverse bold #00d4ff",
            
            # --- Tableaux ---
            "table.header": "bold #a0b0c0",
            "table.border": "#2a2e3a",
            "table.row.hover": "#151b2a",
            
            # --- Alertes et Actions ---
            "action.success": "#b0f7b0",
            "action.warning": "#ffbc6e",
            "action.error": "#ff5555",
            "action.info": "#00d4ff",

            # --- Clés référencées ailleurs dans le code mais absentes du
            # dict jusqu'ici (repli gris plat silencieux) — reprennent les
            # valeurs déjà choisies pour leur équivalent sémantique le plus
            # proche, aucune nouvelle couleur inventée.
            "text.info": "#00d4ff",       # = action.info
            "text.danger": "#ff5555",     # = action.error
            "text.warning": "#ffbc6e",    # = action.warning
            "border.primary": "#00d4ff",  # = border.accent
            "menu.item": "#e0e0e0",       # = text.main (texte normal, pas d'accent)
            "footer.key": "bold #b4c2e0",  # = text.heading (distinct du vif "|" des séparateurs)
            "footer.label": "#8f9bb3",
            "footer.separator": "#00d4ff",  # = border.accent (demandé : "|" toujours vif)
            "footer.context": "bold #b4c2e0",
        })
    
    def get_style(self, style_name: str) -> Style:
        """Get a specific style by name.
        
        Args:
            style_name: Name of the style (e.g., 'status.available')
        
        Returns:
            Rich Style object
        """
        theme = self.get_rich_theme()
        # Fallback to a safe default if the style is not found
        return theme.styles.get(style_name, Style(color="#e0e0e0"))

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
        return "bold #00d4ff"

    @property
    def footer_label_style(self) -> str:
        return "#8f9bb3"

    @property
    def footer_separator_style(self) -> str:
        return "#2a2e3a"

    @property
    def footer_context_style(self) -> str:
        return "bold #b4c2e0"

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Implémente le thème par défaut "Omega Base" basé sur le CSS fourni.
# - Traduit les codes hexadécimaux du site Kraynux en styles Rich.
# Pourquoi dans interfaces/cli/themes/ (charte) :
# - C'est une définition pure de rendu, sans logique métier.
# - Séparé du registry pour permettre l'ajout facile de nouveaux thèmes.
# Ce qu'il ne contient PAS :
# ❌ Pas de logique de détection de terminal (c'est le rôle de terminal.py).
# ❌ Pas de logique métier ou d'appels système.
# Points clés :
# - Palette principale : Fond #0a0e1a, Accent #00d4ff (Cyan), Texte #e0e0e0.
# - Statuts : Available (#b0f7b0), Degraded (#ffbc6e), Missing (#ff5555).
# - Backends : nftables (Cyan), iptables (Gris-bleu), fail2ban (Orange).
# - Supporte les emojis et le rendu Live (Rich Live).
# - get_style() fournit un fallback sécurisé (#e0e0e0) si un style est manquant.
# Comment il sera utilisé (aperçu) :
# - ThemeRegistry l'enregistrera comme thème par défaut ou suggéré.
# - Les renderers (tables.py, dashboard.py) utiliseront "status.available" etc.
#---------------------------------------------------------------------->
