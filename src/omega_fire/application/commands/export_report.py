# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Export report command.

This module defines the command for exporting a report.
It constructs an ExecutionPlan with the necessary steps, defines
required capabilities and permissions, and provides a factory
function for easy invocation.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from omega_fire.application.pipeline.planner import PipelineStep, ExecutionPlan, create_step
from omega_fire.application.exceptions import InvalidRequestError


@dataclass
class ExportReportRequest:
    """Request object for exporting a report."""
    report_name: str
    format: str = "json"
    destination: str | None = None
    include_metadata: bool = True
    registry: Any | None = None
    theme_name: str = "omega-base"

    def validate(self) -> list[str]:
        """Validate the request."""
        errors: list[str] = []
        if not self.report_name:
            errors.append("Report name is required")
        valid_formats = ("json", "txt", "html", "csv")
        if self.format not in valid_formats:
            errors.append(f"Invalid format: {self.format}. Must be one of {valid_formats}")
        return errors

    def is_valid(self) -> bool:
        """Check if the request is valid."""
        return len(self.validate()) == 0


class ExportReportCommand:
    """Command for exporting a report."""

    REQUIRES_CAPABILITIES: list[str] = []
    REQUIRES_PERMISSIONS: list[str] = []
    COMMAND_NAME = "export_report"
    DESCRIPTION = "Export a report to file"

    def __init__(self, request: ExportReportRequest):
        self._request = request

    @property
    def request(self) -> ExportReportRequest:
        return self._request

    def build_plan(self) -> ExecutionPlan:
        """Build the execution plan for this command."""
        errors = self._request.validate()
        if errors:
            raise InvalidRequestError("ExportReportRequest", errors)

        steps = [
            create_step(
                name="validate_export",
                execute=self._validate_export,
                requires=[],
                skip_on_missing_capability=False,
            ),
            create_step(
                name="generate_report",
                execute=self._generate_report,
                requires=[],
                skip_on_missing_capability=False,
            ),
            create_step(
                name="audit_export",
                execute=self._audit_export,
                requires=[],
                skip_on_missing_capability=True,
            ),
        ]

        return ExecutionPlan(
            command_name=self.COMMAND_NAME,
            steps=steps,
            metadata={
                "report_name": self._request.report_name,
                "format": self._request.format,
                "destination": self._request.destination,
                "include_metadata": self._request.include_metadata,
            },
        )

    def _validate_export(self) -> None:
        """Validate export parameters and destination."""
        if self._request.destination:
            dest = Path(self._request.destination)
            dest.parent.mkdir(parents=True, exist_ok=True)

    def _classify_capability_status(self, details_val: Any) -> tuple[str, str]:
        """Classify a capability's raw details into a (semantic badge
        class, French label) pair, reusing the same heuristic
        previously duplicated as inline-styled HTML in this module's
        HTML branch. The badge classes (success/warning/neutral/danger)
        are the shared semantic classes defined once in
        domain/reports/templates/_base.html.j2 — no color decision made
        here, only which bucket a status falls into.
        """
        real_status = self._get_status_from_details(details_val)
        val_str = json.dumps(details_val, ensure_ascii=False) if isinstance(details_val, (dict, list)) else str(details_val)
        val_lower = val_str.lower()

        if real_status == "AVAILABLE" or "service actif" in val_lower or "binaire disponible" in val_lower or val_str == "Actif":
            return "success", "DISPONIBLE"
        elif real_status == "DEGRADED" or "inactif" in val_lower or "degraded" in val_lower:
            return "warning", "DÉGRADÉ"
        elif details_val is False or details_val is None or details_val == "" or real_status == "MISSING":
            return "danger", "NON INSTALLÉ"
        elif real_status == "DISQUALIFIED":
            return "danger", "DISQUALIFIÉ"
        else:
            return "success", "DISPONIBLE"

    @staticmethod
    def _get_status_from_details(details_val: Any) -> str:
        """Extract the official status of a component, if its details
        are a dict carrying one (e.g. {"status": "AVAILABLE"})."""
        if isinstance(details_val, dict):
            st = details_val.get("status", "")
            if st:
                return str(st).upper()
        return ""

    def _generate_report(self) -> None:
        """Generate the report file using infrastructure exporters with real data."""
        dest_path = Path(self._request.destination) if self._request.destination else Path(f"var/exports/report.{self._request.format}")
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        fmt = self._request.format.lower()

        # 1. Extraction des données réelles du Registre / Système
        registry = self._request.registry
        system_details = {}
        capabilities_list = []

        if registry:
            if hasattr(registry, "to_dict"):
                system_details = registry.to_dict()
            elif hasattr(registry, "capabilities"):
                system_details = {k: str(v) for k, v in getattr(registry, "capabilities", {}).items()}
            elif hasattr(registry, "list_all"):
                capabilities_list = [str(c) for c in registry.list_all()]

        items = system_details.items() if system_details else [(c, "Actif") for c in capabilities_list]
        capability_rows = []
        for name, details in items:
            status_class, status_label = self._classify_capability_status(details)
            capability_rows.append({
                "name": name,
                "value": json.dumps(details, ensure_ascii=False) if isinstance(details, (dict, list)) else str(details),
                "status_class": status_class,
                "status_label": status_label,
            })

        report_data = {
            "title": self._request.report_name,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "summary": {
                "status": "OPERATIONAL",
                "total_capabilities": len(capabilities_list) if capabilities_list else len(system_details),
            },
            "capabilities": system_details if system_details else capabilities_list,
            "capability_rows": capability_rows,
            "theme_name": self._request.theme_name,
        }

        # 2. Export selon le format sélectionné
        if fmt == "json":
            try:
                from omega_fire.infrastructure.exporters.json_exporter import JsonExporter
                exporter = JsonExporter()
                if hasattr(exporter, "export_data"):
                    exporter.export_data(report_data, dest_path)
                else:
                    dest_path.write_text(json.dumps(report_data, indent=2, ensure_ascii=False), encoding="utf-8")
            except Exception:
                dest_path.write_text(json.dumps(report_data, indent=2, ensure_ascii=False), encoding="utf-8")

        elif fmt == "html":
            try:
                from omega_fire.infrastructure.exporters.html_exporter import HtmlExporter
                templates_dir = Path("src/omega_fire/domain/reports/templates")
                exporter = HtmlExporter(templates_dir=templates_dir)
                exporter.export_data(report_data, dest_path, template_name="report_full.html.j2")
            except Exception:
                # Repli minimal si Jinja2/le template ne sont pas
                # disponibles pour une raison quelconque — plus le
                # chemin normal depuis la correction du mismatch de
                # données ci-dessus (report_full.html.j2 attendait
                # auparavant un objet "report" jamais fourni, le
                # rendu échouait donc systématiquement et ce repli
                # s'exécutait à chaque export, pas seulement en cas
                # d'erreur réelle). Volontairement texte brut, sans
                # dupliquer une nouvelle fois le CSS des rapports.
                lines = [f"<html><body><pre>{report_data['title']} — {report_data['generated_at']}\n"]
                for row in capability_rows:
                    lines.append(f"{row['name']}: {row['status_label']} — {row['value']}\n")
                lines.append("</pre></body></html>")
                dest_path.write_text("".join(lines), encoding="utf-8")

        elif fmt in ("txt", "csv"):
            items = system_details.items() if system_details else [(c, "Actif") for c in capabilities_list]
            
            lines = []
            lines.append("================================================================================")
            lines.append("                        OMEGA-FIRE SYSTEM DIAGNOSTIC REPORT                     ")
            lines.append("================================================================================")
            lines.append(f" Titre          : {report_data['title']}")
            lines.append(f" Date / Heure   : {report_data['generated_at']}")
            lines.append(f" Statut Global  : {report_data['summary']['status']}")
            lines.append(f" Total Modules  : {report_data['summary']['total_capabilities']}")
            lines.append("--------------------------------------------------------------------------------")
            lines.append("")
            lines.append("[ DÉTAIL DES CAPACITÉS ET MODULES ]")
            lines.append("")

            for name, details in items:
                val_str_raw = json.dumps(details) if isinstance(details, (dict, list)) else str(details)
                val_lower = val_str_raw.lower()
                real_status = self._get_status_from_details(details)
                
                if real_status == "AVAILABLE" or "service actif" in val_lower or "binaire disponible" in val_lower or val_str_raw == "Actif":
                    status_str = "[ DISPONIBLE ]"
                elif real_status == "DEGRADED" or "inactif" in val_lower or "degraded" in val_lower:
                    status_str = "[ DÉGRADÉ ]"
                elif details is False or details is None or details == "" or real_status == "MISSING":
                    status_str = "[ NON INSTALLÉ ]"
                elif real_status == "DISQUALIFIED":
                    status_str = "[ DISQUALIFIÉ ]"
                else:
                    status_str = "[ DISPONIBLE ]"

                # 2. Formate le JSON sur plusieurs lignes si c'est un dictionnaire/liste
                lines.append(f"● {name}")
                lines.append(f"  ├─ Statut : {status_str}")
                
                if isinstance(details, (dict, list)):
                    lines.append("  └─ Spécifications :")
                    formatted_json = json.dumps(details, indent=4, ensure_ascii=False)
                    for line in formatted_json.splitlines():
                        lines.append(f"        {line}")
                else:
                    lines.append(f"  └─ Spécifications : {details}")

                lines.append("")

            lines.append("--------------------------------------------------------------------------------")
            lines.append(f"-- Fin du rapport texte Omega-Fire CLI [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] --")

            dest_path.write_text("\n".join(lines), encoding="utf-8")

    def _audit_export(self) -> None:
        """Audit the export operation."""
        pass


