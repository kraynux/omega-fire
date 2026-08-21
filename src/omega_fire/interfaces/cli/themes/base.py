# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Base theme class for Omega-Fire CLI.

Defines the abstract interface that all Omega-Fire themes must implement.
Ensures consistency in rendering across the application.

Conforms to Omega-Fire architecture charter:
- Pure rendering definitions, no business logic
- No dependency on domain/, application/, or infrastructure/
"""
from abc import ABC, abstractmethod

from rich.style import Style
from rich.theme import Theme


class Theme(ABC):
    """Abstract base class for all Omega-Fire themes."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Internal identifier of the theme (e.g., 'omega-base')."""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name of the theme (e.g., 'Omega Base')."""
        pass

    @property
    @abstractmethod
    def prefers_emojis(self) -> bool:
        """Whether this theme's visual identity includes emoji glyphs.

        A design choice of the theme itself (e.g. "omega-hack"/"omega-mono"
        are deliberately emoji-free regardless of terminal capability), NOT
        a terminal capability check — that is a separate, independent
        concern handled by TerminalDetector (themes/terminal.py) and
        icons.py::terminal_supports_emojis(). Renamed from
        "supports_emojis" (2026-08-17, referentiel §47) after the previous
        name caused a real incident: code assumed it reflected real
        terminal capability when it never did.
        """
        pass

    @property
    @abstractmethod
    def supports_live_rendering(self) -> bool:
        """Whether the theme supports Rich Live rendering."""
        pass

    @abstractmethod
    def get_rich_theme(self) -> Theme:
        """Return the Rich Theme object containing all style definitions."""
        pass

    def get_style(self, style_name: str) -> Style:
        """Get a specific style by name, with a safe fallback.
        
        Args:
            style_name: The name of the style to retrieve.
            
        Returns:
            A Rich Style object. Falls back to default text style if not found.
        """
        rich_theme = self.get_rich_theme()
        style_val = rich_theme.styles.get(style_name)

        if isinstance(style_val, Style):
            return style_val
        elif isinstance(style_val, str):
            return Style.parse(style_val)
        
        return Style.null()

    @abstractmethod
    def is_compatible(self, terminal_info: dict) -> bool:
        """Check if the theme is compatible with the given terminal capabilities.
        
        Args:
            terminal_info: Dictionary from TerminalDetector (contains 'colors', etc.)
            
        Returns:
            True if compatible, False otherwise.
        """
        pass

    @abstractmethod
    def get_fallback_theme(self) -> str:
        """Return the name of the fallback theme if this one is incompatible.
        
        Returns:
            The internal name of the fallback theme (e.g., 'omega-mono').
        """
        pass

    # ----------------------------------------------------------------------
    # SPLASH SCREEN STYLES (3 styles distincts)
    # ----------------------------------------------------------------------
    @property
    @abstractmethod
    def splash_header_style(self) -> str:
        """Style Rich pour le header du splash (2 lignes au-dessus du logo)."""
        pass

    @property
    @abstractmethod
    def splash_logo_style(self) -> str:
        """Style Rich pour le logo ASCII du splash (base de centrage)."""
        pass

    @property
    @abstractmethod
    def splash_tagline_style(self) -> str:
        """Style Rich pour la tagline du splash (2 lignes en-dessous du logo)."""
        pass

    # ----------------------------------------------------------------------
    # FOOTER STYLES (4 styles distincts pour le footer dynamique)
    # ----------------------------------------------------------------------
    @property
    @abstractmethod
    def footer_key_style(self) -> str:
        """Style Rich pour les touches dans le footer (Esc, Enter, [T], etc.)."""
        pass

    @property
    @abstractmethod
    def footer_label_style(self) -> str:
        """Style Rich pour les désignations dans le footer (Valider, Annuler, etc.)."""
        pass

    @property
    @abstractmethod
    def footer_separator_style(self) -> str:
        """Style Rich pour les séparateurs │ dans le footer."""
        pass

    @property
    @abstractmethod
    def footer_context_style(self) -> str:
        """Style Rich pour le contexte actuel dans le footer (📋 Menu, ✏️ Saisie, etc.)."""
        pass

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définir le contrat abstrait que tous les thèmes Omega-Fire doivent respecter.
# - Garantir la cohérence du rendu à travers toute l'application.
# Pourquoi dans interfaces/cli/themes/ (charte) :
# - C'est une définition pure de rendu, sans logique métier.
# - Séparé du registry pour permettre l'ajout facile de nouveaux thèmes.
# Ce qu'il ne contient PAS :
# ❌ Pas de logique de détection de terminal.
# ❌ Pas de logique métier ou d'appels système.
# ❌ Pas de dépendance vers domain/, application/ ou infrastructure/.
# Points clés :
# - Propriétés abstraites : name, display_name, prefers_emojis, supports_live_rendering.
# - Méthodes abstraites : get_rich_theme(), is_compatible(), get_fallback_theme().
# - Styles splash : splash_header_style, splash_logo_style, splash_tagline_style.
# - Styles footer : footer_key_style, footer_label_style, footer_separator_style, footer_context_style.
# - get_style() fournit un fallback sécurisé ("default") si un style est manquant.
#---------------------------------------------------------------------->
