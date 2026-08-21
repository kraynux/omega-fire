# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Omega-Fire themes package.

This package provides the theme system for Omega-Fire CLI.
It includes 10 themes covering all terminal types and user preferences.
"""
from omega_fire.interfaces.cli.themes.base import Theme
from omega_fire.interfaces.cli.themes.registry import (
    ThemeRegistry,
    theme_registry,
    get_active_theme,
)
from omega_fire.interfaces.cli.themes.terminal import (
    TerminalDetector,
    detect_terminal_theme,
)

# Import all theme classes
from omega_fire.interfaces.cli.themes.omega_base import OmegaBaseTheme
from omega_fire.interfaces.cli.themes.omega_dark import OmegaDarkTheme
from omega_fire.interfaces.cli.themes.omega_dark import OmegaDarkTheme
from omega_fire.interfaces.cli.themes.omega_light import OmegaLightTheme
from omega_fire.interfaces.cli.themes.omega_mono import OmegaMonoTheme
from omega_fire.interfaces.cli.themes.omega_contrast import OmegaContrastTheme
from omega_fire.interfaces.cli.themes.omega_minimal import OmegaMinimalTheme
from omega_fire.interfaces.cli.themes.omega_neon import OmegaNeonTheme
from omega_fire.interfaces.cli.themes.omega_hack import OmegaHackTheme
from omega_fire.interfaces.cli.themes.omega_burn import OmegaBurnTheme
from omega_fire.interfaces.cli.themes.omega_pink import OmegaPinkTheme


# Register all themes
theme_registry.register(OmegaBaseTheme)
theme_registry.register(OmegaDarkTheme)
theme_registry.register(OmegaDarkTheme)
theme_registry.register(OmegaLightTheme)
theme_registry.register(OmegaMonoTheme)
theme_registry.register(OmegaContrastTheme)
theme_registry.register(OmegaMinimalTheme)
theme_registry.register(OmegaNeonTheme)
theme_registry.register(OmegaHackTheme)
theme_registry.register(OmegaBurnTheme)
theme_registry.register(OmegaPinkTheme)


def initialize_theme(theme_name: str = None) -> None:
    """Initialize the theme system.
    
    If no theme_name is provided, auto-detects the best theme based on terminal.
    Theme name is case-insensitive.
    
    Args:
        theme_name: Optional theme name to activate (e.g., 'omega-neon', 'Omega-Neon')
    """
    from omega_fire.interfaces.cli.themes.normalization import normalize_name
    
    if theme_name is None:
        theme_name = detect_terminal_theme()
    else:
        theme_name = normalize_name(theme_name)
    
    theme_registry.set_active(theme_name)


def get_available_themes() -> list[str]:
    """Get a list of all available theme names.
    
    Returns:
        List of theme names
    """
    return theme_registry.get_theme_names()


def set_theme(theme_name: str) -> None:
    """Set the active theme (case-insensitive).
    
    Args:
        theme_name: Name of the theme to activate
    
    Raises:
        RenderError: If the theme is not registered
    """
    from omega_fire.interfaces.cli.themes.normalization import normalize_name
    
    normalized_name = normalize_name(theme_name)
    theme_registry.set_active(normalized_name)


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Point d'entrée du package themes/
# - Importe et enregistre tous les 10 thèmes disponibles
# - Expose les fonctions de convenance pour initialiser et sélectionner les thèmes
# - Fournit la détection automatique du terminal pour choisir le thème par défaut
#---------------------------------------------------------------------->
