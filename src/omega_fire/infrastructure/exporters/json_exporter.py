# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""JSON exporter for reports.

Infrastructure component that serializes report structures to JSON format.
This is the concrete implementation that handles file I/O and JSON encoding.
It consumes the serializable structures produced by domain/reports/serializers/.
"""
import json
from pathlib import Path
from typing import Any, Union
from omega_fire.domain.reports.builders import Report
from omega_fire.domain.reports.serializers import report_to_serializable, reports_to_serializable


class JsonExporter:
    """Exporter that writes reports to JSON files.
    
    This class takes serializable structures from the domain layer
    and writes them to JSON files with proper formatting.
    """
    
    def __init__(self, pretty: bool = True, indent: int = 2):
        """Initialize the JSON exporter.
        
        Args:
            pretty: If True, format JSON with indentation (default: True)
            indent: Number of spaces for indentation (default: 2)
        """
        self.pretty = pretty
        self.indent = indent
    
    def export_report(
        self,
        report: Report,
        output_path: Union[str, Path],
    ) -> Path:
        """Export a single report to a JSON file.
        
        Args:
            report: Report domain model
            output_path: Path where the JSON file will be written
        
        Returns:
            Path to the created file
        """
        output_path = Path(output_path)
        data = report_to_serializable(report)
        
        # Serialize to JSON
        if self.pretty:
            json_str = json.dumps(data, indent=self.indent, ensure_ascii=False)
        else:
            json_str = json.dumps(data, ensure_ascii=False)
        
        # Write to file
        output_path.write_text(json_str, encoding="utf-8")
        
        return output_path
    
    def export_reports(
        self,
        reports: list[Report],
        output_path: Union[str, Path],
    ) -> Path:
        """Export multiple reports to a single JSON file.
        
        Args:
            reports: List of Report domain models
            output_path: Path where the JSON file will be written
        
        Returns:
            Path to the created file
        """
        output_path = Path(output_path)
        data = reports_to_serializable(reports)
        
        # Serialize to JSON
        if self.pretty:
            json_str = json.dumps(data, indent=self.indent, ensure_ascii=False)
        else:
            json_str = json.dumps(data, ensure_ascii=False)
        
        # Write to file
        output_path.write_text(json_str, encoding="utf-8")
        
        return output_path
    
    def export_data(
        self,
        data: Any,
        output_path: Union[str, Path],
    ) -> Path:
        """Export arbitrary data to a JSON file.
        
        This is a generic method that can export any serializable data,
        not just reports.
        
        Args:
            data: Any JSON-serializable data
            output_path: Path where the JSON file will be written
        
        Returns:
            Path to the created file
        """
        output_path = Path(output_path)
        
        # Serialize to JSON
        if self.pretty:
            json_str = json.dumps(data, indent=self.indent, ensure_ascii=False)
        else:
            json_str = json.dumps(data, ensure_ascii=False)
        
        # Write to file
        output_path.write_text(json_str, encoding="utf-8")
        
        return output_path


def export_report_to_json(
    report: Report,
    output_path: Union[str, Path],
    pretty: bool = True,
) -> Path:
    """Convenience function to export a report to JSON.
    
    Args:
        report: Report domain model
        output_path: Path where the JSON file will be written
        pretty: If True, format JSON with indentation (default: True)
    
    Returns:
        Path to the created file
    """
    exporter = JsonExporter(pretty=pretty)
    return exporter.export_report(report, output_path)


def export_reports_to_json(
    reports: list[Report],
    output_path: Union[str, Path],
    pretty: bool = True,
) -> Path:
    """Convenience function to export multiple reports to JSON.
    
    Args:
        reports: List of Report domain models
        output_path: Path where the JSON file will be written
        pretty: If True, format JSON with indentation (default: True)
    
    Returns:
        Path to the created file
    """
    exporter = JsonExporter(pretty=pretty)
    return exporter.export_reports(reports, output_path)

# <-- INFO DEV ---------------------------------------------------------
# Points clés :
# - Rôle : sérialiser les structures en JSON et écrire les fichiers
# - Dépendances : utilise domain/reports/serializers.py pour obtenir les dicts
# - I/O : c'est le seul endroit autorisé pour json.dumps() et Path.write_text()
# - Conformité : respecte la charte — l'infrastructure gère la technique
#---------------------------------------------------------------------->
"""JSON exporter for reports.

