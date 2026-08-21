# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Core results model.

Defines the Result[T] dataclass, which represents a normalized operation result.
This is the standard return type for operations that can fail without raising
exceptions. It contains success indicator, data on success, error on failure,
and information about skipped elements (degraded mode).
"""
from dataclasses import dataclass, field
from typing import Generic, TypeVar, Optional, Any
from datetime import datetime


# Generic type parameter for the result data
T = TypeVar('T')


@dataclass
class Result(Generic[T]):
    """A normalized operation result.
    
    Represents the outcome of an operation that can succeed or fail.
    This is an alternative to raising exceptions for expected failures,
    especially in degraded mode or when partial execution is acceptable.
    
    Attributes:
        success: True if the operation succeeded, False otherwise
        data: The result data if successful (type T)
        error: Error message if failed
        skipped: List of elements that were skipped (e.g., due to missing capabilities)
        metadata: Optional dictionary with additional context
        timestamp: When the result was created
    """
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    skipped: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def is_success(self) -> bool:
        """Check if the operation succeeded.
        
        Returns:
            True if success is True
        """
        return self.success
    
    def is_failure(self) -> bool:
        """Check if the operation failed.
        
        Returns:
            True if success is False
        """
        return not self.success
    
    def has_skipped(self) -> bool:
        """Check if any elements were skipped.
        
        Returns:
            True if the skipped list is not empty
        """
        return len(self.skipped) > 0
    
    def get_data(self, default: Optional[T] = None) -> Optional[T]:
        """Get the result data or a default value.
        
        Args:
            default: Value to return if data is None
        
        Returns:
            The data if present, otherwise the default value
        """
        return self.data if self.data is not None else default
    
    def get_error(self, default: str = "Unknown error") -> str:
        """Get the error message or a default value.
        
        Args:
            default: Value to return if error is None
        
        Returns:
            The error message if present, otherwise the default value
        """
        return self.error if self.error is not None else default
    
    def add_skipped(self, item: str) -> None:
        """Add an item to the skipped list.
        
        Args:
            item: The item that was skipped
        """
        if item not in self.skipped:
            self.skipped.append(item)
    
    def add_metadata(self, key: str, value: Any) -> None:
        """Add a metadata entry.
        
        Args:
            key: Metadata key
            value: Metadata value
        """
        self.metadata[key] = value
    
    def to_dict(self) -> dict[str, Any]:
        """Convert the result to a dictionary.
        
        Returns:
            Dictionary representation of the result
        """
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "skipped": self.skipped,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }
    
    def __str__(self) -> str:
        """Return string representation.
        
        Returns:
            String like "Result(success=True, data=...)" or "Result(success=False, error=...)"
        """
        if self.success:
            return f"Result(success=True, data={self.data})"
        return f"Result(success=False, error={self.error})"


def success_result(data: T, metadata: Optional[dict[str, Any]] = None) -> Result[T]:
    """Create a successful result.
    
    Args:
        data: The result data
        metadata: Optional metadata
    
    Returns:
        Result with success=True
    """
    return Result(
        success=True,
        data=data,
        metadata=metadata or {},
    )


def failure_result(
    error: str,
    skipped: Optional[list[str]] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> Result[Any]:
    """Create a failed result.
    
    Args:
        error: Error message
        skipped: Optional list of skipped items
        metadata: Optional metadata
    
    Returns:
        Result with success=False
    """
    return Result(
        success=False,
        error=error,
        skipped=skipped or [],
        metadata=metadata or {},
    )


def partial_result(
    data: T,
    skipped: list[str],
    metadata: Optional[dict[str, Any]] = None,
) -> Result[T]:
    """Create a partial result (success with skipped items).
    
    This is used when an operation partially succeeded, for example
    in degraded mode where some steps were skipped due to missing
    capabilities.
    
    Args:
        data: The result data
        skipped: List of skipped items
        metadata: Optional metadata
    
    Returns:
        Result with success=True and non-empty skipped list
    """
    return Result(
        success=True,
        data=data,
        skipped=skipped,
        metadata=metadata or {},
    )


def merge_results(results: list[Result[Any]]) -> Result[Any]:
    """Merge multiple results into a single result.
    
    The merged result is successful only if all input results are successful.
    Skipped items are aggregated from all results.
    
    Args:
        results: List of results to merge
    
    Returns:
        Merged result
    """
    if not results:
        return success_result(None)
    
    all_success = all(r.success for r in results)
    all_skipped = []
    all_metadata = {}
    
    for result in results:
        all_skipped.extend(result.skipped)
        all_metadata.update(result.metadata)
    
    if all_success:
        # All succeeded — return the last data (or merge if needed)
        last_data = results[-1].data if results else None
        return partial_result(last_data, all_skipped, all_metadata) if all_skipped else success_result(last_data, all_metadata)
    
    # At least one failed — return failure with aggregated skipped
    errors = [r.error for r in results if not r.success and r.error]
    error_msg = "; ".join(errors) if errors else "Unknown error"
    return failure_result(error_msg, all_skipped, all_metadata)

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit la dataclass Result[T] qui représente un résultat normalisé d'une opération. C'est le type de retour standardisé pour les opérations qui peuvent échouer sans lever d'exception. Il contient un indicateur de succès, les données en cas de succès, l'erreur en cas d'échec, et des informations sur les éléments ignorés (mode dégradé).
# Pourquoi dans core/ (charte) :
# - C'est un modèle transverse utilisé par tout le système
# - Aucune dépendance externe (pas de domain/, application/, infrastructure/)
# - Testable en mémoire pure
# - Utilisé par application/ pour retourner des résultats structurés
# Ce qu'il ne contient PAS (règles projet) :
# ❌ Pas d'import depuis domain/, application/, infrastructure/, interfaces/
# ❌ Pas de logique métier spécifique
# ❌ Pas de subprocess, sqlite3, rich — aucun I/O
# Points clés :
# - Result[T] : dataclass générique avec success, data, error, skipped, metadata, timestamp
# - Méthodes de vérification : is_success(), is_failure(), has_skipped()
# - Méthodes d'accès : get_data(), get_error() avec valeurs par défaut
# - Méthodes de modification : add_skipped(), add_metadata()
# - Sérialisation : to_dict() pour conversion en dictionnaire
# - Factory functions : success_result(), failure_result(), partial_result()
# - merge_results() : fusionne plusieurs résultats en un seul
# - Mode dégradé : le champ skipped permet de tracker les éléments ignorés
# - Aucune dépendance externe : utilise uniquement dataclasses, typing, datetime
# - Aucun I/O : ne lit ni n'écrit aucun fichier
# Comment il sera utilisé (aperçu) :
# - application/commands/ban_ip.py retournera un Result pour indiquer le succès/échec
# - application/pipeline/executor.py retournera un Result avec les steps ignorés en mode dégradé
# - interfaces/cli/actions.py affichera le résultat de manière lisible
# - Les tests vérifieront les résultats sans dépendre d'exceptions
#---------------------------------------------------------------------->
