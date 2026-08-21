# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Text file storage.

Provides simple text file read/write operations for logs, reports,
and temporary data. All paths are relative to var/.

This module performs real file I/O and is therefore in infrastructure/.
"""
from pathlib import Path
from typing import Optional
from omega_fire.core.exceptions import CoreError


class TextStoreError(CoreError):
    """Exception raised when text store operations fail."""
    pass


class TextStore:
    """Simple text file storage."""
    
    def __init__(self, base_dir: Path):
        """Initialize the text store.
        
        Args:
            base_dir: Base directory for text files (e.g., var/)
        """
        self._base_dir = base_dir
        self._base_dir.mkdir(parents=True, exist_ok=True)
    
    def save(self, relative_path: str, content: str, encoding: str = "utf-8") -> Path:
        """Save content to a text file.
        
        Args:
            relative_path: Path relative to base_dir
            content: Text content to write
            encoding: File encoding (default: utf-8)
        
        Returns:
            Path to the created file
        
        Raises:
            TextStoreError: If save fails
        """
        try:
            file_path = self._base_dir / relative_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding=encoding)
            return file_path
        except Exception as e:
            raise TextStoreError(f"Failed to save text to {relative_path}: {e}") from e
    
    def load(self, relative_path: str, encoding: str = "utf-8") -> str:
        """Load content from a text file.
        
        Args:
            relative_path: Path relative to base_dir
            encoding: File encoding (default: utf-8)
        
        Returns:
            Text content
        
        Raises:
            TextStoreError: If load fails or file doesn't exist
        """
        try:
            file_path = self._base_dir / relative_path
            
            if not file_path.exists():
                raise TextStoreError(f"File not found: {relative_path}")
            
            return file_path.read_text(encoding=encoding)
        
        except Exception as e:
            if isinstance(e, TextStoreError):
                raise
            raise TextStoreError(f"Failed to load text from {relative_path}: {e}") from e
    
    def append(self, relative_path: str, content: str, encoding: str = "utf-8") -> Path:
        """Append content to a text file.
        
        Args:
            relative_path: Path relative to base_dir
            content: Text content to append
            encoding: File encoding (default: utf-8)
        
        Returns:
            Path to the file
        
        Raises:
            TextStoreError: If append fails
        """
        try:
            file_path = self._base_dir / relative_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, "a", encoding=encoding) as f:
                f.write(content)
            
            return file_path
        except Exception as e:
            raise TextStoreError(f"Failed to append text to {relative_path}: {e}") from e
    
    def exists(self, relative_path: str) -> bool:
        """Check if a text file exists.
        
        Args:
            relative_path: Path relative to base_dir
        
        Returns:
            True if the file exists
        """
        file_path = self._base_dir / relative_path
        return file_path.exists()
    
    def delete(self, relative_path: str) -> bool:
        """Delete a text file.
        
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
    
    def rename(self, relative_path: str, new_relative_path: str) -> Path:
        """Rename (or move) a text file within base_dir.
        
        Args:
            relative_path: Current path relative to base_dir
            new_relative_path: New path relative to base_dir
        
        Returns:
            Path to the renamed file
        
        Raises:
            TextStoreError: If the source file doesn't exist, or if a
                file already exists at the destination (never silently
                overwrites an existing file).
        """
        try:
            source_path = self._base_dir / relative_path
            dest_path = self._base_dir / new_relative_path

            if not source_path.exists():
                raise TextStoreError(f"File not found: {relative_path}")

            if dest_path.exists():
                raise TextStoreError(
                    f"A file already exists at destination: {new_relative_path}"
                )

            dest_path.parent.mkdir(parents=True, exist_ok=True)
            source_path.rename(dest_path)
            return dest_path

        except Exception as e:
            if isinstance(e, TextStoreError):
                raise
            raise TextStoreError(
                f"Failed to rename {relative_path} to {new_relative_path}: {e}"
            ) from e
    
    
    def list_files(self, pattern: str = "*.txt") -> list[Path]:
        """List text files matching a pattern.
        
        Args:
            pattern: Glob pattern (default: "*.txt")
        
        Returns:
            List of file paths
        """
        return list(self._base_dir.rglob(pattern))


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Fournit des opérations simples de lecture/écriture de fichiers texte
# - Utilisé pour les logs, rapports et données temporaires
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
# - TextStore : classe principale avec base_dir configurable
# - save() : écrit un fichier texte
# - load() : lit un fichier texte
# - append() : ajoute du contenu à la fin d'un fichier
# - exists() : vérifie si un fichier existe
# - delete() : supprime un fichier
# - rename() : renomme/déplace un fichier — échoue explicitement si la
#   source est absente ou si la destination existe déjà (jamais d'écrasement
#   silencieux)
# - list_files() : liste les fichiers texte avec un pattern glob
# - Gestion des erreurs : TextStoreError pour toute opération échouée
# - Création automatique des répertoires parents
# - Encodage configurable (défaut: UTF-8)
# Comment il sera utilisé (aperçu) :
# - infrastructure/exporters/txt_exporter.py l'utilisera pour les exports texte
# - infrastructure/logging/app_logger.py l'utilisera pour les logs
# - Les tests utiliseront un répertoire temporaire
#---------------------------------------------------------------------->
