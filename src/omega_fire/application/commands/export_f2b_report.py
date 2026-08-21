# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Export fail2ban detail report command (menu 6.4).

Orchestrates the generation of the detailed fail2ban report: builds
the report data via the query layer, renders it to TXT or HTML, and
writes the file.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from omega_fire.application.queries.f2b_report.report_builder import build_f2b_report
from omega_fire.application.queries.f2b_report.models import F2bReportData


@dataclass
class ExportF2bReportRequest:
    """Input for the export fail2ban report use case."""
    format: str = "html"  # "txt" | "html"
    destination: Optional[str] = None
    theme_name: str = "omega-base"

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.format not in ("txt", "html"):
            errors.append(f"Invalid format: {self.format}. Must be 'txt' or 'html'")
        return errors

    def is_valid(self) -> bool:
        return len(self.validate()) == 0


@dataclass
class ExportF2bReportResult:
    """Output of the export fail2ban report use case."""
    success: bool
    message: str
    file_path: Optional[Path] = None


class ExportF2bReportCommand:
    """Use case: build and export the detailed fail2ban report (menu 6.4)."""

    def __init__(
        self,
        fail2ban_adapter: Any,
        service_controller: Any,
        history_reader: Any,
        html_exporter: Any = None,
    ):
        self._fail2ban_adapter = fail2ban_adapter
        self._service_controller = service_controller
        self._history_reader = history_reader
        self._html_exporter = html_exporter

    def execute(self, request: ExportF2bReportRequest) -> ExportF2bReportResult:
        errors = request.validate()
        if errors:
            return ExportF2bReportResult(success=False, message="; ".join(errors))

        report = build_f2b_report(
            fail2ban_adapter=self._fail2ban_adapter,
            service_controller=self._service_controller,
            history_reader=self._history_reader,
        )

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_path = Path(f"var/exports/f2b-rapport_{timestamp}.{request.format}")
        dest_path = Path(request.destination) if request.destination else default_path
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            if request.format == "txt":
                content = self._format_as_txt(report)
                dest_path.write_text(content, encoding="utf-8")
            else:
                if self._html_exporter is None:
                    return ExportF2bReportResult(
                        success=False,
                        message="Exporteur HTML non disponible.",
                    )
                data = self._report_to_dict(report)
                data["theme_name"] = request.theme_name
                self._html_exporter.export_data(
                    data, dest_path, template_name="f2b_report.html.j2"
                )
        except Exception as e:
            return ExportF2bReportResult(
                success=False,
                message=f"Échec de la génération du rapport : {e}",
            )

        return ExportF2bReportResult(
            success=True,
            message=f"Rapport fail2ban généré avec succès : {dest_path}",
            file_path=dest_path,
        )

    def _report_to_dict(self, report: F2bReportData) -> dict:
        """Flatten F2bReportData into a dict for Jinja2."""
        return {
            "generated_at": report.generated_at.strftime("%Y-%m-%d %H:%M:%S"),
            "system": report.system,
            "total_jails": report.total_jails,
            "jails": report.jails,
            "duplicate_ips": report.duplicate_ips,
        }

    def _format_as_txt(self, report: F2bReportData) -> str:
        """Render F2bReportData as plain text."""
        lines = []
        lines.append("=" * 80)
        lines.append("                 OMEGA-FIRE — RAPPORT DÉTAILLÉ FAIL2BAN")
        lines.append("=" * 80)
        lines.append(f" Généré le : {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("-" * 80)
        lines.append("")

        lines.append("[ SYSTÈME ]")
        lines.append(f"  Installé          : {'Oui' if report.system.installed else 'Non'}")
        lines.append(f"  Service actif     : {'Oui' if report.system.service_running else 'Non'}")
        if report.system.enabled_at_boot is None:
            lines.append("  Activé au démarrage : Indéterminé (gestionnaire de service non détecté)")
        else:
            lines.append(f"  Activé au démarrage : {'Oui' if report.system.enabled_at_boot else 'Non'}")
        lines.append("")

        lines.append(f"[ JAILS ({report.total_jails}) ]")
        lines.append("")
        for jail in report.jails:
            lines.append(f"● {jail.name}")
            lines.append(f"  ├─ Échecs (actuel/total) : {jail.currently_failed} / {jail.total_failed}")
            lines.append(f"  ├─ Bannis (actuel/total) : {jail.currently_banned} / {jail.total_banned}")
            lines.append(
                f"  ├─ Config : maxretry={jail.maxretry or 'N/A'}  "
                f"bantime={jail.bantime or 'N/A'}  findtime={jail.findtime or 'N/A'}"
            )
            if jail.banned_ips:
                ips_str = ", ".join(jail.banned_ips)
                lines.append(f"  ├─ IPs bannies : {ips_str}")
                if jail.banned_ips_overflow > 0:
                    lines.append(f"  │  (+{jail.banned_ips_overflow} autre(s))")
            else:
                lines.append("  ├─ IPs bannies : aucune")

            if jail.history_available:
                if jail.recent_bans:
                    lines.append("  └─ 10 derniers bans (historique fail2ban) :")
                    for rb in jail.recent_bans:
                        lines.append(f"       {rb.timeofban.strftime('%Y-%m-%d %H:%M:%S')} — {rb.ip}")
                else:
                    lines.append("  └─ Aucun ban dans l'historique fail2ban.")
            else:
                lines.append("  └─ Historique fail2ban indisponible (base non trouvée).")
            lines.append("")

        lines.append("[ IPS PRÉSENTES DANS PLUSIEURS JAILS ]")
        if report.duplicate_ips:
            for dup in report.duplicate_ips:
                jails_str = ", ".join(dup.jails)
                lines.append(f"  {dup.ip:<18} → {jails_str}")
        else:
            lines.append("  Aucune IP partagée entre plusieurs jails actuellement.")
        lines.append("")

        lines.append("-" * 80)
        lines.append(f"-- Fin du rapport [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] --")

        return "\n".join(lines)


def create_export_f2b_report_command(
    fail2ban_adapter: Any,
    service_controller: Any,
    history_reader: Any,
    html_exporter: Any = None,
) -> ExportF2bReportCommand:
    """Factory function to create an ExportF2bReportCommand."""
    return ExportF2bReportCommand(
        fail2ban_adapter=fail2ban_adapter,
        service_controller=service_controller,
        history_reader=history_reader,
        html_exporter=html_exporter,
    )


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Orchestre la génération du rapport détaillé fail2ban (menu 6.4) :
#   build_f2b_report() (query), formate en TXT ou délègue au
#   HtmlExporter (Jinja2), écrit le fichier.
#
# Pourquoi dans application/commands/ (charte) :
# - Seul endroit autorisé à écrire — la query report_builder.py reste
#   volontairement en lecture seule.
# - Pattern simple (comme export_audit_report.py) : pas de pipeline
#   ExecutionPlan.
#
# Comment il sera utilisé :
# - interfaces/cli/actions.py::action_6_4_export_f2b_stats résout les
#   dépendances via ctx.container, construit la command, l'exécute.
#----------------------------------------------------------------------