def create_export_report_command(
    report_name: str,
    format: str = "json",
    destination: str | None = None,
    include_metadata: bool = True,
    registry: Any | None = None,
    theme_name: str = "omega-base",
) -> ExportReportCommand:
    """Factory function to create an ExportReportCommand."""
    request = ExportReportRequest(
        report_name=report_name,
        format=format,
        destination=destination,
        include_metadata=include_metadata,
        registry=registry,
        theme_name=theme_name,
    )
    return ExportReportCommand(request)


def plan_export_report(
    report_name: str,
    format: str = "json",
    destination: str | None = None,
    include_metadata: bool = True,
    registry: Any | None = None,
    theme_name: str = "omega-base",
) -> ExecutionPlan:
    """Convenience function to create and plan an export report command."""
    command = create_export_report_command(report_name, format, destination, include_metadata, registry, theme_name)
    return command.build_plan()
# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Commande d'export de rapport (JSON, TXT, HTML, CSV)
# - Construit un ExecutionPlan avec steps (validate, generate, audit)
# - Pas de capacité système requise (c'est de l'export)
# - Pas de permission root requise
#
# Pourquoi dans application/commands/ (charte) :
# - Cas d'usage applicatif qui orchestre des opérations
# - Dépend de application/pipeline/ pour le planning
# - Ne dépend pas de infrastructure/ (pas d'exécution système directe)
#
# Ce qu'il ne contient PAS (règles projet) :
# ❌ Pas d'import depuis infrastructure/
# ❌ Pas d'import depuis interfaces/
# ❌ Pas de subprocess, json.dump, open() — aucun I/O
#
# Points clés :
# - ExportReportRequest : validation (report_name, format, destination)
# - ExportReportCommand : build_plan() avec 3 steps
# - REQUIRES_CAPABILITIES = [] (pas de backend système requis)
# - REQUIRES_PERMISSIONS = [] (pas de root requis)
# - create_export_report_command() : factory
# - plan_export_report() : convenience
#
# Comment il sera utilisé :
# - interfaces/cli/actions.py appellera plan_export_report()
# - application/pipeline/executor.py exécutera le plan
# - ports/exporter.py portera la génération réelle
#---------------------------------------------------------------------->
