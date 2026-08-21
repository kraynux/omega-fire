# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""IP blacklist export logic.

Pure domain logic for preparing ban data for export.
This module transforms BanEntry objects into export-ready structures
(dicts, text lines) but does NOT write any files.
File writing is delegated to infrastructure/exporters/.
"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional
from omega_fire.domain.ip_blacklist.models import BanEntry, BanStatus


class ExportFormat(Enum):
    """Supported export formats."""
    JSON = "json"
    TXT = "txt"
    CSV = "csv"


class ExportScope(Enum):
    """Scope of the export."""
    ACTIVE_ONLY = "active_only"
    ALL = "all"
    BY_BACKEND = "by_backend"
    BY_DATE_RANGE = "by_date_range"


@dataclass
class ExportData:
    """Export-ready data structure.
    
    This is the output of the domain export logic.
    Infrastructure exporters consume this to write files.
    """
    format: ExportFormat
    scope: ExportScope
    entries: list[dict]
    metadata: dict
    generated_at: datetime = datetime.now()
    
    def count(self) -> int:
        """Return the number of entries in the export."""
        return len(self.entries)
    
    def is_empty(self) -> bool:
        """Check if the export contains no entries."""
        return len(self.entries) == 0


def prepare_export(
    entries: list[BanEntry],
    export_format: ExportFormat,
    scope: ExportScope = ExportScope.ACTIVE_ONLY,
    backend_filter: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> ExportData:
    """Prepare ban entries for export.
    
    Transforms domain models into export-ready dictionaries.
    Does NOT write any files.
    
    Args:
        entries: List of ban entries to export
        export_format: Target format (JSON, TXT, CSV)
        scope: Export scope (active only, all, by backend, by date)
        backend_filter: Backend name if scope is BY_BACKEND
        start_date: Start date if scope is BY_DATE_RANGE
        end_date: End date if scope is BY_DATE_RANGE
    
    Returns:
        ExportData ready for infrastructure exporters
    """
    # Apply scope filter
    filtered = _apply_scope(entries, scope, backend_filter, start_date, end_date)
    
    # Transform to export-ready dicts
    export_entries = [_entry_to_dict(e, export_format) for e in filtered]
    
    # Build metadata
    metadata = _build_metadata(filtered, scope, backend_filter)
    
    return ExportData(
        format=export_format,
        scope=scope,
        entries=export_entries,
        metadata=metadata
    )


def _apply_scope(
    entries: list[BanEntry],
    scope: ExportScope,
    backend_filter: Optional[str],
    start_date: Optional[datetime],
    end_date: Optional[datetime]
) -> list[BanEntry]:
    """Apply scope filter to entries."""
    if scope == ExportScope.ACTIVE_ONLY:
        return [e for e in entries if e.is_active()]
    
    elif scope == ExportScope.ALL:
        return entries
    
    elif scope == ExportScope.BY_BACKEND:
        if not backend_filter:
            raise ValueError("backend_filter is required for BY_BACKEND scope")
        return [e for e in entries if e.backend == backend_filter and e.is_active()]
    
    elif scope == ExportScope.BY_DATE_RANGE:
        filtered = entries
        if start_date:
            filtered = [e for e in filtered if e.banned_at >= start_date]
        if end_date:
            filtered = [e for e in filtered if e.banned_at <= end_date]
        return filtered
    
    return entries


def _entry_to_dict(entry: BanEntry, fmt: ExportFormat) -> dict:
    """Transform a BanEntry into an export-ready dictionary.
    
    The structure varies slightly by format to optimize output.
    """
    base = {
        "ip": entry.ip,
        "backend": entry.backend,
        "status": entry.status.value,
        "banned_at": entry.banned_at.isoformat(),
    }
    
    if fmt == ExportFormat.JSON:
        # Full detail for JSON
        base.update({
            "jail_name": entry.jail_name,
            "comment": entry.comment,
            "expires_at": entry.expires_at.isoformat() if entry.expires_at else None,
            "removed_at": entry.removed_at.isoformat() if entry.removed_at else None,
            "removed_by": entry.removed_by,
            "source": entry.source.value,
        })
    
    elif fmt == ExportFormat.TXT:
        # Minimal for plain text (one line per IP)
        base = {"ip": entry.ip}
    
    elif fmt == ExportFormat.CSV:
        # Flat structure for CSV
        base.update({
            "jail_name": entry.jail_name or "",
            "comment": entry.comment or "",
            "expires_at": entry.expires_at.isoformat() if entry.expires_at else "",
            "source": entry.source.value,
        })
    
    return base


def _build_metadata(
    entries: list[BanEntry],
    scope: ExportScope,
    backend_filter: Optional[str]
) -> dict:
    """Build export metadata."""
    backends = list({e.backend for e in entries})
    
    metadata = {
        "total_entries": len(entries),
        "scope": scope.value,
        "backends_included": backends,
    }
    
    if backend_filter:
        metadata["backend_filter"] = backend_filter
    
    return metadata


def format_as_text(export_data: ExportData) -> str:
    """Format export data as plain text (one IP per line).
    
    This is a convenience function for simple text exports.
    Returns a string, not a file.
    """
    lines = [entry["ip"] for entry in export_data.entries]
    return "\n".join(lines)


def format_as_csv(export_data: ExportData) -> str:
    """Format export data as CSV string.
    
    Returns a CSV-formatted string, not a file.
    """
    if not export_data.entries:
        return ""
    
    # Header from first entry keys
    headers = list(export_data.entries[0].keys())
    lines = [",".join(headers)]
    
    for entry in export_data.entries:
        values = [str(entry.get(h, "")) for h in headers]
        lines.append(",".join(values))
    
    return "\n".join(lines)

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit la logique métier de préparation des données pour l'export de la blacklist. Ce module transforme les BanEntry en structures exportables (dictionnaires, lignes de texte) mais n'écrit aucun fichier — l'écriture est déléguée à infrastructure/exporters/.
# Pourquoi dans domain/ : 
# - C'est une règle métier : quel format de données pour quel type d'export
# - Aucune dépendance externe (opère sur les modèles du domaine)
# - Fonctions pures : pas d'I/O, pas d'écriture fichier
# - La séparation est claire : domain/ prépare les données, infrastructure/exporters/ les écrit
# Ce qu'il ne contient PAS (règles projet)
# ❌ Pas d'import depuis infrastructure/ (pas d'écriture fichier)
# ❌ Pas d'import depuis interfaces/ (pas de rendu)
# ❌ Pas de open(), json.dump(), Path.write_text() — aucun I/O
# ❌ Pas de logique de chemin de fichier (ça vit dans infrastructure/config/paths.py)
# Points clés :
# - Séparation stricte : ce module prépare les données, infrastructure/exporters/ les écrit
# - ExportData : structure intermédiaire entre domain et infrastructure
# - prepare_export() : fonction pure qui transforme BanEntry → dictionnaires
# - format_as_text() / format_as_csv() : retournent des chaînes, pas des fichiers
# - Aucun I/O : pas de open(), json.dump(), Path.write_text()
# - Testable en mémoire : peut être testé avec des BanEntry construits manuellement
# Comment il sera utilisé (aperçu) :
# - application/commands/export_report.py appellera prepare_export() pour obtenir ExportData
# - Puis passera ExportData à infrastructure/exporters/json_exporter.py (ou txt, html) pour l'écriture
# - interfaces/cli/actions.py proposera le format et le scope à l'utilisateur
#---------------------------------------------------------------------->
