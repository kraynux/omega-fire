# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Configuration loader.

Loads configuration from multiple sources: environment variables,
.env file, and configuration files. Provides a unified interface
for accessing configuration values.

This module performs file I/O to load configuration and is therefore
in infrastructure/.
"""
from pathlib import Path
from typing import Optional
from omega_fire.infrastructure.config.settings import AppSettings, load_settings
from omega_fire.infrastructure.config.paths import AppPaths


class ConfigLoader:
    """Loads and manages application configuration."""
    
    def __init__(
        self,
        base_dir: Optional[Path] = None,
        env_file: Optional[Path] = None,
    ):
        """Initialize the configuration loader.
        
        Args:
            base_dir: Base directory of the application
            env_file: Optional path to .env file
        """
        self._base_dir = base_dir or Path.cwd()
        self._env_file = env_file
        self._settings: Optional[AppSettings] = None
        self._paths: Optional[AppPaths] = None
    
    def load(self) -> AppSettings:
        """Load configuration from all sources.
        
        Returns:
            AppSettings instance
        """
        if self._settings is not None:
            return self._settings
        
        # Determine .env file path
        env_file = self._env_file
        if env_file is None:
            default_env = self._base_dir / ".env"
            if default_env.exists():
                env_file = default_env
        
        # Load settings
        self._settings = load_settings(
            env_file=env_file,
            base_dir=self._base_dir,
        )
        
        # Initialize paths
        self._paths = self._settings.paths
        
        return self._settings
    
    def get_settings(self) -> AppSettings:
        """Get the loaded settings.
        
        Returns:
            AppSettings instance
        
        Raises:
            RuntimeError: If settings haven't been loaded yet
        """
        if self._settings is None:
            raise RuntimeError("Settings not loaded. Call load() first.")
        return self._settings
    
    def get_paths(self) -> AppPaths:
        """Get the application paths.
        
        Returns:
            AppPaths instance
        
        Raises:
            RuntimeError: If settings haven't been loaded yet
        """
        if self._paths is None:
            raise RuntimeError("Paths not loaded. Call load() first.")
        return self._paths
    
    def reload(self) -> AppSettings:
        """Reload configuration from all sources.
        
        Returns:
            Fresh AppSettings instance
        """
        self._settings = None
        self._paths = None
        return self.load()
    
    def is_loaded(self) -> bool:
        """Check if configuration has been loaded.
        
        Returns:
            True if settings are loaded
        """
        return self._settings is not None


def load_config(
    base_dir: Optional[Path] = None,
    env_file: Optional[Path] = None,
) -> AppSettings:
    """Convenience function to load configuration.
    
    Args:
        base_dir: Optional base directory
        env_file: Optional path to .env file
    
    Returns:
        AppSettings instance
    """
    loader = ConfigLoader(base_dir, env_file)
    return loader.load()


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Charge la configuration depuis plusieurs sources (.env, env vars, fichiers)
# - Fournit une interface unifiée pour accéder aux settings et paths
# - Supporte le rechargement à chaud de la configuration
# Pourquoi dans infrastructure/config/ (charte) :
# - C'est de la configuration technique (chargement de fichiers)
# - Le domaine ne doit pas connaître le mécanisme de chargement
# - L'application/ reçoit AppSettings via injection
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier (pas de règles de blacklist, politiques)
# ❌ Pas de dépendance vers domain/, application/ ou interfaces/
# ❌ Pas d'écriture de fichiers de configuration
# Points clés :
# - ConfigLoader : classe principale avec cache interne
# - load() : charge depuis .env + env vars + paths
# - get_settings() / get_paths() : accesseurs avec vérification de chargement
# - reload() : recharge la configuration (utile pour le menu 7.4)
# - is_loaded() : vérifie si la config est chargée
# - Fonction de convenance : load_config()
# Comment il sera utilisé (aperçu) :
# - app/bootstrap.py instanciera ConfigLoader et l'utilisera au démarrage
# - interfaces/cli/actions.py (menu 7.4) appelle directement
#   ctx.container.scanner.scan() pour recharger la configuration — pas
#   de commande application/ dédiée (même mécanisme que le menu 1.3)
# - Les tests mockeront les fichiers de configuration
#---------------------------------------------------------------------->
