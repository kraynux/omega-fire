# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""JSON file storage.

Provides simple JSON file read/write operations for configuration
files, exports, and temporary data. All paths are relative to var/.

This module performs real file I/O and is therefore in infrastructure/.
"""
import json
from pathlib import Path
from typing import Any, Optional
from omega_fire.core.exceptions import CoreError


class JsonStoreError(CoreError):
    """Exception raised when JSON store operations fail."""
    pass


class JsonStore:
    """Simple JSON file storage."""
    
    def __init__(self, base_dir: Path):
        """Initialize the JSON store.
        
        Args:
            base_dir: Base directory for JSON files (e.g., var/)
        """
        self._base_dir = base_dir
        self._base_dir.mkdir(parents=True, exist_ok=True)
    
    def save(self, relative_path: str, data: Any, pretty: bool = True) -> Path:
        """Save data to a JSON file.
        
        Args:
            relative_path: Path relative to base_dir (e.g., "config/settings.json")
            data: Data to serialize (must be JSON-serializable)
            pretty: If True, format with indentation
        
        Returns:
            Path to the created file
        
        Raises:
            JsonStoreError: If save fails
        """
        try:
            file_path = self._base_dir / relative_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            if pretty:
                content = json.dumps(data, indent=2, ensure_ascii=False)
            else:
                content = json.dumps(data, ensure_ascii=False)
            
            file_path.write_text(content, encoding="utf-8")
            return file_path
        
        except Exception as e:
            raise JsonStoreError(f"Failed to save JSON to {relative_path}: {e}") from e
    
    def load(self, relative_path: str) -> Any:
        """Load data from a JSON file.
        
        Args:
            relative_path: Path relative to base_dir
        
        Returns:
            Deserialized data
        
        Raises:
            JsonStoreError: If load fails or file doesn't exist
        """
        try:
            file_path = self._base_dir / relative_path
            
            if not file_path.exists():
                raise JsonStoreError(f"File not found: {relative_path}")
            
            content = file_path.read_text(encoding="utf-8")
            return json.loads(content)
        
        except json.JSONDecodeError as e:
            raise JsonStoreError(f"Invalid JSON in {relative_path}: {e}") from e
        except Exception as e:
            if isinstance(e, JsonStoreError):
                raise
            raise JsonStoreError(f"Failed to load JSON from {relative_path}: {e}") from e
    
    def exists(self, relative_path: str) -> bool:
        """Check if a JSON file exists.
        
        Args:
            relative_path: Path relative to base_dir
        
        Returns:
            True if the file exists
        """
        file_path = self._base_dir / relative_path
        return file_path.exists()
    
    def delete(self, relative_path: str) -> bool:
        """Delete a JSON file.
        
        Args:
            relative_path: Path relative to base_dir
        
        Returns:
            True if deleted, False if not found
        """
        file_path = self._base_dir / relative_path
        if file_path.exists():
            file_path.unlink()
            return True
        return False
    
    def list_files(self, pattern: str = "*.json") -> list[Path]:
        """List JSON files matching a pattern.
        
        Args:
            pattern: Glob pattern (default: "*.json")
        
        Returns:
            List of file paths
        """
        return list(self._base_dir.rglob(pattern))


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Fournit des opérations simples de lecture/écriture de fichiers JSON
# - Utilisé pour la configuration, les exports et les données temporaires
# - Tous les chemins sont relatifs à var/ (pas dans le code source)
# Pourquoi dans infrastructure/ (charte) :
# - C'est une implémentation technique qui fait des I/O réels (fichiers)
# - Le domaine ne doit pas connaître le système de fichiers (règle de dépendance)
# - L'application/ utilise les repositories via ports/, pas cette classe
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier (pas de règles de blacklist, politiques)
# ❌ Pas de dépendance vers domain/, application/ ou interfaces/
# ❌ Pas de validation métier (c'est le rôle du domaine)
# Points clés :
# - JsonStore : classe principale avec base_dir configurable
# - save() : sérialise et écrit un fichier JSON (pretty ou compact)
# - load() : lit et désérialise un fichier JSON
# - exists() : vérifie si un fichier existe
# - delete() : supprime un fichier
# - list_files() : liste les fichiers JSON avec un pattern glob
# - Gestion des erreurs : JsonStoreError pour toute opération échouée
# - Création automatique des répertoires parents
# - Encodage UTF-8 pour supporter les caractères spéciaux
# Comment il sera utilisé (aperçu) :
# - infrastructure/config/loader.py l'utilisera pour charger la configuration
# - infrastructure/exporters/json_exporter.py l'utilisera pour les exports
# - Les tests utiliseront un répertoire temporaire
#---------------------------------------------------------------------->
