# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Reports domain service.

Orchestrates business operations for report generation.
This service coordinates the domain modules (builders, serializers)
to construct logical report content. It does NOT write files —
that is the responsibility of infrastructure/exporters/.
"""
from datetime import datetime
from typing import Optional
from omega_fire.domain.ip_blacklist.models import BanEntry
from omega_fire.domain.rules.models import FirewallRule
from omega_fire.domain.fail2ban.models import Jail
from omega_fire.domain.logs.models import LogEntry, TopIP
from omega_fire.domain.reports.builders import (
    ReportBuilder,
    ReportSection,
    Report,
)


class ReportsService:
    """Domain service for report generation.
    
    This service orchestrates business logic for building reports.
    It constructs logical report content (sections, data) without
    performing any file I/O.
    """
    
    def build_blacklist_report(
        self,
        banned_ips: list[BanEntry],
        include_stats: bool = True,
        title: str = "Blacklist Report",
    ) -> Report:
        """Build a report of banned IPs.
        
        Args:
            banned_ips: List of banned IP entries
            include_stats: Whether to include summary statistics
            title: Report title
        
        Returns:
            Report object with blacklist content
        """
        builder = ReportBuilder(title=title)
        
        # Summary section
        if include_stats:
            builder.add_section_object(ReportSection(
                name="Summary",
                content={
                    "total_bans": len(banned_ips),
                    "active_bans": len([b for b in banned_ips if b.is_active()]),
                    "generated_at": datetime.now().isoformat(),
                }
            ))
        
        # Bans by backend
        by_backend: dict[str, list[BanEntry]] = {}
        for ban in banned_ips:
            by_backend.setdefault(ban.backend, []).append(ban)
        
        for backend, bans in by_backend.items():
            builder.add_section_object(ReportSection(
                name=f"Bans on {backend}",
                content={
                    "count": len(bans),
                    "ips": [b.ip for b in bans],
                }
            ))
        
        # Detailed list
        builder.add_section_object(ReportSection(
            name="Detailed List",
            content={
                "entries": [
                    {
                        "ip": b.ip,
                        "backend": b.backend,
                        "status": b.status.value,
                        "comment": b.comment,
                        "banned_at": b.banned_at.isoformat() if b.banned_at else None,
                    }
                    for b in banned_ips
                ]
            }
        ))
        
        return builder.build()
    
    def build_ruleset_report(
        self,
        rules: list[FirewallRule],
        title: str = "Firewall Ruleset Report",
    ) -> Report:
        """Build a report of firewall rules.
        
        Args:
            rules: List of firewall rules
            title: Report title
        
        Returns:
            Report object with ruleset content
        """
        builder = ReportBuilder(title=title)
        
        # Summary
        builder.add_section_object(ReportSection(
            name="Summary",
            content={
                "total_rules": len(rules),
                "generated_at": datetime.now().isoformat(),
            }
        ))
        
        # Rules by backend
        by_backend: dict[str, list[FirewallRule]] = {}
        for rule in rules:
            by_backend.setdefault(rule.backend, []).append(rule)
        
        for backend, backend_rules in by_backend.items():
            builder.add_section_object(ReportSection(
                name=f"Rules on {backend}",
                content={
                    "count": len(backend_rules),
                    "rules": [
                        {
                            "chain": r.chain.value,
                            "protocol": r.protocol.value if r.protocol else None,
                            "port": r.get_port_display(),
                            "action": r.action.value,
                            "comment": r.comment,
                        }
                        for r in backend_rules
                    ]
                }
            ))
        
        return builder.build()
    
    def build_fail2ban_report(
        self,
        jails: list[Jail],
        title: str = "Fail2ban Report",
    ) -> Report:
        """Build a report of fail2ban jails.
        
        Args:
            jails: List of fail2ban jails
            title: Report title
        
        Returns:
            Report object with fail2ban content
        """
        builder = ReportBuilder(title=title)
        
        # Summary
        active_jails = [j for j in jails if j.is_active()]
        builder.add_section_object(ReportSection(
            name="Summary",
            content={
                "total_jails": len(jails),
                "active_jails": len(active_jails),
                "total_banned": sum(j.total_banned for j in jails),
                "currently_banned": sum(j.currently_banned for j in jails),
                "generated_at": datetime.now().isoformat(),
            }
        ))
        
        # Jail details
        builder.add_section_object(ReportSection(
            name="Jail Details",
            content={
                "jails": [
                    {
                        "name": j.name,
                        "status": j.status.value,
                        "backend": j.config.backend,
                        "maxretry": j.config.maxretry,
                        "bantime": j.config.bantime,
                        "currently_banned": j.currently_banned,
                        "total_banned": j.total_banned,
                    }
                    for j in jails
                ]
            }
        ))
        
        return builder.build()
    
    def build_audit_report(
        self,
        banned_ips: list[BanEntry],
        rules: list[FirewallRule],
        jails: list[Jail],
        top_ips: list[TopIP],
        recent_actions: list[dict],
        title: str = "Complete Audit Report",
    ) -> Report:
        """Build a comprehensive audit report.
        
        Args:
            banned_ips: List of banned IPs
            rules: List of firewall rules
            jails: List of fail2ban jails
            top_ips: Top IPs from log analysis
            recent_actions: Recent system actions
            title: Report title
        
        Returns:
            Report object with complete audit content
        """
        builder = ReportBuilder(title=title)
        
        # Executive summary
        builder.add_section_object(ReportSection(
            name="Executive Summary",
            content={
                "total_bans": len(banned_ips),
                "total_rules": len(rules),
                "total_jails": len(jails),
                "generated_at": datetime.now().isoformat(),
            }
        ))
        
        # Backend status
        builder.add_section_object(ReportSection(
            name="Backend Status",
            content={
                "nftables": {
                    "bans": len([b for b in banned_ips if b.backend == "nftables"]),
                    "rules": len([r for r in rules if r.backend == "nftables"]),
                },
                "iptables": {
                    "bans": len([b for b in banned_ips if b.backend == "iptables"]),
                    "rules": len([r for r in rules if r.backend == "iptables"]),
                },
                "ip6tables": {
                    "bans": len([b for b in banned_ips if b.backend == "ip6tables"]),
                    "rules": len([r for r in rules if r.backend == "ip6tables"]),
                },
                "fail2ban": {
                    "jails": len(jails),
                    "banned": sum(j.currently_banned for j in jails),
                },
            }
        ))
        
        # Top IPs from logs
        builder.add_section_object(ReportSection(
            name="Top IPs (Logs)",
            content={
                "top_ips": [
                    {"ip": t.ip, "count": t.count}
                    for t in top_ips[:20]
                ]
            }
        ))
        
        # Top banned IPs
        ip_counts: dict[str, int] = {}
        for ban in banned_ips:
            ip_counts[ban.ip] = ip_counts.get(ban.ip, 0) + 1
        
        top_banned = sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)[:20]
        builder.add_section_object(ReportSection(
            name="Top Banned IPs",
            content={
                "top_banned": [
                    {"ip": ip, "count": count}
                    for ip, count in top_banned
                ]
            }
        ))
        
        # Recent actions
        builder.add_section_object(ReportSection(
            name="Recent Actions",
            content={
                "actions": recent_actions[:20]
            }
        ))
        
        return builder.build()
    
    def build_stats_report(
        self,
        period_label: str,
        kpi: dict,
        hourly_series: list[int],
        daily_trend: list[tuple[str, int]],
        top_ips: list[dict],
        top_jails: list[dict],
        management: dict,
        rules_evolution: list[tuple[str, int, int]],
        title: str = "Rapport Statistique",
    ) -> Report:
        """Build a periodic statistics report (menus 8.3/8.4).

        Combines ban/jail activity (from log aggregation), operator
        activity (from the audit trail), and rule/ban count evolution
        (from snapshot history) into a single structured report.

        Deliberately accepts only plain primitives (dict/list/tuple),
        never core.stats.models or ports.* dataclasses: domain/ depends
        on no other layer, so the caller (application/) is responsible
        for unpacking LogStatsSummary, AuditEntry, and Snapshot objects
        into these plain structures before calling this method.

        Args:
            period_label: Human-readable period label (e.g. "7 jours").
            kpi: Summary counters — expected keys: total_events,
                total_bans, top_jail_name, peak_hour, peak_count,
                data_source.
            hourly_series: 24 values, activity by hour-of-day, cumulated
                over the whole period (see LogAggregator.get_summary()).
            daily_trend: (label, count) pairs, day-by-day or week-by-
                week, chronologically sorted (see
                LogAggregator.get_daily_trend()).
            top_ips: List of dicts with keys ip, total_bans, last_ban.
            top_jails: List of dicts with keys name, total_bans,
                is_active, percentage.
            management: Operator activity counters — expected keys:
                rule_changes, backups, restores, total_actions,
                success_rate, recent_entries (list of (time_label,
                description, success) tuples).
            rules_evolution: (date_label, rules_count, ips_count)
                tuples, one per available snapshot in the period,
                chronologically sorted.
            title: Report title.

        Returns:
            Report object with all stats sections.
        """
        builder = ReportBuilder(title=title)

        builder.add_section_object(ReportSection(
            name="KPI",
            content={
                "period_label": period_label,
                "total_events": kpi.get("total_events", 0),
                "total_bans": kpi.get("total_bans", 0),
                "top_jail_name": kpi.get("top_jail_name", "Aucun"),
                "peak_hour": kpi.get("peak_hour", "--:--"),
                "peak_count": kpi.get("peak_count", 0),
                "data_source": kpi.get("data_source", "Inconnue"),
                "generated_at": datetime.now().isoformat(),
            }
        ))

        builder.add_section_object(ReportSection(
            name="Distribution Horaire",
            content={"hourly_series": hourly_series}
        ))

        builder.add_section_object(ReportSection(
            name="Tendance Journalière",
            content={"trend": daily_trend}
        ))

        builder.add_section_object(ReportSection(
            name="Top IPs",
            content={"ips": top_ips}
        ))

        builder.add_section_object(ReportSection(
            name="Top Jails",
            content={"jails": top_jails}
        ))

        builder.add_section_object(ReportSection(
            name="Gestion",
            content=management
        ))

        builder.add_section_object(ReportSection(
            name="Évolution des Règles",
            content={"points": rules_evolution}
        ))

        return builder.build()
    
    def get_report_metadata(self, report: Report) -> dict:
        """Extract metadata from a report.
        
        Args:
            report: Report object
        
        Returns:
            Dictionary with report metadata
        """
        return {
            "title": report.title,
            "section_count": len(report.sections),
            "generated_at": report.generated_at.isoformat(),
            "section_names": [s.name for s in report.sections],
        }

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Orchestration métier des rapports. Ce service coordonne la construction de rapports (blacklist, règles, fail2ban, audit complet, statistiques périodiques) en utilisant les builders du domaine. Il ne fait aucune écriture fichier — c'est le rôle de infrastructure/exporters/.
# Pourquoi dans domain/ (charte) :
# - C'est une règle métier : quoi inclure dans un rapport, comment structurer les sections
# - Aucune dépendance externe (opère sur les modèles du domaine)
# - Testable en mémoire pure
# - Utilisé par application/commands/export_report.py et
#   application/queries/build_stats_report.py
# Ce qu'il ne contient PAS (règles projet)
# ❌ Pas d'import depuis infrastructure/ (pas d'écriture fichier, pas de Jinja2)
# ❌ Pas d'import depuis interfaces/ (pas de rendu)
# ❌ Pas d'import depuis application/ (pas de cas d'usage)
# ❌ Pas de open(), Path.write(), json.dump() — aucun I/O
# Points clés :
# - Orchestration métier : construit des rapports logiques sans I/O
# - 5 types de rapports : blacklist, ruleset, fail2ban, audit complet,
#   statistiques périodiques (build_stats_report, menus 8.3/8.4)
#  - ReportBuilder : utilise le builder pattern pour construire les rapports
#  - Aucune dépendance externe : opère uniquement sur les modèles du domaine
#  - Aucun I/O : ne lit ni n'écrit aucun fichier
#  - Testable en mémoire : peut être testé avec des modèles construits manuellement
# - IMPORTANT : toute section construite comme un objet ReportSection
#   COMPLET (name= et content= passés ensemble) DOIT être ajoutée via
#   builder.add_section_object(section), jamais builder.add_section(...)
#   — cette dernière attend (name: str, content: dict) en DEUX
#   arguments séparés (domain/reports/builders.py::ReportBuilder.
#   add_section()), pas un objet ReportSection unique. Confondre les
#   deux ne lève aucune erreur (name accepte silencieusement l'objet
#   entier comme valeur) mais produit des sections vides/corrompues à
#   l'export — bug découvert et corrigé dans les 18 appels de ce
#   fichier lors du chantier des rapports 8.3/8.4.
# - build_stats_report() : seul builder à n'accepter QUE des primitives
#   (dict/list/tuple), jamais de dataclasses core.stats.models ou
#   ports.* — domain/ ne dépend d'aucune autre couche, donc c'est à
#   l'appelant (application/queries/build_stats_report.py) de dépaqueter
#   LogStatsSummary/AuditEntry/Snapshot avant l'appel.
# Comment il sera utilisé (aperçu) :
# - application/commands/export_report.py appellera ces méthodes pour construire le rapport
# - application/queries/build_stats_report.py appellera build_stats_report()
#   pour les menus 8.3/8.4 (rapports statistiques 7j/30j)
# - infrastructure/exporters/json_exporter.py sérialisera le Report en JSON
# - infrastructure/exporters/html_exporter.py utilisera Jinja2 pour rendre le rapport en HTML
# - interfaces/cli/actions.py proposera le choix du type de rapport à l'utilisateur
#---------------------------------------------------------------------->
