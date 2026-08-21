# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Export audit report command.

Orchestrates the generation of the full audit report (menu 6.3):
builds the report data via the query layer, renders it to TXT or HTML,
writes the file, and records this export in the audit journal — the
journal entry is what allows the NEXT audit to know its "since" date
(see application/queries/audit_report/report_builder.py).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from omega_fire.application.queries.audit_report.report_builder import build_audit_report
from omega_fire.application.queries.audit_report.models import AuditReportData

# Doit correspondre exactement à _AUDIT_EXPORT_ACTION_TITLE dans
# application/queries/audit_report/report_builder.py.
_AUDIT_EXPORT_ACTION_TITLE = "6.3 Export d'audit complet"


@dataclass
class ExportAuditReportRequest:
    """Input for the export audit report use case."""
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
class ExportAuditReportResult:
    """Output of the export audit report use case."""
    success: bool
    message: str
    file_path: Optional[Path] = None


class ExportAuditReportCommand:
    """Use case: build and export the full audit report (menu 6.3)."""

    def __init__(
        self,
        rule_repository: Any,
        ban_repository: Any,
        registry: Any,
        adapters: dict[str, Any],
        audit_logger: Any,
        db_connection: Any,
        html_exporter: Any = None,
    ):
        self._rule_repository = rule_repository
        self._ban_repository = ban_repository
        self._registry = registry
        self._adapters = adapters
        self._audit_logger = audit_logger
        self._db_connection = db_connection
        self._html_exporter = html_exporter

    def execute(self, request: ExportAuditReportRequest) -> ExportAuditReportResult:
        errors = request.validate()
        if errors:
            return ExportAuditReportResult(success=False, message="; ".join(errors))

        report = build_audit_report(
            rule_repository=self._rule_repository,
            ban_repository=self._ban_repository,
            registry=self._registry,
            adapters=self._adapters,
            audit_logger=self._audit_logger,
            db_connection=self._db_connection,
        )

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_path = Path(f"var/exports/audit-rapport_{timestamp}.{request.format}")
        dest_path = Path(request.destination) if request.destination else default_path
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            if request.format == "txt":
                content = self._format_as_txt(report)
                dest_path.write_text(content, encoding="utf-8")
            else:
                if self._html_exporter is None:
                    return ExportAuditReportResult(
                        success=False,
                        message="Exporteur HTML non disponible.",
                    )
                data = self._report_to_dict(report)
                data["theme_name"] = request.theme_name
                self._html_exporter.export_data(
                    data, dest_path, template_name="audit_report.html.j2"
                )
        except Exception as e:
            return ExportAuditReportResult(
                success=False,
                message=f"Échec de la génération du rapport : {e}",
            )

        # Trace l'export dans le journal — permet au PROCHAIN audit de
        # savoir depuis quelle date compter (voir report_builder.py).
        if self._audit_logger is not None:
            try:
                self._audit_logger.log_event(
                    event_type="action_execution",
                    actor="cli:admin",
                    action=_AUDIT_EXPORT_ACTION_TITLE,
                    result="success",
                    details={"format": request.format, "path": str(dest_path)},
                )
            except Exception:
                pass  # L'export a réussi ; l'échec de la trace ne doit pas faire échouer la commande.

        return ExportAuditReportResult(
            success=True,
            message=f"Rapport d'audit généré avec succès : {dest_path}",
            file_path=dest_path,
        )

    def _report_to_dict(self, report: AuditReportData) -> dict:
        """Flatten AuditReportData into a dict for Jinja2 (HtmlExporter
        calls template.render(**data) when data is a dict)."""
        return {
            "generated_at": report.generated_at.strftime("%Y-%m-%d %H:%M:%S"),
            "period_since": report.period_since,
            "executive_summary": report.executive_summary,
            "capabilities": report.capabilities,
            "rules_inventory": report.rules_inventory,
            "ip_internal_duplicate_count": report.ip_internal_duplicate_count,
            "ip_cross_backend_count": report.ip_cross_backend_count,
            "sync_info": report.sync_info,
            "ip_inventory": report.ip_inventory,
            "journal_summary": report.journal_summary,
            "anomalies": report.anomalies,
            "app_health": report.app_health,
            "disk_usage": report.disk_usage,
            "fail2ban_summary": report.fail2ban_summary,
            "db_integrity": report.db_integrity,
        }

    def _format_as_txt(self, report: AuditReportData) -> str:
        """Render AuditReportData as plain text."""
        lines = []
        lines.append("=" * 80)
        lines.append("                    OMEGA-FIRE — RAPPORT D'AUDIT COMPLET")
        lines.append("=" * 80)
        lines.append(f" Généré le      : {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}")
        if report.period_since:
            lines.append(f" Période depuis : {report.period_since}")
        else:
            lines.append(" Période        : premier audit (depuis l'origine du journal)")
        lines.append("-" * 80)
        lines.append("")
        lines.append("[ RÉSUMÉ EXÉCUTIF ]")
        lines.append(report.executive_summary)
        lines.append("")

        lines.append("[ SERVICES & CAPACITÉS ]")
        lines.append(
            f"  Disponibles: {report.capabilities.total_available}  "
            f"Manquantes: {report.capabilities.total_missing}  "
            f"Dégradées: {report.capabilities.total_degraded}  "
            f"Disqualifiées: {report.capabilities.total_disqualified}"
        )
        for cap in report.capabilities.capabilities:
            lines.append(f"  • {cap['id']:<25} [{cap['status']}]  ({cap['category']})")
        lines.append("")

        lines.append("[ ACTIVITÉ RÈGLES & BANS ]")
        lines.append(
            f"  Règles totales: {report.rules_inventory.total_count}  "
            f"Actives: {report.rules_inventory.enabled_count}"
        )
        
        if report.sync_info.found:
            lines.append(f"  Dernière synchronisation : {report.sync_info.last_sync_at}")
        else:
            lines.append("  Aucune synchronisation enregistrée.")
        lines.append("")

        lines.append("[ INVENTAIRE IP ACTUEL — photo à date, indépendant de la période ]")
        if report.ip_inventory:
            for inv in report.ip_inventory:
                lines.append(f"  • {inv.backend:<12} : {inv.active_count} IP(s) active(s)")
        else:
            lines.append("  Aucune IP active actuellement.")
        if report.ip_internal_duplicate_count > 0:
            lines.append(f"  ⚠ {report.ip_internal_duplicate_count} doublon(s) IP au sein d'un même backend.")
        if report.ip_cross_backend_count > 0:
            lines.append(f"  ℹ {report.ip_cross_backend_count} IP(s) présente(s) dans plusieurs backends (normal après sync).")
        lines.append("")

        lines.append("[ FAIL2BAN (résumé — détail complet : menu 6.4) ]")
        lines.append(
            f"  Jails: {report.fail2ban_summary.total_jails}  "
            f"IPs bannies: {report.fail2ban_summary.total_currently_banned}"
        )
        lines.append("")

        lines.append("[ JOURNAL APPLICATIF — TOP ÉVÉNEMENTS ]")
        for name, count in report.journal_summary.top_events:
            lines.append(f"  {count:>4}× {name}")
        lines.append(f"  Erreurs      : {report.journal_summary.error_count}")
        lines.append(f"  Autres       : {report.journal_summary.other_count}")
        lines.append("")

        lines.append("[ ANOMALIES DÉTECTÉES ]")
        if report.anomalies:
            for a in report.anomalies:
                marker = "‼" if a.severity == "critical" else "⚠"
                suffix = f" (×{a.count})" if a.count > 1 else ""
                lines.append(f"  {marker} [{a.category}] {a.description}{suffix}")
        else:
            lines.append("  ✔ Aucune anomalie détectée.")
        lines.append("")

        lines.append("[ SANTÉ APPLICATIVE & RESSOURCES ]")
        lines.append(f"  Version         : {report.app_health.version}")
        lines.append(f"  Dernier backup  : {report.app_health.last_backup_info}")
        lines.append(
            f"  Backups         : {report.disk_usage.backups_size_mb} MB "
            f"({report.disk_usage.backups_count} archives)"
        )
        lines.append(f"  Base de données : {report.disk_usage.db_size_mb} MB")
        lines.append(f"  Logs            : {report.disk_usage.logs_size_mb} MB")
        lines.append(f"  Espace libre    : {report.disk_usage.free_space_gb} GB")
        if report.disk_usage.warning:
            lines.append(f"  ⚠ {report.disk_usage.warning}")
        lines.append("")

        lines.append("[ INTÉGRITÉ BASE DE DONNÉES ]")
        status = "OK" if report.db_integrity.integrity_ok else "PROBLÈME"
        lines.append(f"  Statut          : {status} ({report.db_integrity.integrity_details})")
        lines.append(f"  Taille          : {report.db_integrity.db_size_mb} MB")
        lines.append(f"  Version schéma  : {report.db_integrity.schema_version}")
        lines.append("")

        lines.append("-" * 80)
        lines.append(f"-- Fin du rapport [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] --")

        return "\n".join(lines)


