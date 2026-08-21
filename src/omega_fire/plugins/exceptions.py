# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Exceptions spécifiques au système de plugins.

Conformes à la charte Omega-Fire :
- Héritent d'une classe parente PluginsError.
- Ne dépendent d'aucune autre couche (domain/, application/, infrastructure/).
- Utilisées uniquement par loader.py et manager.py.
"""
from __future__ import annotations


class PluginsError(Exception):
    """Exception de base pour toutes les erreurs de plugins."""
    pass


class PluginNotFoundError(PluginsError):
    """Le plugin demandé n'existe pas ou n'est pas installé."""
    
    def __init__(self, plugin_name: str, message: str | None = None):
        self.plugin_name = plugin_name
        super().__init__(message or f"Plugin introuvable : '{plugin_name}'")


class PluginLoadError(PluginsError):
    """Le plugin existe mais ne peut pas être chargé (import, syntaxe, dépendance)."""
    
    def __init__(self, plugin_name: str, reason: str | None = None):
        self.plugin_name = plugin_name
        self.reason = reason
        msg = f"Impossible de charger le plugin '{plugin_name}'"
        if reason:
            msg += f" : {reason}"
        super().__init__(msg)


class PluginValidationError(PluginsError):
    """Le plugin est chargé mais ne respecte pas le contrat attendu."""
    
    def __init__(self, plugin_name: str, reason: str | None = None):
        self.plugin_name = plugin_name
        self.reason = reason
        msg = f"Plugin '{plugin_name}' invalide"
        if reason:
            msg += f" : {reason}"
        super().__init__(msg)


class PluginActivationError(PluginsError):
    """Le plugin ne peut pas être activé (prérequis manquants, conflit)."""
    
    def __init__(self, plugin_name: str, reason: str | None = None):
        self.plugin_name = plugin_name
        self.reason = reason
        msg = f"Impossible d'activer le plugin '{plugin_name}'"
        if reason:
            msg += f" : {reason}"
        super().__init__(msg)


class PluginConflictError(PluginsError):
    """Deux plugins sont en conflit (mêmes capacités, mêmes hooks)."""
    
    def __init__(self, plugin_a: str, plugin_b: str, reason: str | None = None):
        self.plugin_a = plugin_a
        self.plugin_b = plugin_b
        self.reason = reason
        msg = f"Conflit entre plugins '{plugin_a}' et '{plugin_b}'"
        if reason:
            msg += f" : {reason}"
        super().__init__(msg)


class PluginDependencyError(PluginsError):
    """Un plugin requis est manquant pour activer un autre plugin."""
    
    def __init__(self, plugin_name: str, missing_dependency: str):
        self.plugin_name = plugin_name
        self.missing_dependency = missing_dependency
        super().__init__(
            f"Plugin '{plugin_name}' nécessite le plugin '{missing_dependency}' qui n'est pas disponible"
        )

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Exceptions spécifiques au sous-système plugins/.
# - Hiérarchie : PluginsError (base) → PluginNotFoundError, PluginLoadError,
#   PluginValidationError, PluginActivationError, PluginConflictError,
#   PluginDependencyError.
#
# Pourquoi dans plugins/ (charte) :
# - Exceptions propres au sous-système, pas partagées avec d'autres couches.
# - Aucune dépendance vers domain/, application/, infrastructure/, interfaces/.
# - Utilisées uniquement par loader.py et manager.py.
#
# Ce qu'il ne contient PAS :
# ❌ Pas d'exception métier (c'est le rôle de domain/).
# ❌ Pas d'exception applicative (c'est le rôle de application/).
# ❌ Pas d'exception technique (c'est le rôle de infrastructure/).
# ❌ Pas de dépendance vers d'autres couches.
#
# Points clés :
# - PluginsError : classe de base pour catch global.
# - PluginNotFoundError : plugin absent du disque ou du registre.
# - PluginLoadError : erreur d'import, syntaxe, dépendance manquante.
# - PluginValidationError : plugin ne respecte pas le contrat (méthodes manquantes).
# - PluginActivationError : prérequis non satisfaits, conflit de capacités.
# - PluginConflictError : deux plugins déclarent les mêmes capacités/hooks.
# - PluginDependencyError : plugin requis manquant pour activer un autre.
#---------------------------------------------------------------------->        
