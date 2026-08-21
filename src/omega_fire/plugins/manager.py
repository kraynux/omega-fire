# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Plugin manager for Omega-Fire.

Manages the lifecycle of plugins: loading, activation, deactivation, and querying.
Provides a unified interface for the application to interact with plugins.

Conforms to Omega-Fire architecture charter:
- Pure management logic, no business rules
- No dependency on domain/, application/, or infrastructure/
- Implements ports/plugin.py contract (PluginPort)
- Errors are isolated and reported, never propagated to the core
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from omega_fire.plugins.exceptions import (
    PluginActivationError,
    PluginConflictError,
    PluginDependencyError,
    PluginLoadError,
    PluginNotFoundError,
)
from omega_fire.plugins.loader import PluginLoader, PluginManifest


# ----------------------------------------------------------------------
# Plugin status enum
# ----------------------------------------------------------------------
class PluginStatus:
    """Status of a plugin in the manager."""
    LOADED = "loaded"
    ACTIVE = "active"
    DISABLED = "disabled"
    ERROR = "error"


# ----------------------------------------------------------------------
# Plugin info (runtime state)
# ----------------------------------------------------------------------
@dataclass
class PluginInfo:
    """Runtime information about a plugin.
    
    Attributes:
        manifest: Plugin metadata.
        status: Current status (loaded, active, disabled, error).
        module: The loaded plugin module.
        error_message: Error message if status is ERROR.
    """
    manifest: PluginManifest
    status: str = PluginStatus.LOADED
    module: Any = None
    error_message: Optional[str] = None


# ----------------------------------------------------------------------
# Plugin manager
# ----------------------------------------------------------------------
class PluginManager:
    """Manages the lifecycle of plugins.
    
    Attributes:
        loader: The plugin loader instance.
        plugins: Dictionary of loaded plugins (name → PluginInfo).
    """
    
    def __init__(self, loader: Optional[PluginLoader] = None):
        """Initialize the plugin manager.
        
        Args:
            loader: Optional plugin loader (created if None).
        """
        self.loader = loader or PluginLoader()
        self.plugins: dict[str, PluginInfo] = {}
    
    def discover_plugins(self) -> list[PluginManifest]:
        """Discover all available plugins.
        
        Returns:
            List of PluginManifest for discovered plugins.
        """
        plugin_paths = self.loader.discover_plugins()
        manifests = []
        
        for path in plugin_paths:
            try:
                manifest, _ = self.loader.load_plugin(path)
                manifests.append(manifest)
            except Exception:
                pass  # Silently ignore discovery errors
        
        return manifests
    
    def load_plugin(self, plugin_name: str) -> PluginInfo:
        """Load a plugin by name.
        
        Args:
            plugin_name: Name of the plugin to load.
        
        Returns:
            PluginInfo for the loaded plugin.
        
        Raises:
            PluginNotFoundError: If the plugin is not found.
            PluginLoadError: If the plugin cannot be loaded.
        """
        # Check if already loaded
        if plugin_name in self.plugins:
            return self.plugins[plugin_name]
        
        # Find the plugin
        plugin_paths = self.loader.discover_plugins()
        target_path = None
        for path in plugin_paths:
            if path.stem == plugin_name:
                target_path = path
                break
        
        if target_path is None:
            raise PluginNotFoundError(plugin_name)
        
        # Load the plugin
        try:
            manifest, module = self.loader.load_plugin(target_path)
            plugin_info = PluginInfo(
                manifest=manifest,
                status=PluginStatus.LOADED,
                module=module,
            )
            self.plugins[plugin_name] = plugin_info
            return plugin_info
        except Exception as e:
            plugin_info = PluginInfo(
                manifest=PluginManifest(name=plugin_name),
                status=PluginStatus.ERROR,
                error_message=str(e),
            )
            self.plugins[plugin_name] = plugin_info
            raise
    
    def activate_plugin(self, plugin_name: str) -> None:
        """Activate a loaded plugin.
        
        Args:
            plugin_name: Name of the plugin to activate.
        
        Raises:
            PluginNotFoundError: If the plugin is not loaded.
            PluginActivationError: If the plugin cannot be activated.
            PluginDependencyError: If a required dependency is missing.
            PluginConflictError: If there is a conflict with another plugin.
        """
        if plugin_name not in self.plugins:
            raise PluginNotFoundError(plugin_name)
        
        plugin_info = self.plugins[plugin_name]
        
        if plugin_info.status == PluginStatus.ACTIVE:
            return  # Already active
        
        if plugin_info.status == PluginStatus.ERROR:
            raise PluginActivationError(plugin_name, plugin_info.error_message)
        
        # Check dependencies
        for dep in plugin_info.manifest.dependencies:
            if dep not in self.plugins or self.plugins[dep].status != PluginStatus.ACTIVE:
                raise PluginDependencyError(plugin_name, dep)
        
        # Check conflicts
        self._check_conflicts(plugin_info)
        
        # Activate the plugin
        try:
            if hasattr(plugin_info.module, "activate"):
                plugin_info.module.activate()
            plugin_info.status = PluginStatus.ACTIVE
        except Exception as e:
            plugin_info.status = PluginStatus.ERROR
            plugin_info.error_message = str(e)
            raise PluginActivationError(plugin_name, str(e))
    
    def deactivate_plugin(self, plugin_name: str) -> None:
        """Deactivate an active plugin.
        
        Args:
            plugin_name: Name of the plugin to deactivate.
        
        Raises:
            PluginNotFoundError: If the plugin is not loaded.
        """
        if plugin_name not in self.plugins:
            raise PluginNotFoundError(plugin_name)
        
        plugin_info = self.plugins[plugin_name]
        
        if plugin_info.status != PluginStatus.ACTIVE:
            return  # Not active, nothing to do
        
        try:
            if hasattr(plugin_info.module, "deactivate"):
                plugin_info.module.deactivate()
            plugin_info.status = PluginStatus.LOADED
        except Exception as e:
            plugin_info.status = PluginStatus.ERROR
            plugin_info.error_message = str(e)
    
    def _check_conflicts(self, plugin_info: PluginInfo) -> None:
        """Check for conflicts with other active plugins.
        
        Args:
            plugin_info: The plugin to check.
        
        Raises:
            PluginConflictError: If a conflict is detected.
        """
        for name, other_info in self.plugins.items():
            if name == plugin_info.manifest.name:
                continue
            
            if other_info.status != PluginStatus.ACTIVE:
                continue
            
            # Check capability conflicts
            common_caps = set(plugin_info.manifest.capabilities) & set(other_info.manifest.capabilities)
            if common_caps:
                raise PluginConflictError(
                    plugin_info.manifest.name,
                    other_info.manifest.name,
                    f"Capacités en conflit : {', '.join(common_caps)}"
                )
    
    def get_plugin(self, plugin_name: str) -> PluginInfo:
        """Get information about a plugin.
        
        Args:
            plugin_name: Name of the plugin.
        
        Returns:
            PluginInfo for the plugin.
        
        Raises:
            PluginNotFoundError: If the plugin is not loaded.
        """
        if plugin_name not in self.plugins:
            raise PluginNotFoundError(plugin_name)
        return self.plugins[plugin_name]
    
    def list_plugins(self, status: Optional[str] = None) -> list[PluginInfo]:
        """List all plugins, optionally filtered by status.
        
        Args:
            status: Optional status filter (loaded, active, disabled, error).
        
        Returns:
            List of PluginInfo.
        """
        if status is None:
            return list(self.plugins.values())
        return [p for p in self.plugins.values() if p.status == status]
    
    def get_active_plugins(self) -> list[PluginInfo]:
        """Get all active plugins.
        
        Returns:
            List of active PluginInfo.
        """
        return self.list_plugins(status=PluginStatus.ACTIVE)
    
    def unload_plugin(self, plugin_name: str) -> None:
        """Unload a plugin.
        
        Args:
            plugin_name: Name of the plugin to unload.
        
        Raises:
            PluginNotFoundError: If the plugin is not loaded.
        """
        if plugin_name not in self.plugins:
            raise PluginNotFoundError(plugin_name)
        
        plugin_info = self.plugins[plugin_name]
        
        # Deactivate if active
        if plugin_info.status == PluginStatus.ACTIVE:
            self.deactivate_plugin(plugin_name)
        
        del self.plugins[plugin_name]

 # <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Gestion du cycle de vie des plugins (chargement, activation, désactivation).