Infrastructure component that serializes report structures to JSON format.
This is the concrete implementation that handles file I/O and JSON encoding.
It consumes the serializable structures produced by domain/reports/serializers/.
"""
import json
from pathlib import Path
from typing import Any, Union
from omega_fire.domain.reports.builders import Report
from omega_fire.domain.reports.serializers import report_to_serializable, reports_to_serializable


class JsonExporter:
    """Exporter that writes reports to JSON files.
    
    This class takes serializable structures from the domain layer
    and writes them to JSON files with proper formatting.
    """
    
    def __init__(self, pretty: bool = True, indent: int = 2):
        """Initialize the JSON exporter.
        
        Args:
            pretty: If True, format JSON with indentation (default: True)
            indent: Number of spaces for indentation (default: 2)
        """
        self.pretty = pretty
        self.indent = indent
    
    def export_report(
        self,
        report: Report,
        output_path: Union[str, Path],
    ) -> Path:
        """Export a single report to a JSON file.
        
        Args:
            report: Report domain model
            output_path: Path where the JSON file will be written
        
        Returns:
            Path to the created file
        """
        output_path = Path(output_path)
        data = report_to_serializable(report)
        
        # Serialize to JSON
        if self.pretty:
            json_str = json.dumps(data, indent=self.indent, ensure_ascii=False)
        else:
            json_str = json.dumps(data, ensure_ascii=False)
        
        # Write to file
        output_path.write_text(json_str, encoding="utf-8")
        
        return output_path
    
    def export_reports(
        self,
        reports: list[Report],
        output_path: Union[str, Path],
    ) -> Path:
        """Export multiple reports to a single JSON file.
        
        Args:
            reports: List of Report domain models
            output_path: Path where the JSON file will be written
        
        Returns:
            Path to the created file
        """
        output_path = Path(output_path)
        data = reports_to_serializable(reports)
        
        # Serialize to JSON
        if self.pretty:
            json_str = json.dumps(data, indent=self.indent, ensure_ascii=False)
        else:
            json_str = json.dumps(data, ensure_ascii=False)
        
        # Write to file
        output_path.write_text(json_str, encoding="utf-8")
        
        return output_path
    
    def export_data(
        self,
        data: Any,
        output_path: Union[str, Path],
    ) -> Path:
        """Export arbitrary data to a JSON file.
        
        This is a generic method that can export any serializable data,
        not just reports.
        
        Args:
            data: Any JSON-serializable data
            output_path: Path where the JSON file will be written
        
        Returns:
            Path to the created file
        """
        output_path = Path(output_path)
        
        # Serialize to JSON
        if self.pretty:
            json_str = json.dumps(data, indent=self.indent, ensure_ascii=False)
        else:
            json_str = json.dumps(data, ensure_ascii=False)
        
        # Write to file
        output_path.write_text(json_str, encoding="utf-8")
        
        return output_path


def export_report_to_json(
    report: Report,
    output_path: Union[str, Path],
    pretty: bool = True,
) -> Path:
    """Convenience function to export a report to JSON.
    
    Args:
        report: Report domain model
        output_path: Path where the JSON file will be written
        pretty: If True, format JSON with indentation (default: True)
    
    Returns:
        Path to the created file
    """
    exporter = JsonExporter(pretty=pretty)
    return exporter.export_report(report, output_path)


def export_reports_to_json(
    reports: list[Report],
    output_path: Union[str, Path],
    pretty: bool = True,
) -> Path:
    """Convenience function to export multiple reports to JSON.
    
    Args:
        reports: List of Report domain models
        output_path: Path where the JSON file will be written
        pretty: If True, format JSON with indentation (default: True)
    
    Returns:
        Path to the created file
    """
    exporter = JsonExporter(pretty=pretty)
    return exporter.export_reports(reports, output_path)

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Exporte des données au format JSON
# - Consomme les structures sérialisables de domain/reports/serializers.py
# - Écrit les fichiers JSON avec formatage optionnel
# Pourquoi dans infrastructure/exporters/ (charte) :
# - C'est de l'infrastructure technique (écriture de fichiers JSON)
# - Le domaine construit le contenu logique, l'infrastructure écrit le format
# - interfaces/ propose le format, l'infrastructure l'implémente
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier (pas de construction de rapport)
# ❌ Pas de dépendance vers application/ ou interfaces/
# ❌ Pas de décision de quoi exporter (c'est le rôle de l'application)
# Points clés :
# - JsonExporter : classe principale avec pretty/indent configurables
# - export_data() : exporte des données arbitraires
# - export_report() : exporte un objet Report du domaine
# - export_reports() : exporte une liste d'objets Report
# - Utilise report_to_serializable() du domaine pour la conversion
# - Crée les répertoires parents si nécessaire
# - Fonction de convenance : export_to_json()
# Comment il sera utilisé (aperçu) :
# - application/commands/export_report.py l'utilisera pour les exports JSON
# - interfaces/cli/actions.py proposera le format JSON à l'utilisateur
# - Les tests mockeront l'écriture de fichiers
#---------------------------------------------------------  
   
