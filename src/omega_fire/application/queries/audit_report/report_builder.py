# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Audit report assembly: orchestrates all section collectors into a
single AuditReportData (menu 6.3).

Pure query orchestration: reads from repositories, registry, adapters,
and the audit logger, and assembles the final DTO. Never writes
anything — marking this export in the audit trail is the
responsibility of the caller (application/commands/export_audit_report.py),
which has write privileges this module intentionally does not.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from omega_fire.application.queries.audit_report.models import AuditReportData
from omega_fire.application.queries.audit_report.capabilities_section import (
    collect_capabilities_section,
    collect_fail2ban_summary,
)
from omega_fire.application.queries.audit_report.activity_section import (
    collect_sync_info,
    collect_journal_summary,
)
from omega_fire.application.queries.audit_report.inventory_section import (
    collect_rules_inventory,
    collect_ip_inventory,
)
from omega_fire.application.queries.audit_report.health_section import (
    collect_app_health,
    collect_disk_usage,
    check_database_integrity,
)
from omega_fire.application.queries.audit_report.anomalies_section import (
    collect_anomalies,
)
from omega_fire.shared.i18n import _

_AUDIT_EXPORT_ACTION_TITLE = "6.3 Export d'audit complet"


def _find_last_audit_date(audit_logger: Any) -> Optional[datetime]:
    """Find the timestamp of the most recent successful audit export."""
    if audit_logger is None:
        return None

    entries = audit_logger.get_all_since(None)
    export_entries = [
        e for e in entries
        if e.success and e.action.strip() == _AUDIT_EXPORT_ACTION_TITLE
    ]

    if not export_entries:
        return None

    return max(export_entries, key=lambda e: e.timestamp).timestamp


def _build_executive_summary(report: AuditReportData) -> str:
    """Build a short executive summary from the assembled report data."""
    lines = []

    lines.append(
        _("Capacités : {total_available} disponible(s), {total_missing} manquante(s), {total_degraded} dégradée(s).").format(total_available=report.capabilities.total_available, total_missing=report.capabilities.total_missing, total_degraded=report.capabilities.total_degraded)
    )
    lines.append(
        _("Règles actuelles : {total_count} au total, {enabled_count} active(s).").format(total_count=report.rules_inventory.total_count, enabled_count=report.rules_inventory.enabled_count)
    )
    
    if report.sync_info.found:
        lines.append(_("Dernière synchronisation : {last_sync_at}.").format(last_sync_at=report.sync_info.last_sync_at))
    else:
        lines.append(_("Aucune synchronisation enregistrée."))

    total_ips = sum(inv.active_count for inv in report.ip_inventory)
    lines.append(_("IPs bannies actuellement (photo à date) : {total_ips} au total.").format(total_ips=total_ips))
    if report.ip_internal_duplicate_count > 0:
        lines.append(_("⚠ {ip_internal_duplicate_count} doublon(s) IP détecté(s) au sein d'un même backend.").format(ip_internal_duplicate_count=report.ip_internal_duplicate_count))
    if report.ip_cross_backend_count > 0:
        lines.append(_("ℹ {ip_cross_backend_count} IP(s) présente(s) dans plusieurs backends simultanément (normal après une synchronisation).").format(ip_cross_backend_count=report.ip_cross_backend_count))

    lines.append(
        _("Fail2ban : {total_jails} jail(s), {total_currently_banned} IP(s) bannie(s) actuellement.").format(total_jails=report.fail2ban_summary.total_jails, total_currently_banned=report.fail2ban_summary.total_currently_banned)
    )

    if report.anomalies:
        critical = sum(1 for a in report.anomalies if a.severity == "critical")
        warning = len(report.anomalies) - critical
        lines.append(
            _("⚠ {count} anomalie(s) détectée(s) ({critical} critique(s), {warning} avertissement(s)).").format(count=len(report.anomalies), critical=critical, warning=warning)
        )
    else:
        lines.append(_("✔ Aucune anomalie détectée."))

    if report.db_integrity.integrity_ok:
        lines.append(_("✔ Intégrité base de données : OK."))
    else:
        lines.append(_("⚠ Intégrité base de données : {integrity_details}.").format(integrity_details=report.db_integrity.integrity_details))

    if report.disk_usage.warning:
        lines.append(f"⚠ {report.disk_usage.warning}.")

    return "\n".join(lines)


def build_audit_report(
    rule_repository: Any,
    ban_repository: Any,
    registry: Any,
    adapters: dict[str, Any],
    audit_logger: Any,
    db_connection: Any,
) -> AuditReportData:
    """Assemble the complete audit report (menu 6.3)."""
    since_date = _find_last_audit_date(audit_logger)
    fail2ban_adapter = adapters.get("fail2ban")

    ip_inventory, ip_internal_duplicate_count, ip_cross_backend_count = collect_ip_inventory(adapters)
    report = AuditReportData(
        generated_at=datetime.now(),
        period_since=since_date.strftime("%Y-%m-%d %H:%M:%S") if since_date else None,
        capabilities=collect_capabilities_section(registry),
        rules_inventory=collect_rules_inventory(rule_repository),
        sync_info=collect_sync_info(audit_logger),
        ip_inventory=ip_inventory,
        ip_internal_duplicate_count=ip_internal_duplicate_count,
        ip_cross_backend_count=ip_cross_backend_count,
        journal_summary=collect_journal_summary(audit_logger, since_date),
        anomalies=collect_anomalies(rule_repository, ban_repository, registry, adapters),
        app_health=collect_app_health(),
        disk_usage=collect_disk_usage(),
        fail2ban_summary=collect_fail2ban_summary(fail2ban_adapter),
        db_integrity=check_database_integrity(db_connection),
    )

    report.executive_summary = _build_executive_summary(report)
    return report
