# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Contrat pour les exporteurs de rapports (JSON, TXT, HTML)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Protocol


class ExportFormat(str, Enum):
    """Format d'export supporté."""
    JSON = "json"
    TXT = "txt"
    HTML = "html"


@dataclass(frozen=True, slots=True)
class ExportResult:
    """Résultat d'un export.

    Attributs:
        path: chemin du fichier exporté.
        format: format d'export (json, txt, html).
        size_bytes: taille du fichier en octets.
        record_count: nombre d'enregistrements exportés.
    """
    path: Path
    format: ExportFormat
    size_bytes: int
    record_count: int


class ExporterPort(Protocol):
    """Contrat pour les exporteurs de rapports.

    Définit les opérations attendues pour exporter des données
    vers différents formats (JSON, TXT, HTML).
    """

    @abstractmethod
    def export(
        self,
        data: Any,
        output_path: Path,
        format: ExportFormat,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> ExportResult:
        """Exporte des données vers un fichier.

        Args:
            data: données à exporter (doit être sérialisable).
            output_path: chemin du fichier de sortie.
            format: format d'export (json, txt, html).
            metadata: métadonnées optionnelles (titre, description, etc.).

        Returns:
            ExportResult avec chemin, format, taille, nombre d'enregistrements.

        Raises:
            ExportError: si l'export échoue (écriture, format non supporté).
        """
        ...

    @abstractmethod
    def supports_format(self, format: ExportFormat) -> bool:
        """Vérifie si cet exporteur supporte un format donné.

        Args:
            format: format à vérifier.

        Returns:
            True si le format est supporté.
        """
        ...

    @abstractmethod
    def list_supported_formats(self) -> list[ExportFormat]:
        """Liste les formats supportés par cet exporteur.

        Returns:
            Liste de ExportFormat.
        """
        ...

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit le contrat (Protocol) pour les exporteurs de rapports.
# - Fournit ExportFormat (enum) et ExportResult (dataclass frozen).
# - Spécifie les opérations : export(), supports_format(), list_supported_formats().
#
# Pourquoi dans ports/ (charte) :
# - C'est un contrat attendu par le cœur applicatif (application/commands/export_report.py)
# - Pas d'implémentation concrète (c'est le rôle de infrastructure/exporters/)
# - Aucune dépendance vers domain/, application/, infrastructure/, interfaces/
#
# Ce qu'il ne contient PAS :
# ❌ Pas d'implémentation concrète (écriture JSON, HTML, TXT)
# ❌ Pas d'import depuis domain/
# ❌ Pas d'import depuis application/
# ❌ Pas d'import depuis infrastructure/
# ❌ Pas d'import depuis interfaces/
# ❌ Pas de logique de template (Jinja2)
#
# Points clés :
# - ExportFormat : enum (json, txt, html)
# - ExportResult : dataclass frozen avec path, format, size_bytes, record_count
# - ExporterPort : Protocol définissant export(), supports_format(), list_supported_formats()
# - Toutes les méthodes sont abstraites (via Protocol)
# - ExportResult est immuable (frozen=True, slots=True)
#
# Comment il sera utilisé (aperçu) :
# - application/commands/export_report.py appellera exporter_port.export()
# - infrastructure/exporters/json_exporter.py implémentera ExporterPort
# - infrastructure/exporters/txt_exporter.py implémentera ExporterPort
# - infrastructure/exporters/html_exporter.py implémentera ExporterPort
# - interfaces/cli/actions.py proposera les formats via list_supported_formats()
#---------------------------------------------------------------------->        
