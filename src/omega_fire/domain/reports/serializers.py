# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Domain reports serializers.

Pure domain logic for transforming reports into serializable structures.
This module converts domain models into dictionaries that can be serialized
by infrastructure/exporters/. It does NOT perform any actual serialization
(JSON, TXT, HTML) — that is the responsibility of infrastructure/.
"""
from typing import Any
from omega_fire.domain.reports.builders import Report, ReportSection


def report_to_dict(report: Report) -> dict[str, Any]:
    """Convert a Report to a serializable dictionary.
    
    Args:
        report: Report domain model
    
    Returns:
        Dictionary representation suitable for serialization
    """
    return {
        "title": report.title,
        "generated_at": report.generated_at.isoformat(),
        "sections": [section_to_dict(section) for section in report.sections],
        "metadata": report.metadata,
    }


def section_to_dict(section: ReportSection) -> dict[str, Any]:
    """Convert a ReportSection to a serializable dictionary.
    
    Args:
        section: ReportSection domain model
    
    Returns:
        Dictionary representation
    """
    return {
        "name": section.name,
        "content": section.content,
    }


def section_to_csv_data(section: ReportSection) -> list[dict[str, Any]]:
    """Convert a ReportSection to a list of dictionaries for CSV export.
    
    This is used when the section contains tabular data that should be
    exported as CSV. The infrastructure layer will handle the actual
    CSV serialization.
    
    Args:
        section: ReportSection with tabular data
    
    Returns:
        List of dictionaries (one per row)
    """
    # If content is already a list, return it
    if isinstance(section.content, list):
        return section.content
    
    # If content is a dict with an "items" key, extract it
    if isinstance(section.content, dict) and "items" in section.content:
        return section.content["items"]
    
    # Otherwise, wrap the content in a list
    return [section.content]


def report_to_serializable(report: Report) -> dict[str, Any]:
    """Convert a Report to a fully serializable structure.
    
    This is the main entry point for exporters. It returns a dictionary
    that can be directly serialized to JSON, TXT, or HTML by the
    infrastructure layer.
    
    Args:
        report: Report domain model
    
    Returns:
        Dictionary ready for serialization
    """
    return report_to_dict(report)


def reports_to_serializable(reports: list[Report]) -> list[dict[str, Any]]:
    """Convert multiple Reports to serializable structures.
    
    Args:
        reports: List of Report domain models
    
    Returns:
        List of dictionaries ready for serialization
    """
    return [report_to_serializable(report) for report in reports]

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit la logique de sérialisation des rapports en structures de données (dict, string). Ce module transforme un Report en format JSON-serializable ou en texte brut, sans écrire de fichier — l'écriture réelle est déléguée à infrastructure/exporters/.
# Pourquoi dans domain/ (charte) :
# - C'est une règle métier : comment structurer les données d'un rapport pour l'export
# - Aucune dépendance externe (juste json, csv, io de la stdlib)
# - Fonctions pures : pas d'I/O, pas d'écriture fichier
# - Testable en mémoire pure
# Ce qu'il ne contient PAS (règles projet) :
# ❌ Pas d'import depuis infrastructure/ (pas d'écriture fichier)
# ❌ Pas d'import depuis interfaces/ (pas de rendu)
# ❌ Pas d'import depuis application/ (pas de cas d'usage)
# ❌ Pas de open(), Path.write(), jinja2 — aucun I/O ni template
#Points clés :
# - report_to_dict() : transforme un Report en dictionnaire JSON-serializable
# - report_to_json() : sérialise en chaîne JSON (avec ou sans indentation)
# - report_to_text() : génère une représentation texte lisible par un humain
# - section_to_csv() : sérialise une section (contenant une liste de dicts) en CSV
# - report_to_csv_sections() : sérialise toutes les sections compatibles en CSV
# - extract_section_data() : extrait le contenu d'une section spécifique
# - flatten_report() : aplatisse le rapport en un dictionnaire à un seul niveau
# - _serialize_value() : helper récursif pour gérer datetime, dict, list
# - Aucune dépendance externe : utilise uniquement json, csv, io de la stdlib
# - Aucun I/O : ne lit ni n'écrit aucun fichier
# Comment il sera utilisé (aperçu) :
# - infrastructure/exporters/json_exporter.py appellera report_to_json() puis écrira le résultat
# - infrastructure/exporters/txt_exporter.py appellera report_to_text() puis écrira le résultat
# - infrastructure/exporters/html_exporter.py utilisera Jinja2 (pas ici, c'est infrastructure)
# - application/commands/export_report.py choisira le sérialiseur selon le format demandé
#---------------------------------------------------------------------->
