# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Icon system with automatic fallback based on terminal capabilities.

Detects automatically if the terminal supports emojis:
- If yes: displays emojis (except for problematic ones that are always replaced)
- If no: automatically falls back to universal geometric Unicode icons

Problematic emojis (📡, 🔁, 📁, 💾) are ALWAYS replaced by geometric icons,
even on modern terminals, because they are known to render badly on many systems.
"""
import os
import sys
from typing import Optional


# ----------------------------------------------------------------------
# Emojis known to render badly on many terminals
# These are ALWAYS replaced by geometric icons, regardless of terminal support
# ----------------------------------------------------------------------
PROBLEMATIC_EMOJIS = {
    "📡",  # Satellite antenna - often renders as garbage
    "🔁",  # Repeat - often renders as garbage
    "📁",  # File folder - often renders as garbage
    "💾",  # Floppy disk - often renders as garbage
    "🛡️",  # Shield+VS16 - Rich counts 2 cells, several terminals only
            # render 1 (variation-selector width is terminal-dependent),
            # causing a 1-character border misalignment in bordered menus
    "⚙️",   # Gear+VS16 - same variation-selector width mismatch as above
}


# ----------------------------------------------------------------------
# Section icons: emoji version (for terminals that support emojis)
# ----------------------------------------------------------------------
SECTION_EMOJIS = {
    "1": "📡",  # État des capacités
    "2": "🛡️",  # Gestion des IPs
    "3": "⚙️",  # Gestion des règles
    "4": "🔁",  # Gestion Fail2ban
    "5": "📊",  # Gestion des logs
    "6": "📁",  # Exports & rapports
    "7": "💾",  # Système & persistance
    "8": "📈",  # Monitoring
    "0": "❌",  # Quitter
}


# ----------------------------------------------------------------------
# Geometric icons (universal fallback - supported by ALL terminals)
# ----------------------------------------------------------------------
SECTION_GEOMETRIC = {
    "1": "◉",  # Cercle dans cercle (État/Diagnostics)
    "2": "◆",  # Losange plein (IPs/Blacklist)
    "3": "■",  # Carré plein (Règles/Filtres)
    "4": "◎",  # Cercle dans cercle inversé (Fail2ban/Cycle)
    "5": "▲",  # Triangle plein (Logs/Monitoring)
    "6": "★",  # Étoile pleine (Exports/Rapports)
    "7": "●",  # Cercle plein (Système/Persistance)
    "8": "◈",  # Losange dans losange (Monitoring/Stats)
    "0": "✖",  # Croix (Quitter)
}


# ----------------------------------------------------------------------
# Terminal capability detection
# ----------------------------------------------------------------------
def _detect_emoji_support() -> bool:
    """Detect if the current terminal supports emoji rendering.
    
    Detection strategy:
    1. Check LANG/LC_ALL for UTF-8 support
    2. Check TERM for known problematic terminals
    3. Check if stdout is a TTY
    
    Returns:
        True if emojis are likely to render correctly
    """
    # Not a TTY → no emoji support
    if not sys.stdout.isatty():
        return False
    
    # Check LANG/LC_ALL for UTF-8
    lang = os.environ.get("LANG", "") or os.environ.get("LC_ALL", "")
    if "UTF-8" not in lang.upper() and "UTF8" not in lang.upper():
        return False
    
    # Check TERM for known problematic terminals
    term = os.environ.get("TERM", "").lower()
    problematic_terms = {
        "linux",      # Linux console (TTY) - no emoji support
        "vt100",      # Old VT100
        "vt220",      # Old VT220
        "dumb",       # Dumb terminal
    }
    if term in problematic_terms:
        return False
    
    # Check NO_COLOR environment variable (convention)
    if "NO_COLOR" in os.environ:
        return False
    
    return True


# Cache the detection result (expensive to recompute)
_EMOJI_SUPPORT_CACHE: Optional[bool] = None


def terminal_supports_emojis() -> bool:
    """Check if the terminal supports emojis (cached result).
    
    Returns:
        True if emojis are supported
    """
    global _EMOJI_SUPPORT_CACHE
    if _EMOJI_SUPPORT_CACHE is None:
        _EMOJI_SUPPORT_CACHE = _detect_emoji_support()
    return _EMOJI_SUPPORT_CACHE


def reset_emoji_detection_cache() -> None:
    """Reset the emoji detection cache (useful for testing)."""
    global _EMOJI_SUPPORT_CACHE
    _EMOJI_SUPPORT_CACHE = None


# ----------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------
def menu_icon(section_number: str) -> str:
    """Return the appropriate icon for a menu section.
    
    Automatic detection:
    - If terminal supports emojis AND the emoji is not problematic → emoji
    - Otherwise → geometric icon (universal fallback)
    
    Args:
        section_number: The menu section number (1-8, 0)
        
    Returns:
        The icon for that section (emoji or geometric)
        
    Example:
        >>> menu_icon("1")  # Returns "◉" (📡 is problematic)
        >>> menu_icon("2")  # Returns "🛡️" on modern terminals, "◆" on old ones
        >>> menu_icon("4")  # Returns "◎" (🔁 is problematic)
    """
    emoji = SECTION_EMOJIS.get(section_number)
    if emoji is None:
        return "[?]"
    
    # If emoji is problematic → always use geometric
    if emoji in PROBLEMATIC_EMOJIS:
        return SECTION_GEOMETRIC.get(section_number, "[?]")
    
    # If terminal doesn't support emojis → use geometric
    if not terminal_supports_emojis():
        return SECTION_GEOMETRIC.get(section_number, "[?]")
    
    # Otherwise → use emoji
    return emoji


def get_all_section_icons() -> dict[str, str]:
    """Get all section icons with automatic detection applied.
    
    Returns:
        Dictionary mapping section numbers to their icons
    """
    return {key: menu_icon(key) for key in SECTION_EMOJIS.keys()}


def get_all_emoji_icons() -> dict[str, str]:
    """Get all emoji icons (without detection).
    
    Returns:
        Dictionary mapping section numbers to their emoji icons
    """
    return SECTION_EMOJIS.copy()


def get_all_geometric_icons() -> dict[str, str]:
    """Get all geometric icons (universal fallback).
    
    Returns:
        Dictionary mapping section numbers to their geometric icons
    """
    return SECTION_GEOMETRIC.copy()


def get_terminal_info() -> dict:
    """Get information about terminal capabilities (for debugging).
    
    Returns:
        Dictionary with terminal info
    """
    return {
        "emoji_support": terminal_supports_emojis(),
        "LANG": os.environ.get("LANG", ""),
        "LC_ALL": os.environ.get("LC_ALL", ""),
        "TERM": os.environ.get("TERM", ""),
        "is_tty": sys.stdout.isatty(),
        "NO_COLOR": "NO_COLOR" in os.environ,
    }


# <-- INFO DEV ---------------------------------------------------------
# Role :
# - Systeme d'icones avec detection automatique des capacites du terminal
# - Si le terminal supporte les emojis → affiche les emojis
# - Si le terminal ne supporte pas les emojis → fallback automatique sur
#   les icones geometriques universelles
# - Les emojis problematiques (📡, 🔁, 📁, 💾) sont TOUJOURS remplaces
#   par des icones geometriques, meme sur les terminaux modernes
#
# Pourquoi dans interfaces/cli/renderers/ (charte) :
# - C'est de la logique de rendu pure
# - Pas de logique metier
# - Pas de dependance vers domain/, application/, infrastructure/
# - Utilise uniquement par l'interface utilisateur
#
# Ce qu'il ne contient PAS :
# ❌ Pas de logique metier
# ❌ Pas d'appels systeme
# ❌ Pas de dependance vers d'autres couches
#
# Points cles :
# - PROBLEMATIC_EMOJIS : emojis connus pour mal s'afficher (📡, 🔁, 📁, 💾)
#   Ces emojis sont TOUJOURS remplaces par des icones geometriques
# - SECTION_EMOJIS : emojis pour chaque section de menu
# - SECTION_GEOMETRIC : icones geometriques universelles (fallback)
#   ◉ ◆ ■ ◎ ▲ ★ ● ◈ ✖ - supportes par TOUS les terminaux
# - _detect_emoji_support() : detection automatique via :
#     * sys.stdout.isatty() (doit etre un TTY)
#     * LANG/LC_ALL (doit contenir UTF-8)
#     * TERM (liste noire : linux, vt100, vt220, dumb)
#     * NO_COLOR (convention standard)
# - terminal_supports_emojis() : resultat mis en cache pour performance
# - reset_emoji_detection_cache() : pour les tests
# - menu_icon(section_number) : API principale
#   Retourne l'emoji OU l'icone geometrique selon la detection
# - get_all_section_icons() : retourne tous les icones avec detection
# - get_terminal_info() : debug des capacites du terminal
#
# Logique de decision :
# 1. Si emoji est dans PROBLEMATIC_EMOJIS → TOUJOURS geometrique
# 2. Sinon, si terminal ne supporte pas les emojis → geometrique
# 3. Sinon → emoji
#
# Avantages :
# ✅ Detection automatique (pas de configuration manuelle)
# ✅ Fallback transparent pour l'utilisateur
# ✅ Emojis problematiques toujours remplaces (evite les caracteres bizarres)
# ✅ Icones geometriques universelles (pas de confusion avec raccourcis)
# ✅ Performance (resultat mis en cache)
# ✅ Debuggable (get_terminal_info())
#
# Comment il sera utilise (apercu) :
# - interfaces/cli/menu_builder.py utilisera menu_icon() pour chaque section
# - La detection est automatique, pas de configuration necessaire
# - Sur un terminal moderne avec UTF-8 : emojis (sauf problematiques)
# - Sur un terminal basique ou sans UTF-8 : icones geometriques
#---------------------------------------------------------------------->