# - Interface unifiée pour l'application (list_plugins, get_plugin, etc.).
# - Vérification des dépendances et conflits avant activation.
# - Isolation des erreurs (un plugin en erreur ne casse pas les autres).
#
# Pourquoi dans plugins/ (charte) :
# - Logique de gestion pure, aucune règle métier.
# - Aucune dépendance vers domain/, application/, infrastructure/.
# - Implémente le contrat ports/plugin.py (PluginPort).
# - Erreurs isolées et rapportées, jamais propagées au cœur.
#
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier (c'est le rôle de domain/).
# ❌ Pas d'orchestration (c'est le rôle de application/).
# ❌ Pas d'appels système (c'est le rôle de infrastructure/).
# ❌ Pas de dépendance vers d'autres couches.
#
# Points clés :
# - PluginStatus : constantes pour les états (LOADED, ACTIVE, DISABLED, ERROR).
# - PluginInfo : dataclass avec manifest, status, module, error_message.
# - PluginManager : classe principale avec discover_plugins(), load_plugin(),
#   activate_plugin(), deactivate_plugin(), get_plugin(), list_plugins().
# - discover_plugins() : découvre tous les plugins disponibles.
# - load_plugin() : charge un plugin par nom, gère les erreurs.
# - activate_plugin() : vérifie dépendances et conflits avant activation.
# - deactivate_plugin() : désactive proprement un plugin actif.
# - _check_conflicts() : détecte les conflits de capacités entre plugins actifs.
# - get_active_plugins() : retourne la liste des plugins actifs.
# - unload_plugin() : décharge un plugin (désactive si nécessaire).
#---------------------------------------------------------------------->       
