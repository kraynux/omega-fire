# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Plugin loader for Omega-Fire.

Responsible for discovering and loading plugins from builtin and external sources.
Handles import mechanics, validation, and isolation.

Conforms to Omega-Fire architecture charter:
- Pure loading logic, no business rules
- No dependency on domain/, application/, or infrastructure/
- Uses ports/plugin.py contract for validation
- Errors are isolated and reported, never propagated to the core
"""
from __future__ import annotations

import importlib
import importlib.util
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from omega_fire.plugins.exceptions import (
    PluginLoadError,
    PluginNotFoundError,
    PluginValidationError,
)


# ----------------------------------------------------------------------
# Plugin manifest (metadata extracted from plugin module)
# ----------------------------------------------------------------------
@dataclass
class PluginManifest:
    """Metadata extracted from a plugin module.
    
    Attributes:
        name: Plugin name (unique identifier).
        version: Plugin version string.
        author: Plugin author.
        description: Short description.
        capabilities: List of capabilities provided by the plugin.
        dependencies: List of required plugin names.
        hooks: List of hooks implemented by the plugin.
        module_path: Path to the plugin module.
    """
    name: str
    version: str = "0.0.0"
    author: str = "unknown"
    description: str = ""
    capabilities: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    hooks: list[str] = field(default_factory=list)
    module_path: str = ""


# ----------------------------------------------------------------------
# Plugin loader
# ----------------------------------------------------------------------
class PluginLoader:
    """Loads plugins from builtin and external sources.
    
    Attributes:
        builtin_dir: Path to builtin plugins directory.
        external_dir: Path to external plugins directory.
    """
    
    def __init__(
        self,
        builtin_dir: Optional[Path] = None,
        external_dir: Optional[Path] = None,
    ):
        """Initialize the plugin loader.
        
        Args:
            builtin_dir: Path to builtin plugins (default: plugins/builtin/).
            external_dir: Path to external plugins (default: plugins/external/).
        """
        if builtin_dir is None:
            builtin_dir = Path(__file__).parent / "builtin"
        if external_dir is None:
            external_dir = Path(__file__).parent / "external"
        
        self.builtin_dir = builtin_dir
        self.external_dir = external_dir
    
    def discover_plugins(self) -> list[Path]:
        """Discover all available plugin modules.
        
        Returns:
            List of paths to plugin modules (.py files).
        """
        plugins = []
        
        # Discover builtin plugins
        if self.builtin_dir.exists():
            for path in self.builtin_dir.glob("*.py"):
                if path.name != "__init__.py":
                    plugins.append(path)
        
        # Discover external plugins
        if self.external_dir.exists():
            for path in self.external_dir.glob("*.py"):
                if path.name != "__init__.py":
                    plugins.append(path)
        
        return plugins
    
    def load_plugin(self, plugin_path: Path) -> tuple[PluginManifest, Any]:
        """Load a plugin from a file path.
        
        Args:
            plugin_path: Path to the plugin module.
        
        Returns:
            Tuple of (PluginManifest, plugin_module).
        
        Raises:
            PluginLoadError: If the plugin cannot be loaded.
            PluginValidationError: If the plugin does not respect the contract.
        """
        if not plugin_path.exists():
            raise PluginNotFoundError(plugin_path.stem)
        
        try:
            # Create a unique module name to avoid conflicts
            module_name = f"omega_fire.plugins.loaded.{plugin_path.stem}"
            
            # Load the module
            spec = importlib.util.spec_from_file_location(module_name, plugin_path)
            if spec is None or spec.loader is None:
                raise PluginLoadError(plugin_path.stem, "Impossible de créer le spec du module")
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            # Extract manifest
            manifest = self._extract_manifest(module, plugin_path)
            
            # Validate contract
            self._validate_contract(module, manifest)
            
            return manifest, module
        
        except PluginLoadError:
            raise
        except PluginValidationError:
            raise
        except Exception as e:
            raise PluginLoadError(plugin_path.stem, str(e))
    
    def _extract_manifest(self, module: Any, plugin_path: Path) -> PluginManifest:
        """Extract metadata from a plugin module.
        
        Args:
            module: The loaded plugin module.
            plugin_path: Path to the plugin file.
        
        Returns:
            PluginManifest with extracted metadata.
        
        Raises:
            PluginValidationError: If required metadata is missing.
        """
        # Required attributes
        name = getattr(module, "PLUGIN_NAME", None)
        if not name:
            raise PluginValidationError(
                plugin_path.stem,
                "Attribut manquant : PLUGIN_NAME"
            )
        
        version = getattr(module, "PLUGIN_VERSION", "0.0.0")
        author = getattr(module, "PLUGIN_AUTHOR", "unknown")
        description = getattr(module, "PLUGIN_DESCRIPTION", "")
        capabilities = getattr(module, "PLUGIN_CAPABILITIES", [])
        dependencies = getattr(module, "PLUGIN_DEPENDENCIES", [])
        hooks = getattr(module, "PLUGIN_HOOKS", [])
        
        return PluginManifest(
            name=name,
            version=version,
            author=author,
            description=description,
            capabilities=capabilities,
            dependencies=dependencies,
            hooks=hooks,
            module_path=str(plugin_path),
        )
    
    def _validate_contract(self, module: Any, manifest: PluginManifest) -> None:
        """Validate that the plugin respects the expected contract.
        
        Args:
            module: The loaded plugin module.
            manifest: The plugin manifest.
        
        Raises:
            PluginValidationError: If the contract is not respected.
        """
        # Check for required functions
        required_functions = ["activate", "deactivate"]
        for func_name in required_functions:
            if not hasattr(module, func_name):
                raise PluginValidationError(
                    manifest.name,
                    f"Fonction requise manquante : {func_name}()"
                )
            
            func = getattr(module, func_name)
            if not callable(func):
                raise PluginValidationError(
                    manifest.name,
                    f"L'attribut {func_name} n'est pas une fonction"
                )
        
        # Validate capabilities format
        if not isinstance(manifest.capabilities, list):
            raise PluginValidationError(
                manifest.name,
                "PLUGIN_CAPABILITIES doit être une liste"
            )
        
        # Validate hooks format
        if not isinstance(manifest.hooks, list):
            raise PluginValidationError(
                manifest.name,
                "PLUGIN_HOOKS doit être une liste"
            )

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Chargement des plugins depuis builtin/ et external/.
# - Découverte automatique des modules .py dans les répertoires.
# - Extraction du manifest (métadonnées : nom, version, auteur, capacités, hooks).
# - Validation du contrat (fonctions activate/deactivate obligatoires).
# - Isolation des erreurs (un plugin en erreur ne casse pas le chargement des autres).
#
# Pourquoi dans plugins/ (charte) :
# - Logique de chargement pure, aucune règle métier.
# - Aucune dépendance vers domain/, application/, infrastructure/.
# - Utilise ports/plugin.py pour le contrat (via validation).
# - Erreurs isolées et rapportées, jamais propagées au cœur.
#
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier (c'est le rôle de domain/).
# ❌ Pas d'orchestration (c'est le rôle de application/).
# ❌ Pas d'appels système (c'est le rôle de infrastructure/).
# ❌ Pas de dépendance vers d'autres couches.
#
# Points clés :
# - PluginManifest : dataclass avec métadonnées du plugin.
# - PluginLoader : classe principale avec discover_plugins() et load_plugin().
# - discover_plugins() : scan builtin/ et external/ pour trouver les .py.
# - load_plugin() : charge un module, extrait le manifest, valide le contrat.
# - _extract_manifest() : lit PLUGIN_NAME, PLUGIN_VERSION, etc. depuis le module.
# - _validate_contract() : vérifie activate() et deactivate() présents et callables.
# - Gestion d'erreurs : PluginLoadError, PluginNotFoundError, PluginValidationError.
#---------------------------------------------------------------------->            