def create_export_audit_report_command(
    rule_repository: Any,
    ban_repository: Any,
    registry: Any,
    adapters: dict[str, Any],
    audit_logger: Any,
    db_connection: Any,
    html_exporter: Any = None,
) -> ExportAuditReportCommand:
    """Factory function to create an ExportAuditReportCommand."""
    return ExportAuditReportCommand(
        rule_repository=rule_repository,
        ban_repository=ban_repository,
        registry=registry,
        adapters=adapters,
        audit_logger=audit_logger,
        db_connection=db_connection,
        html_exporter=html_exporter,
    )


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Orchestre la génération complète du rapport d'audit (menu 6.3) :
#   appelle build_audit_report() (query), formate en TXT ou délègue au
#   HtmlExporter (Jinja2), écrit le fichier, trace l'export dans le
#   journal d'audit.
#
# Pourquoi dans application/commands/ (charte) :
# - Seul endroit autorisé à écrire (fichier + trace journal) — la
#   query report_builder.py reste volontairement en lecture seule.
# - Pattern simple (comme rotate_logs.py, sync_backends.py) : pas de
#   pipeline ExecutionPlan.
#
# Points clés :
# - _AUDIT_EXPORT_ACTION_TITLE doit rester identique à la constante de
#   même nom dans report_builder.py — sinon le prochain audit ne
#   retrouvera pas la trace de celui-ci (redeviendra "premier audit").
# - _report_to_dict() : aplati AuditReportData en dict pour Jinja2
#   (HtmlExporter.export_data appelle template.render(**data)).
# - Échec de la trace journal n'invalide pas un export par ailleurs
#   réussi (try/except silencieux sur cette seule étape).
#
# Flux d'exécution :
# interfaces/cli/actions.py : action_6_3_export_audit(ctx)
#   ↓ résout repositories/registry/adapters/audit_logger/db_connection
#     via ctx.container
# application/commands/export_audit_report.py : ExportAuditReportCommand.execute()
#   ↓ application/queries/audit_report/report_builder.py::build_audit_report()
#   ↓ HtmlExporter.export_data() ou écriture TXT directe
#   ↓ audit_logger.log_event() (trace pour le prochain audit)
#----------------------------------------------------------------------
