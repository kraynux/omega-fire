# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Reports domain builders.

Pure domain logic for report structure and construction.
This module defines the data models for reports and provides
a builder pattern for constructing them. It does NOT serialize
or write files — that is the responsibility of infrastructure/.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class ReportSection:
    """A section within a report.
    
    Contains a name and structured content (dictionary).
    The content can be any serializable data structure.
    """
    name: str
    content: dict[str, Any] = field(default_factory=dict)
    
    def is_empty(self) -> bool:
        """Check if the section has no content."""
        return len(self.content) == 0
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the section content."""
        return self.content.get(key, default)


@dataclass
class Report:
    """A complete report with metadata and sections.
    
    This is a pure data structure representing a logical report.
    It does not know how to serialize itself to JSON, CSV, or HTML —
    that is the responsibility of infrastructure/exporters/.
    """
    title: str
    sections: list[ReportSection] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def add_section(self, section: ReportSection) -> None:
        """Add a section to the report."""
        self.sections.append(section)
    
    def get_section(self, name: str) -> Optional[ReportSection]:
        """Get a section by name. Returns None if not found."""
        for section in self.sections:
            if section.name == name:
                return section
        return None
    
    def has_section(self, name: str) -> bool:
        """Check if a section exists."""
        return self.get_section(name) is not None
    
    def section_count(self) -> int:
        """Return the number of sections."""
        return len(self.sections)
    
    def is_empty(self) -> bool:
        """Check if the report has no sections."""
        return len(self.sections) == 0
    
    def get_all_data(self) -> dict[str, Any]:
        """Get all report data as a single dictionary.
        
        Returns:
            Dictionary with title, metadata, and all sections
        """
        return {
            "title": self.title,
            "generated_at": self.generated_at.isoformat(),
            "metadata": self.metadata,
            "sections": {
                section.name: section.content
                for section in self.sections
            }
        }


class ReportBuilder:
    """Builder for constructing reports step by step.
    
    Provides a fluent interface for building reports with
    multiple sections.
    """
    
    def __init__(self, title: str):
        """Initialize the builder with a report title.
        
        Args:
            title: Report title
        """
        self.title = title
        self.sections: list[ReportSection] = []
        self.metadata: dict[str, Any] = {}
        self.generated_at: datetime = datetime.now()
    
    def set_metadata(self, key: str, value: Any) -> "ReportBuilder":
        """Set a metadata field.
        
        Args:
            key: Metadata key
            value: Metadata value
        
        Returns:
            Self for method chaining
        """
        self.metadata[key] = value
        return self
    
    def add_section(
        self,
        name: str,
        content: Optional[dict[str, Any]] = None,
    ) -> "ReportBuilder":
        """Add a section to the report.
        
        Args:
            name: Section name
            content: Section content (dictionary)
        
        Returns:
            Self for method chaining
        """
        section = ReportSection(
            name=name,
            content=content or {}
        )
        self.sections.append(section)
        return self
    
    def add_section_object(self, section: ReportSection) -> "ReportBuilder":
        """Add a pre-built section object.
        
        Args:
            section: ReportSection object
        
        Returns:
            Self for method chaining
        """
        self.sections.append(section)
        return self
    
    def set_generated_at(self, timestamp: datetime) -> "ReportBuilder":
        """Set the generation timestamp.
        
        Args:
            timestamp: Generation timestamp
        
        Returns:
            Self for method chaining
        """
        self.generated_at = timestamp
        return self
    
    def build(self) -> Report:
        """Build and return the report.
        
        Returns:
            Complete Report object
        """
        return Report(
            title=self.title,
            sections=list(self.sections),
            generated_at=self.generated_at,
            metadata=dict(self.metadata),
        )
    
    def reset(self) -> "ReportBuilder":
        """Reset the builder to its initial state.
        
        Returns:
            Self for method chaining
        """
        self.sections.clear()
        self.metadata.clear()
        self.generated_at = datetime.now()
        return self

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit les modèles de données pour les rapports et le builder pattern pour les construire. Ce module contient les classes Report, ReportSection, et ReportBuilder qui permettent de construire des rapports structurés en mémoire.
# Pourquoi dans domain/ (charte) :
# - C'est une règle métier : structure d'un rapport, sections, métadonnées
# - Aucune dépendance externe (juste dataclasses, datetime, typing)
# - Testable en mémoire pure
# - Utilisé par domain/reports/service.py pour construire les rapports
# Ce qu'il ne contient PAS (règles projet) :
# ❌ Pas d'import depuis infrastructure/ (pas de sérialisation)
# ❌ Pas d'import depuis interfaces/ (pas de rendu)
# ❌ Pas d'import depuis application/ (pas de cas d'usage)
# ❌ Pas de open(), Path.write(), json.dump() — aucun I/O
# Points clés :
# - ReportSection : section d'un rapport avec nom et contenu structuré
# - Report : rapport complet avec titre, sections, métadonnées, timestamp
# - ReportBuilder : builder pattern pour construire les rapports étape par étape
# - Méthodes fluent : set_metadata(), add_section(), set_generated_at() retournent self pour le chaining
# - get_all_data() : retourne tout le rapport sous forme de dictionnaire sérialisable
# - Aucune dépendance externe : utilise uniquement dataclasses, datetime, typing
# - Aucun I/O : ne lit ni n'écrit aucun fichier
# Comment il sera utilisé (aperçu) :
# - domain/reports/service.py utilisera ReportBuilder pour construire les rapports
# - infrastructure/exporters/json_exporter.py appellera report.get_all_data() pour sérialiser en JSON
# - infrastructure/exporters/html_exporter.py itérera sur report.sections pour rendre chaque section
# - interfaces/cli/actions.py affichera le rapport via les renderers
#---------------------------------------------------------------------->
