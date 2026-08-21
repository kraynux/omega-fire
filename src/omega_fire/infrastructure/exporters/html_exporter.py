# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""HTML exporter.

Exports data to HTML format using Jinja2 templates. Consumes serializable
structures from domain/reports/serializers.py and renders them to HTML files.

This module performs file I/O and is therefore in infrastructure/.
"""
from pathlib import Path
from typing import Any, Union
from omega_fire.domain.reports.serializers import report_to_serializable


class HtmlExporter:
    """Exporter that writes data to HTML files.
    
    Uses Jinja2 templates to render HTML output. Templates are loaded
    from domain/reports/templates/.
    """
    
    def __init__(self, templates_dir: Path):
        """Initialize the HTML exporter.
        
        Args:
            templates_dir: Directory containing Jinja2 templates
        """
        self.templates_dir = templates_dir
        self._env = None
    
    def _get_jinja_env(self):
        """Get or create the Jinja2 environment.
        
        Returns:
            Jinja2 Environment instance
        """
        if self._env is None:
            try:
                from jinja2 import Environment, FileSystemLoader
                self._env = Environment(
                    loader=FileSystemLoader(str(self.templates_dir)),
                    autoescape=True,
                )
            except ImportError:
                raise RuntimeError(
                    "Jinja2 is required for HTML export. "
                    "Install it with: pip install jinja2"
                )
        return self._env
    
    def export_data(
        self,
        data: Any,
        output_path: Union[str, Path],
        template_name: str = "report_full.html.j2",
    ) -> Path:
        """Export arbitrary data to an HTML file.
        
        Args:
            data: Data to export (must be dict-like)
            output_path: Path where the HTML file will be written
            template_name: Name of the Jinja2 template to use
        
        Returns:
            Path to the created file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        env = self._get_jinja_env()
        template = env.get_template(template_name)
        
        if isinstance(data, dict):
            html_content = template.render(**data)
        else:
            html_content = template.render(data=data)
        
        output_path.write_text(html_content, encoding="utf-8")
        return output_path
    
    def export_report(
        self,
        report,
        output_path: Union[str, Path],
        template_name: str = "report_full.html.j2",
    ) -> Path:
        """Export a Report domain object to an HTML file.
        
        Args:
            report: Report domain object
            output_path: Path where the HTML file will be written
            template_name: Name of the Jinja2 template to use
        
        Returns:
            Path to the created file
        """
        data = report_to_serializable(report)
        return self.export_data(data, output_path, template_name)
    
    def list_templates(self) -> list[str]:
        """List available HTML templates.
        
        Returns:
            List of template file names
        """
        if not self.templates_dir.exists():
            return []
        
        return [f.name for f in self.templates_dir.glob("*.j2")]


def export_to_html(
    data: Any,
    output_path: Union[str, Path],
    templates_dir: Path,
    template_name: str = "report_full.html.j2",
) -> Path:
    """Convenience function to export data to HTML.
    
    Args:
        data: Data to export
        output_path: Path where the HTML file will be written
        templates_dir: Directory containing Jinja2 templates
        template_name: Name of the Jinja2 template to use
    
    Returns:
        Path to the created file
    """
    exporter = HtmlExporter(templates_dir)
    return exporter.export_data(data, output_path, template_name)


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Exporte des données au format HTML via Jinja2
# - Utilise les templates de domain/reports/templates/
# - Consomme les structures sérialisables de domain/reports/serializers.py
# Pourquoi dans infrastructure/exporters/ (charte) :
# - C'est de l'infrastructure technique (rendu HTML via Jinja2)
# - Le domaine construit le contenu logique, l'infrastructure écrit le format
# - Les templates sont séparés du code Python (dans domain/reports/templates/)
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier (pas de construction de rapport)
# ❌ Pas de dépendance vers application/ ou interfaces/
# ❌ Pas de décision de quoi exporter (c'est le rôle de l'application)
# Points clés :
# - HtmlExporter : classe principale avec templates_dir configurable
# - Utilise Jinja2 (import conditionnel avec message d'erreur clair)
# - export_data() : exporte des données arbitraires avec template
# - export_report() : exporte un objet Report du domaine
# - list_templates() : liste les templates disponibles
# - Auto-escape activé pour la sécurité HTML
# - Crée les répertoires parents si nécessaire
# - Fonction de convenance : export_to_html()
# Dépendance externe :
# - Requiert jinja2 (pip install jinja2)
# - Lève RuntimeError si jinja2 n'est pas installé
# Comment il sera utilisé (aperçu) :
# - application/commands/export_report.py l'utilisera pour les exports HTML
# - interfaces/cli/actions.py proposera le format HTML à l'utilisateur
# - Les templates sont dans domain/reports/templates/ (séparés du code)
# - Les tests mockeront Jinja2 pour vérifier le rendu
#---------------------------------------------------------------------->
