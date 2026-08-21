# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Interface layer exceptions.

Technical exceptions specific to the interface layer (CLI/TUI).
These express failures in rendering, user input, navigation, or display.
They are caught by the application layer or displayed directly to the user.
"""
from omega_fire.core.exceptions import CoreError


class InterfaceError(CoreError):
    """Base exception for interface operations."""
    def __init__(self, message: str, context: dict = None):
        super().__init__(message, context)


class RenderError(InterfaceError):
    """Raised when rendering fails."""
    def __init__(self, component: str, reason: str, context: dict = None):
        super().__init__(
            f"Failed to render '{component}': {reason}",
            {**(context or {}), "component": component, "reason": reason},
        )
        self.component = component
        self.reason = reason


class UserInputError(InterfaceError):
    """Raised when user input is invalid or cannot be processed."""
    def __init__(self, prompt_name: str, reason: str, context: dict = None):
        super().__init__(
            f"Invalid user input for '{prompt_name}': {reason}",
            {**(context or {}), "prompt_name": prompt_name, "reason": reason},
        )
        self.prompt_name = prompt_name
        self.reason = reason


class NavigationError(InterfaceError):
    """Raised when menu navigation fails."""
    def __init__(self, node_path: str, reason: str, context: dict = None):
        super().__init__(
            f"Navigation failed for '{node_path}': {reason}",
            {**(context or {}), "node_path": node_path, "reason": reason},
        )
        self.node_path = node_path
        self.reason = reason


class MenuBuildError(InterfaceError):
    """Raised when menu construction fails."""
    def __init__(self, reason: str, context: dict = None):
        super().__init__(
            f"Failed to build menu: {reason}",
            {**(context or {}), "reason": reason},
        )
        self.reason = reason


class KeybindingError(InterfaceError):
    """Raised when keybinding handling fails."""
    def __init__(self, key: str, reason: str, context: dict = None):
        super().__init__(
            f"Keybinding error for '{key}': {reason}",
            {**(context or {}), "key": key, "reason": reason},
        )
        self.key = key
        self.reason = reason


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit les exceptions techniques spécifiques à la couche interfaces/
# - Ces exceptions expriment des pannes de rendu, d'entrée utilisateur, de navigation
# - Elles sont capturées par application/ ou affichées directement à l'utilisateur
# Pourquoi dans interfaces/ (charte) :
# - Ce sont des erreurs d'interface, pas des règles métier
# - Elles encapsulent les pannes de rendu Rich, de prompts, de navigation
# - Elles héritent de CoreError pour être capturées uniformément
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier (pas de règles de blacklist, politiques)
# ❌ Pas d'appels système (juste des définitions d'exceptions)
# ❌ Pas de dépendance vers domain/, application/ ou infrastructure/
# Points clés :
# - Hiérarchie : InterfaceError → CoreError → Exception
# - 5 exceptions ciblées :
#   - RenderError : échec de rendu Rich (component, reason)
#   - UserInputError : entrée utilisateur invalide (prompt_name, reason)
#   - NavigationError : échec de navigation (node_path, reason)
#   - MenuBuildError : échec de construction du menu (reason)
#   - KeybindingError : échec de gestion des raccourcis (key, reason)
# - Contexte riche : chaque exception stocke les données pertinentes
# Comment elles seront utilisées (aperçu) :
# - interfaces/cli/renderers/ les lèvera lors du rendu
# - interfaces/cli/prompts.py les lèvera lors de la saisie utilisateur
# - interfaces/cli/tree_builder.py les lèvera lors de la navigation
# - application/pipeline/ les capturera pour afficher des messages stables
#---------------------------------------------------------------------->
