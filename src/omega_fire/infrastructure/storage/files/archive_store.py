# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Archive file storage (tar.gz).

Provides operations for creating and extracting tar.gz archives.
Used for backups, snapshots, and bulk exports. All paths are relative to var/.

This module performs real file I/O and is therefore in infrastructure/.
"""
import tarfile
import gzip
from pathlib import Path
from typing import Optional
from datetime import datetime
from omega_fire.core.exceptions import CoreError


class ArchiveStoreError(CoreError):
    """Exception raised when archive operations fail."""
    pass


class ArchiveStore:
    """Archive file storage for tar.gz files."""
    
    def __init__(self, base_dir: Path):
        """Initialize the archive store.
        
        Args:
            base_dir: Base directory for archives (e.g., var/backups/)
        """
        self._base_dir = base_dir
        self._base_dir.mkdir(parents=True, exist_ok=True)
    
    def create_archive(
        self,
        archive_name: str,
        source_paths: list[Path],
        base_path: Optional[Path] = None,
    ) -> Path:
        """Create a tar.gz archive from multiple files/directories.
        
        Args:
            archive_name: Name of the archive (without extension)
            source_paths: List of files/directories to include
            base_path: Optional base path for relative paths in archive
        
        Returns:
            Path to the created archive
        
        Raises:
            ArchiveStoreError: If creation fails
        """
        try:
            archive_path = self._base_dir / f"{archive_name}.tar.gz"
            
            with tarfile.open(archive_path, "w:gz") as tar:
                for source in source_paths:
                    if not source.exists():
                        continue
                    
                    arcname = source.name if base_path is None else str(source.relative_to(base_path))
                    tar.add(source, arcname=arcname)
            
            return archive_path
        
        except Exception as e:
            raise ArchiveStoreError(f"Failed to create archive {archive_name}: {e}") from e
    
    def extract_archive(
        self,
        archive_path: Path,
        dest_dir: Path,
    ) -> None:
        """Extract a tar.gz archive to a destination directory.
        
        Args:
            archive_path: Path to the archive file
            dest_dir: Destination directory for extraction
        
        Raises:
            ArchiveStoreError: If extraction fails
        """
        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
            
            with tarfile.open(archive_path, "r:gz") as tar:
                tar.extractall(dest_dir)
        
        except Exception as e:
            raise ArchiveStoreError(f"Failed to extract archive {archive_path}: {e}") from e
    
    def list_archives(self, pattern: str = "*.tar.gz") -> list[Path]:
        """List archive files matching a pattern.
        
        Args:
            pattern: Glob pattern (default: "*.tar.gz")
        
        Returns:
            List of archive file paths
        """
        return list(self._base_dir.glob(pattern))
    
    def get_archive_info(self, archive_path: Path) -> dict:
        """Get information about an archive.
        
        Args:
            archive_path: Path to the archive file
        
        Returns:
            Dictionary with archive information
        
        Raises:
            ArchiveStoreError: If info retrieval fails
        """
        try:
            stat = archive_path.stat()
            
            return {
                "path": str(archive_path),
                "name": archive_path.name,
                "size_bytes": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            }
        
        except Exception as e:
            raise ArchiveStoreError(f"Failed to get info for {archive_path}: {e}") from e
    
    def delete_archive(self, archive_path: Path) -> bool:
        """Delete an archive file.
        
        Args:
            archive_path: Path to the archive file
        
        Returns:
            True if deleted, False if not found
        """
        if archive_path.exists():
            archive_path.unlink()
            return True
        return False


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Fournit des opérations de création et extraction d'archives tar.gz
# - Utilisé pour les backups, snapshots et exports en masse
# - Tous les chemins sont relatifs à var/ (pas dans le code source)
# Pourquoi dans infrastructure/ (charte) :
# - C'est une implémentation technique qui fait des I/O réels (fichiers, compression)
# - Le domaine ne doit pas connaître le système de fichiers (règle de dépendance)
# - L'application/ utilise les repositories via ports/, pas cette classe
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier (pas de règles de blacklist, politiques)
# ❌ Pas de dépendance vers domain/, application/ ou interfaces/
# ❌ Pas de validation métier (c'est le rôle du domaine)
# Points clés :
# - ArchiveStore : classe principale avec base_dir configurable
# - create_archive() : crée une archive tar.gz à partir de fichiers/répertoires
# - extract_archive() : extrait une archive vers un répertoire
# - list_archives() : liste les archives avec un pattern glob
# - get_archive_info() : retourne les métadonnées d'une archive (taille, dates)
# - delete_archive() : supprime une archive
# - Gestion des erreurs : ArchiveStoreError pour toute opération échouée
# - Création automatique des répertoires parents
# - Support de la compression gzip
# Comment il sera utilisé (aperçu) :
# - application/commands/backup_state.py l'utilisera pour créer les backups
# - application/commands/restore_state.py l'utilisera pour extraire les backups
# - Les tests utiliseront un répertoire temporaire
#---------------------------------------------------------------------->
