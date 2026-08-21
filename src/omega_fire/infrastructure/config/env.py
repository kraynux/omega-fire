# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Environment variables loader.

Loads environment variables from .env file and os.environ.
Provides a simple interface to access configuration values with
type conversion and default values.

This module performs file I/O to read .env files and is therefore
in infrastructure/.
"""
import os
from pathlib import Path
from typing import Any, Optional


class EnvLoader:
    """Loads and manages environment variables."""
    
    def __init__(self, env_file: Optional[Path] = None):
        """Initialize the environment loader.
        
        Args:
            env_file: Path to the .env file (optional)
        """
        self._env_file = env_file
        self._cache: dict[str, str] = {}
        self._loaded = False
    
    def load(self) -> None:
        """Load environment variables from .env file and os.environ.
        
        If a .env file is provided and exists, it is loaded first.
        Then os.environ is merged (os.environ takes precedence).
        """
        if self._loaded:
            return
        
        # Load from .env file if provided
        if self._env_file and self._env_file.exists():
            self._load_env_file(self._env_file)
        
        # Merge with os.environ (os.environ takes precedence)
        for key, value in os.environ.items():
            self._cache[key] = value
        
        self._loaded = True
    
    def _load_env_file(self, env_file: Path) -> None:
        """Load variables from a .env file.
        
        Args:
            env_file: Path to the .env file
        """
        try:
            content = env_file.read_text(encoding="utf-8")
            for line in content.split("\n"):
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue
                
                # Parse KEY=VALUE
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Remove quotes if present
                    if (value.startswith('"') and value.endswith('"')) or \
                       (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]
                    
                    self._cache[key] = value
        
        except Exception:
            # Silently ignore .env file errors
            pass
    
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get an environment variable as string.
        
        Args:
            key: Variable name
            default: Default value if not found
        
        Returns:
            Variable value or default
        """
        if not self._loaded:
            self.load()
        return self._cache.get(key, default)
    
    def get_int(self, key: str, default: int = 0) -> int:
        """Get an environment variable as integer.
        
        Args:
            key: Variable name
            default: Default value if not found or invalid
        
        Returns:
            Integer value or default
        """
        value = self.get(key)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            return default
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get an environment variable as boolean.
        
        Recognizes: true, 1, yes, on → True
                    false, 0, no, off → False
        
        Args:
            key: Variable name
            default: Default value if not found
        
        Returns:
            Boolean value or default
        """
        value = self.get(key)
        if value is None:
            return default
        
        return value.lower() in ("true", "1", "yes", "on")
    
    def get_float(self, key: str, default: float = 0.0) -> float:
        """Get an environment variable as float.
        
        Args:
            key: Variable name
            default: Default value if not found or invalid
        
        Returns:
            Float value or default
        """
        value = self.get(key)
        if value is None:
            return default
        try:
            return float(value)
        except ValueError:
            return default
    
    def get_list(self, key: str, separator: str = ",", default: Optional[list[str]] = None) -> list[str]:
        """Get an environment variable as list of strings.
        
        Args:
            key: Variable name
            separator: List separator (default: comma)
            default: Default value if not found
        
        Returns:
            List of strings or default
        """
        value = self.get(key)
        if value is None:
            return default or []
        return [item.strip() for item in value.split(separator) if item.strip()]
    
    def has(self, key: str) -> bool:
        """Check if an environment variable exists.
        
        Args:
            key: Variable name
        
        Returns:
            True if the variable exists
        """
        if not self._loaded:
            self.load()
        return key in self._cache
    
    def set(self, key: str, value: str) -> None:
        """Set an environment variable in the cache and os.environ.
        
        Args:
            key: Variable name
            value: Variable value
        """
        self._cache[key] = value
        os.environ[key] = value
    
    def get_all(self) -> dict[str, str]:
        """Get all environment variables.
        
        Returns:
            Dictionary of all variables
        """
        if not self._loaded:
            self.load()
        return dict(self._cache)


def load_env(env_file: Optional[Path] = None) -> EnvLoader:
    """Convenience function to load environment variables.
    
    Args:
        env_file: Optional path to .env file
    
    Returns:
        EnvLoader instance
    """
    loader = EnvLoader(env_file)
    loader.load()
    return loader


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Charge les variables d'environnement depuis .env et os.environ
# - Fournit des helpers avec conversion de type (int, bool, float, list)
# - os.environ prend le pas sur le fichier .env (permet l'override)
# Pourquoi dans infrastructure/config/ (charte) :
# - C'est de la configuration technique (variables d'environnement)
# - Le domaine ne doit pas connaître .env
# - L'application/ utilise les settings, pas EnvLoader directement
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier (pas de règles de blacklist, politiques)
# ❌ Pas de dépendance vers domain/, application/ ou interfaces/
# ❌ Pas d'écriture de fichier .env (juste lecture)
# Points clés :
# - EnvLoader : classe principale avec cache interne
# - load() : charge depuis .env puis os.environ
# - get() : retourne une string
# - get_int() / get_bool() / get_float() / get_list() : conversions typées
# - has() : vérifie si une variable existe
# - set() : met à jour le cache et os.environ
# - get_all() : retourne toutes les variables
# - Parsing .env : supporte les commentaires (#), les quotes, les espaces
# - Fonction de convenance : load_env()
# Comment il sera utilisé (aperçu) :
# - app/bootstrap.py chargera les variables au démarrage
# - infrastructure/config/settings.py utilisera EnvLoader pour construire les settings
# - Les tests mockeront les variables d'environnement
#---------------------------------------------------------------------->
