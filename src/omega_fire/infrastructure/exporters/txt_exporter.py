# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Text exporter.

Exports data to plain text format. Generates human-readable text
representations of reports and data structures.

This module performs file I/O and is therefore in infrastructure/.
"""
from pathlib import Path
from typing import Any, Union
from omega_fire.domain.reports.serializers import report_to_serializable


class TxtExporter:
    """Exporter that writes data to plain text files.
    
    Generates human-readable text representations suitable for
    viewing in terminals or text editors.
    """
    
    def __init__(self, separator: str = "=" * 80):
        """Initialize the text exporter.
        
        Args:
            separator: Section separator string
        """
        self.separator = separator
    
    def export_data(self, data: Any, output_path: Union[str, Path]) -> Path:
        """Export arbitrary data to a text file.
        
        Args:
            data: Data to export (dict, list, or primitive)
            output_path: Path where the text file will be written
        
        Returns:
            Path to the created file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        content = self._format_data(data)
        output_path.write_text(content, encoding="utf-8")
        return output_path
    
    def export_report(self, report, output_path: Union[str, Path]) -> Path:
        """Export a Report domain object to a text file.
        
        Args:
            report: Report domain object
            output_path: Path where the text file will be written
        
        Returns:
            Path to the created file
        """
        data = report_to_serializable(report)
        content = self._format_report(data)
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
        return output_path
    
    def _format_data(self, data: Any, indent: int = 0) -> str:
        """Format data as human-readable text.
        
        Args:
            data: Data to format
            indent: Indentation level
        
        Returns:
            Formatted text string
        """
        lines = []
        prefix = "  " * indent
        
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    lines.append(f"{prefix}{key}:")
                    lines.append(self._format_data(value, indent + 1))
                else:
                    lines.append(f"{prefix}{key}: {value}")
        
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, (dict, list)):
                    lines.append(f"{prefix}-")
                    lines.append(self._format_data(item, indent + 1))
                else:
                    lines.append(f"{prefix}- {item}")
        
        else:
            lines.append(f"{prefix}{data}")
        
        return "\n".join(lines)
    
    def _format_report(self, data: dict) -> str:
        """Format a report as human-readable text.
        
        Args:
            data: Report data dictionary
        
        Returns:
            Formatted report text
        """
        lines = []
        
        # Header
        lines.append(self.separator)
        lines.append(f"  {data.get('title', 'Report')}")
        lines.append(f"  Generated: {data.get('generated_at', 'N/A')}")
        lines.append(self.separator)
        lines.append("")
        
        # Sections
        for section in data.get("sections", []):
            lines.append(f"## {section.get('name', 'Section')}")
            lines.append("-" * 40)
            
            content = section.get("content")
            if isinstance(content, (dict, list)):
                lines.append(self._format_data(content))
            else:
                lines.append(str(content))
            
            lines.append("")
        
        # Metadata
        if data.get("metadata"):
            lines.append(self.separator)
            lines.append("Metadata:")
            lines.append(self._format_data(data["metadata"]))
        
        return "\n".join(lines)


def export_to_txt(data: Any, output_path: Union[str, Path]) -> Path:
    """Convenience function to export data to text.
    
    Args:
        data: Data to export
        output_path: Path where the text file will be written
    
    Returns:
        Path to the created file
    """
    exporter = TxtExporter()
    return exporter.export_data(data, output_path)


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Exporte des données au format texte brut lisible
# - Génère des représentations textuelles adaptées aux terminaux
# - Formatage hiérarchique pour les structures complexes
# Pourquoi dans infrastructure/exporters/ (charte) :
# - C'est de l'infrastructure technique (écriture de fichiers texte)
# - Le domaine construit le contenu logique, l'infrastructure écrit le format
# - interfaces/ propose le format, l'infrastructure l'implémente
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier (pas de construction de rapport)
# ❌ Pas de dépendance vers application/ ou interfaces/
# ❌ Pas de décision de quoi exporter (c'est le rôle de l'application)
# Points clés :
# - TxtExporter : classe principale avec separator configurable
# - export_data() : exporte des données arbitraires
# - export_report() : exporte un objet Report avec formatage spécial
# - _format_data() : formate récursivement dict/list en texte indenté
# - _format_report() : formatage spécifique pour les rapports (header, sections)
# - Crée les répertoires parents si nécessaire
# - Fonction de convenance : export_to_txt()
# Comment il sera utilisé (aperçu) :
# - application/commands/export_report.py l'utilisera pour les exports TXT
# - interfaces/cli/actions.py proposera le format TXT à l'utilisateur
# - Les tests mockeront l'écriture de fichiers
#---------------------------------------------------------------------->
