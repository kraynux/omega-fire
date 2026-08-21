# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Theme and name normalization utilities.

Centralizes case-insensitive name normalization for themes, backends,
and terminal names to prevent silent failures due to casing mismatches.
"""
from typing import Optional


def normalize_name(name: str) -> str:
    """Normalize a name to lowercase with hyphens.
    
    Converts to lowercase and replaces underscores with hyphens
    for consistent comparison.
    
    Args:
        name: Name to normalize (e.g., "Omega-Base", "OMEGA_BASE")
    
    Returns:
        Normalized name (e.g., "omega-base")
    
    Examples:
        >>> normalize_name("Omega-Base")
        'omega-base'
        >>> normalize_name("OMEGA_NEON")
        'omega-neon'
        >>> normalize_name("omega_burn")
        'omega-burn'
    """
    if not name:
        return ""
    return name.lower().replace("_", "-").strip()


def normalize_backend(backend: str) -> str:
    """Normalize a backend name.
    
    Args:
        backend: Backend name (e.g., "Nftables", "IPTABLES")
    
    Returns:
        Normalized backend name (e.g., "nftables")
    """
    return normalize_name(backend)


def normalize_terminal(terminal: str) -> str:
    """Normalize a terminal name.
    
    Args:
        terminal: Terminal name (e.g., "Ghostty", "GNOME-TERMINAL")
    
    Returns:
        Normalized terminal name (e.g., "ghostty")
    """
    return normalize_name(terminal)


def find_case_insensitive(items: list[str], target: str) -> Optional[str]:
    """Find an item in a list with case-insensitive matching.
    
    Args:
        items: List of items to search
        target: Target to find
    
    Returns:
        The matching item (original case) or None if not found
    
    Examples:
        >>> find_case_insensitive(["omega-base", "omega-neon"], "Omega-Base")
        'omega-base'
    """
    target_normalized = normalize_name(target)
    for item in items:
        if normalize_name(item) == target_normalized:
            return item
    return None


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Centralise la normalisation des noms pour éviter les plantages dus à la casse
# - Fournit des helpers pour thèmes, backends et terminaux
# - Utilise normalize_name() comme fonction de base (lowercase + hyphens)
# Pourquoi dans interfaces/cli/themes/ (charte) :
# - C'est un utilitaire d'interface pur, pas de logique métier
# - Utilisé uniquement par le système de thèmes et la détection de terminaux
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier
# ❌ Pas d'appels système
# ❌ Pas de dépendance vers domain/, application/ ou infrastructure/
# Points clés :
# - normalize_name() : lowercase + remplace _ par - + strip
# - normalize_backend() / normalize_terminal() : alias explicites
# - find_case_insensitive() : recherche dans une liste avec matching insensible à la casse
# - Retourne l'item original (pas le normalisé) pour préserver l'affichage
# Comment il sera utilisé (aperçu) :
# - registry.py l'utilisera dans set_active() pour normaliser le nom du thème
# - terminal.py l'utilisera pour normaliser les noms de terminaux
# - app/bootstrap.py l'utilisera pour normaliser OMEGA_THEME et --theme
#---------------------------------------------------------------------->
