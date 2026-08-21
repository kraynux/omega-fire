# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Contrat pour le registre d'audit (journalisation des actions)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Protocol


class AuditLevel(str, Enum):
    """Niveau de gravité d'une entrée d'audit."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class AuditEntry:
    """Entrée d'audit immuable.

    Attributs:
        timestamp: date et heure de l'action.
        level: niveau de gravité.
        action: nom de l'action exécutée (ex: "ban_ip", "sync_backends").
        actor: identifiant de l'acteur (ex: "cli:user", "pipeline").
        target: cible de l'action (ex: IP, jail, backend).
        details: détails optionnels (JSON-serializable).
        success: True si l'action a réussi, False sinon.
        error_message: message d'erreur si success=False.
    """
    timestamp: datetime
    level: AuditLevel
    action: str
    actor: str
    target: str
    details: dict | None = None
    success: bool = True
    error_message: str | None = None


class AuditPort(Protocol):
    """Contrat pour le registre d'audit.

    Définit les opérations attendues pour journaliser les actions
    et consulter l'historique d'audit.
    """

    @abstractmethod
    def log(
        self,
        action: str,
        actor: str,
        target: str,
        *,
        level: AuditLevel = AuditLevel.INFO,
        details: dict | None = None,
        success: bool = True,
        error_message: str | None = None,
    ) -> None:
        """Enregistre une entrée d'audit.

        Args:
            action: nom de l'action exécutée.
            actor: identifiant de l'acteur.
            target: cible de l'action.
            level: niveau de gravité (défaut: INFO).
            details: détails optionnels.
            success: True si l'action a réussi.
            error_message: message d'erreur si échec.
        """
        ...

    @abstractmethod
    def get_recent(self, limit: int = 50) -> list[AuditEntry]:
        """Récupère les N entrées d'audit les plus récentes.

        Args:
            limit: nombre maximum d'entrées à retourner.

        Returns:
            Liste d'AuditEntry triées par timestamp décroissant.
        """
        ...

    @abstractmethod
    def search(
        self,
        *,
        action: str | None = None,
        actor: str | None = None,
        target: str | None = None,
        level: AuditLevel | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[AuditEntry]:
        """Recherche des entrées d'audit selon des critères.

        Args:
            action: filtre par nom d'action.
            actor: filtre par acteur.
            target: filtre par cible.
            level: filtre par niveau.
            since: filtre par date minimale.
            limit: nombre maximum d'entrées.

        Returns:
            Liste d'AuditEntry correspondant aux critères.
        """
        ...

    @abstractmethod
    def clear(self, older_than: datetime | None = None) -> int:
        """Supprime les entrées d'audit.

        Args:
            older_than: si fourni, supprime uniquement les entrées avant cette date.
                       Si None, supprime tout.

        Returns:
            Nombre d'entrées supprimées.
        """
        ...

    @abstractmethod
    def delete_oldest(self, count: int) -> int:
        """Supprime les N entrées d'audit les plus anciennes, en
        conservant les plus récentes.

        Complète clear(older_than=...) pour un nettoyage par VOLUME
        plutôt que par ÂGE — utile quand l'utilisateur veut réduire la
        taille du journal sans avoir à raisonner en date.

        Args:
            count: nombre d'entrées les plus anciennes à supprimer. Si
                count dépasse le nombre total d'entrées, tout est
                supprimé (équivalent à clear()).

        Returns:
            Nombre d'entrées effectivement supprimées.
        """
        ...
 # <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit le contrat (Protocol) pour le registre d'audit.
# - Fournit AuditEntry (dataclass frozen) et AuditLevel (enum).
# - Spécifie les opérations : log(), get_recent(), search(), clear(), delete_oldest()
#
# Pourquoi dans ports/ (charte) :
# - C'est un contrat attendu par le cœur applicatif (application/pipeline/hooks/)
# - Pas d'implémentation concrète (c'est le rôle de infrastructure/logging/)
# - Aucune dépendance vers domain/, application/, infrastructure/, interfaces/
#
# Ce qu'il ne contient PAS :
# ❌ Pas d'implémentation concrète (écriture fichier, SQLite)
# ❌ Pas d'import depuis domain/
# ❌ Pas d'import depuis application/
# ❌ Pas d'import depuis infrastructure/
# ❌ Pas d'import depuis interfaces/
# ❌ Pas de logique de rotation, compression, archivage
#    delete_oldest() couvrent la purge simple, pas la rotation)
#
# Points clés :
# - AuditLevel : enum (info, warning, error, critical)
# - AuditEntry : dataclass frozen avec timestamp, level, action, actor, target,
#   details, success, error_message
# - AuditPort : Protocol définissant log(), get_recent(), search(), clear()
# - Toutes les méthodes sont abstraites (@abstractmethod implicite via Protocol)
# - AuditEntry est immuable (frozen=True, slots=True)
#
# Comment il sera utilisé (aperçu) :
# - application/pipeline/hooks/audit_hook.py appellera audit_port.log()
# - infrastructure/logging/audit_logger.py implémentera AuditPort
# - interfaces/cli/actions.py appellera audit_port.get_recent() pour menu 1.4
# - Les tests mockeront AuditPort pour valider le pipeline sans I/O réel
#---------------------------------------------------------------------->       
