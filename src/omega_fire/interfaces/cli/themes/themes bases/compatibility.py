# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Theme compatibility checker.

Analyzes terminal capabilities and suggests compatible themes.
Provides user-friendly messages when a theme is incompatible.
"""
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from omega_fire.interfaces.cli.themes.terminal import TerminalDetector, TerminalInfo
from omega_fire.interfaces.cli.themes.registry import theme_registry


def get_compatible_themes(terminal_info: Optional[dict] = None) -> list[str]:
    """Get the list of themes compatible with the current terminal.
    
    Args:
        terminal_info: Optional terminal info dict (auto-detected if None)
    
    Returns:
        List of compatible theme names
    """
    if terminal_info is None:
        detector = TerminalDetector()
        terminal_info = detector.get_terminal_info()
    
    compatible = []
    
    for theme_name in theme_registry.get_theme_names():
        theme_class = theme_registry._themes[theme_name]
        theme_instance = theme_class()
        
        if theme_instance.is_compatible(terminal_info):
            compatible.append(theme_name)
    
    return compatible


def get_incompatible_themes(terminal_info: Optional[dict] = None) -> list[str]:
    """Get the list of themes incompatible with the current terminal.
    
    Args:
        terminal_info: Optional terminal info dict (auto-detected if None)
    
    Returns:
        List of incompatible theme names
    """
    all_themes = set(theme_registry.get_theme_names())
    compatible = set(get_compatible_themes(terminal_info))
    return list(all_themes - compatible)


def format_compatibility_message(
    requested_theme: str,
    terminal_info: Optional[dict] = None,
    console: Optional[Console] = None,
) -> Panel:
    """Format a user-friendly compatibility message.
    
    Args:
        requested_theme: The theme that was requested
        terminal_info: Optional terminal info dict (auto-detected if None)
        console: Optional Rich console
    
    Returns:
        Rich Panel with compatibility information
    """
    if terminal_info is None:
        detector = TerminalDetector()
        terminal_info = detector.get_terminal_info()
    
    compatible = get_compatible_themes(terminal_info)
    
    # Build the message
    content = Text()
    content.append(f"❌ Le thème '{requested_theme}' n'est pas compatible avec votre terminal.\n\n", style="bold red")
    
    # Terminal info
    content.append("📺 Terminal détecté :\n", style="bold cyan")
    content.append(f"  • Nom : {terminal_info.get('name', 'Inconnu')}\n")
    content.append(f"  • Couleurs : {terminal_info.get('colors', 'Inconnu')}\n")
    content.append(f"  • Emojis : {' Oui' if terminal_info.get('supports_emojis') else '❌ Non'}\n")
    content.append(f"  • Live rendering : {' Oui' if terminal_info.get('supports_live') else '❌ Non'}\n\n")
    
    # Compatible themes
    content.append(" Thèmes compatibles :\n", style="bold green")
    if compatible:
        for theme_name in compatible:
            theme_class = theme_registry._themes[theme_name]
            theme_instance = theme_class()
            content.append(f"  • {theme_name} — {theme_instance.display_name}\n", style="cyan")
    else:
        content.append("  Aucun thème compatible détecté.\n", style="dim yellow")
    
    # Suggestion
    content.append("\n ", style="bold yellow")
    if compatible:
        content.append(f"Utilisez : --theme {compatible[0]}\n", style="yellow")
        content.append(f"Ou changez de thème dans le menu 7.4 (Recharger la configuration)", style="dim")
    else:
        content.append("Essayez omega-minimal pour une compatibilité maximale", style="yellow")
    
    return Panel(
        content,
        title="⚠️  Incompatibilité de thème",
        border_style="yellow",
        padding=(1, 2),
    )


def print_compatibility_warning(
    requested_theme: str,
    fallback_theme: str,
    terminal_info: Optional[dict] = None,
    console: Optional[Console] = None,
) -> None:
    """Print a compatibility warning with suggestions.
    
    Args:
        requested_theme: The theme that was requested
        fallback_theme: The theme that will be used instead
        terminal_info: Optional terminal info dict
        console: Optional Rich console
    """
    console = console or Console()
    
    if terminal_info is None:
        detector = TerminalDetector()
        terminal_info = detector.get_terminal_info()
    
    compatible = get_compatible_themes(terminal_info)
    
    # Build the message
    content = Text()
    content.append(f"⚠️  Le thème '{requested_theme}' n'est pas compatible.\n", style="bold yellow")
    content.append(f"↳ Fallback automatique vers '{fallback_theme}'\n\n", style="cyan")
    
    content.append("📺 Votre terminal :\n", style="bold")
    content.append(f"  {terminal_info.get('name', 'Inconnu')} ({terminal_info.get('colors', '?')} couleurs)\n\n")
    
    content.append(" Thèmes compatibles :\n", style="bold green")
    for theme_name in compatible[:5]:  # Show max 5
        theme_class = theme_registry._themes[theme_name]
        theme_instance = theme_class()
        content.append(f"  • {theme_name} — {theme_instance.display_name}\n", style="cyan")
    
    if len(compatible) > 5:
        content.append(f"  ... et {len(compatible) - 5} autre(s)\n", style="dim")
    
    console.print(Panel(
        content,
        title=" Thème incompatible",
        border_style="yellow",
        padding=(1, 2),
    ))


def check_and_warn_theme(
    requested_theme: str,
    console: Optional[Console] = None,
) -> str:
    """Check theme compatibility and warn if incompatible.
    
    Args:
        requested_theme: The theme to check
        console: Optional Rich console
    
    Returns:
        The actual theme to use (requested or fallback)
    """
    console = console or Console()
    detector = TerminalDetector()
    terminal_info = detector.get_terminal_info()
    
    # Check if the requested theme is compatible
    theme_class = theme_registry._themes.get(requested_theme)
    if theme_class is None:
        # Theme doesn't exist, use fallback
        fallback = detector.detect_best_theme()
        console.print(f"[yellow]⚠️  Thème '{requested_theme}' inconnu. Utilisation de '{fallback}'[/yellow]")
        return fallback
    
    theme_instance = theme_class()
    if not theme_instance.is_compatible(terminal_info):
        # Theme is incompatible, use fallback
        fallback = theme_instance.get_fallback_theme()
        print_compatibility_warning(
            requested_theme=requested_theme,
            fallback_theme=fallback,
            terminal_info=terminal_info,
            console=console,
        )
        return fallback
    
    # Theme is compatible
    return requested_theme


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Analyse les capacités du terminal détecté
# - Suggère la liste des thèmes compatibles
# - Fournit des messages utilisateur clairs quand un thème est incompatible
# - Propose un fallback automatique avec notification
# Pourquoi dans interfaces/cli/themes/ (charte) :
# - C'est de la logique d'interface pure (vérification de compatibilité)
# - Pas de logique métier, pas d'appels système
# - Utilise uniquement TerminalDetector et theme_registry
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier (pas de règles de blacklist, politiques)
# ❌ Pas d'appels système (juste de la vérification de capacités)
# ❌ Pas de dépendance vers domain/, application/ ou infrastructure/
# Points clés :
# - get_compatible_themes() : retourne la liste des thèmes compatibles
# - get_incompatible_themes() : retourne la liste des thèmes incompatibles
# - format_compatibility_message() : génère un Panel Rich avec les suggestions
# - print_compatibility_warning() : affiche un warning avec fallback automatique
# - check_and_warn_theme() : vérifie et retourne le thème à utiliser
# - Messages utilisateur en français avec emojis et couleurs Rich
# - Affiche les 5 premiers thèmes compatibles (pour ne pas surcharger)
# Comment il sera utilisé (aperçu) :
# - app/bootstrap.py appellera check_and_warn_theme() au démarrage
# - interfaces/cli/app.py utilisera format_compatibility_message() pour le menu 7.4
# - Les tests mockeront TerminalDetector pour simuler différents terminaux
#---------------------------------------------------------------------->
