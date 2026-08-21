# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Panel rendering utilities for Omega-Fire CLI.

Provides helpers for creating Rich panels with consistent styling
based on the active theme. All colors and styles are retrieved from
theme_registry, ensuring visual coherence across the application.

Conforms to Omega-Fire architecture charter:
- Pure rendering logic, no business rules
- Uses theme_registry for all styling (no hardcoded colors)
- No dependency on domain/, application/, or infrastructure/
"""
from typing import Optional

from rich.console import RenderableType
from rich.panel import Panel
from rich.text import Text
from rich.align import Align

from omega_fire.interfaces.cli.themes.registry import theme_registry
from omega_fire.interfaces.cli.renderers.styles import center_text


def create_panel(
    content: RenderableType,
    title: Optional[str] = None,
    subtitle: Optional[str] = None,
    border_style: Optional[str] = None,
    padding: tuple[int, int] = (1, 2),
    expand: bool = True,
) -> Panel:
    """Create a Rich panel with theme-consistent styling.
    
    Args:
        content: Panel content (str, Text, or Rich renderable)
        title: Optional panel title
        subtitle: Optional panel subtitle
        border_style: Optional border style (uses theme default if None)
        padding: Padding (vertical, horizontal)
        expand: Whether to expand to full width
    
    Returns:
        Rich Panel object
    """
    if border_style is None:
        border_style = theme_registry.get_style("border.default")
    
    return Panel(
        content,
        title=title,
        subtitle=subtitle,
        border_style=border_style,
        padding=padding,
        expand=expand,
    )


def create_info_panel(
    content: RenderableType,
    title: str = "ℹ️  Information",
    expand: bool = True,
) -> Panel:
    """Create an info panel with theme-consistent styling.
    
    Args:
        content: Panel content
        title: Panel title (default: "ℹ️  Information")
        expand: Whether to expand to full width
    
    Returns:
        Rich Panel object with info styling
    """
    border_style = theme_registry.get_style("action.info")
    
    return Panel(
        content,
        title=title,
        border_style=border_style,
        padding=(1, 2),
        expand=expand,
    )


def create_warning_panel(
    content: RenderableType,
    title: str = "⚠️  Avertissement",
    expand: bool = True,
) -> Panel:
    """Create a warning panel with theme-consistent styling.
    
    Args:
        content: Panel content
        title: Panel title (default: "⚠️  Avertissement")
        expand: Whether to expand to full width
    
    Returns:
        Rich Panel object with warning styling
    """
    border_style = theme_registry.get_style("action.warning")
    
    return Panel(
        content,
        title=title,
        border_style=border_style,
        padding=(1, 2),
        expand=expand,
    )


def create_error_panel(
    content: RenderableType,
    title: str = "❌ Erreur",
    expand: bool = True,
) -> Panel:
    """Create an error panel with theme-consistent styling.
    
    Args:
        content: Panel content
        title: Panel title (default: "❌ Erreur")
        expand: Whether to expand to full width
    
    Returns:
        Rich Panel object with error styling
    """
    border_style = theme_registry.get_style("action.error")
    
    return Panel(
        content,
        title=title,
        border_style=border_style,
        padding=(1, 2),
        expand=expand,
    )


def create_success_panel(
    content: RenderableType,
    title: str = "✅ Succès",
    expand: bool = True,
) -> Panel:
    """Create a success panel with theme-consistent styling.
    
    Args:
        content: Panel content
        title: Panel title (default: "✅ Succès")
        expand: Whether to expand to full width
    
    Returns:
        Rich Panel object with success styling
    """
    border_style = theme_registry.get_style("action.success")
    
    return Panel(
        content,
        title=title,
        border_style=border_style,
        padding=(1, 2),
        expand=expand,
    )


def create_menu_panel(
    menu_content: RenderableType,
    title: str = "Menu Principal",
    subtitle: Optional[str] = None,
    expand: bool = True,
) -> Panel:
    """Create a menu panel with theme-consistent styling.
    
    Args:
        menu_content: Menu content (typically a list of menu items)
        title: Panel title (default: "Menu Principal")
        subtitle: Optional subtitle
        expand: Whether to expand to full width
    
    Returns:
        Rich Panel object with menu styling
    """
    border_style = theme_registry.get_style("border.accent")
    title_style = theme_registry.get_style("menu.title")
    
    title_text = Text(title, style=title_style)
    
    return Panel(
        menu_content,
        title=title_text,
        subtitle=subtitle,
        border_style=border_style,
        padding=(1, 2),
        expand=expand,
    )


def create_splash_panel(
    ascii_art: str,
    subtitle: Optional[str] = None,
    expand: bool = True,
) -> Panel:
    """Create a splash/welcome panel with centered ASCII art.
    
    Args:
        ascii_art: ASCII art string (will be centered)
        subtitle: Optional subtitle below the ASCII art
        expand: Whether to expand to full width
    
    Returns:
        Rich Panel object with splash styling
    """
    border_style = theme_registry.get_style("border.accent")
    
    centered_lines = [center_text(line) for line in ascii_art.split("\n")]
    centered_art = "\n".join(centered_lines)
    
    content_parts = [centered_art]
    
    if subtitle:
        subtitle_text = Text(subtitle, style=theme_registry.get_style("text.muted"))
        content_parts.append("")
        content_parts.append(Align.center(subtitle_text))
    
    content = "\n".join(content_parts)
    
    return Panel(
        content,
        border_style=border_style,
        padding=(2, 4),
        expand=expand,
    )


def create_status_panel(
    status_items: list[tuple[str, str, str]],
    title: str = "État du Système",
    expand: bool = True,
) -> Panel:
    """Create a status panel showing multiple status items.
    
    Args:
        status_items: List of (label, value, status_key) tuples
                     status_key can be "available", "degraded", "missing", "disqualified"
        title: Panel title
        expand: Whether to expand to full width
    
    Returns:
        Rich Panel object with status items
    """
    content = Text()
    
    for label, value, status_key in status_items:
        style = theme_registry.get_style(f"status.{status_key}")
        
        content.append(f"{label}: ", style=theme_registry.get_style("text.main"))
        content.append(f"{value}\n", style=style)
    
    return Panel(
        content,
        title=title,
        border_style=theme_registry.get_style("border.default"),
        padding=(1, 2),
        expand=expand,
    )


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Helpers pour créer des panneaux Rich cohérents avec le thème actif
# - Utilise theme_registry pour tous les styles (pas de couleurs hardcodées)
# - Fournit des panneaux spécialisés : info, warning, error, success, menu, splash, status
# Pourquoi dans interfaces/cli/renderers/ (charte) :
# - Rendu pur, aucune logique métier
# - Utilise uniquement Rich et theme_registry
# - Pas de dépendance vers domain/, application/, infrastructure/
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier (pas de règles de blacklist, politiques)
# ❌ Pas de couleurs hardcodées (tout vient du thème actif)
# ❌ Pas d'appels système
# Points clés :
# - create_panel() : panneau générique avec style de bordure du thème
# - create_info_panel() : panneau d'information (bordure action.info)
# - create_warning_panel() : panneau d'avertissement (bordure action.warning)
# - create_error_panel() : panneau d'erreur (bordure action.error)
# - create_success_panel() : panneau de succès (bordure action.success)
# - create_menu_panel() : panneau de menu (bordure accent, titre style menu.title)
# - create_splash_panel() : panneau de page de garde (ASCII art centré)
# - create_status_panel() : panneau de statut avec items colorés
# - Tous les styles viennent de theme_registry.get_style()
# - create_splash_panel() utilise center_text() de layout.py pour le centrage
# Intégration prévue :
# - interfaces/cli/app.py utilisera create_menu_panel() pour le menu principal
# - interfaces/cli/actions.py utilisera create_success_panel() après une action
# - interfaces/cli/renderers/splash.py utilisera create_splash_panel()
#---------------------------------------------------------------------->
