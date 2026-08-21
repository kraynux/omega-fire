# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Anomaly detection: cross-referencing stored state vs live state,
plus conflicting security tools (section 8).

Each check is independent and defensively wrapped — a failure in one
check (e.g. an adapter unavailable) never prevents the others from
running or crashes the whole report.
"""
from __future__ import annotations

from typing import Any, Optional

from omega_fire.core.enums import CapabilityStatus
from omega_fire.application.queries.audit_report.models import Anomaly

# Sous-ensemble de infrastructure/probe/known_services.py::KNOWN_SERVICES
# ["security_network"] — outils de pare-feu/sécurité concurrents dont la
# coexistence avec Omega-Fire (qui pilote nftables/iptables directement)
# mérite un signalement.
_FIREWALL_MANAGER_TOOLS = ("ufw", "firewalld", "csf", "shorewall")


def _check_rules_enabled_without_ref(rule_repository: Any) -> list[Anomaly]:
    """Check 1: rule marked enabled=True but with no external_ref
    (never actually applied to the live kernel)."""
    anomalies: list[Anomaly] = []
    try:
        rules = rule_repository.find_all()
    except Exception:
        return anomalies

    for rule in rules:
        if getattr(rule, "enabled", False) and not getattr(rule, "external_ref", None):
            anomalies.append(Anomaly(
                category="Règles",
                description=(
                    f"Règle #{getattr(rule, 'id', '?')} marquée active mais "
                    f"jamais appliquée au noyau (external_ref manquant)."
                ),
                severity="warning",
            ))
    return anomalies


def _check_rules_missing_from_live(rule_repository: Any, adapters: dict[str, Any]) -> list[Anomaly]:
    """Check 2: rule with external_ref set, but no longer present in the
    live backend state (removed outside the app, e.g. manually)."""
    anomalies: list[Anomaly] = []
    try:
        rules = rule_repository.find_all()
    except Exception:
        return anomalies

    live_refs_by_backend: dict[str, set[str]] = {}
    for backend, adapter in adapters.items():
        if adapter is None:
            continue
        try:
            live_rules = adapter.list_rules()
            live_refs_by_backend[backend] = {
                str(getattr(r, "external_ref", "")) for r in live_rules
                if getattr(r, "external_ref", None)
            }
        except Exception:
            continue

    for rule in rules:
        ref = getattr(rule, "external_ref", None)
        backend = getattr(rule, "backend", None)
        if not ref or backend not in live_refs_by_backend:
            continue
        if str(ref) not in live_refs_by_backend[backend]:
            anomalies.append(Anomaly(
                category="Règles",
                description=(
                    f"Règle #{getattr(rule, 'id', '?')} ({backend}) référencée "
                    f"en base mais absente du noyau — retirée manuellement ?"
                ),
                severity="critical",
            ))
    return anomalies


def _check_fail2ban_consistency(registry: Any) -> list[Anomaly]:
    """Check 3: fail2ban-client installed, but the service isn't running."""
    anomalies: list[Anomaly] = []
    if registry is None:
        return anomalies

    client = registry.get("fail2ban_client")
    service = registry.get("fail2ban_service")

    if (
        client and client.status == CapabilityStatus.AVAILABLE
        and service and service.status != CapabilityStatus.AVAILABLE
    ):
        anomalies.append(Anomaly(
            category="Fail2ban",
            description=(
                "fail2ban-client est installé, mais le service fail2ban "
                "n'est pas actif — les jails configurées ne sont pas appliquées."
            ),
            severity="critical",
        ))
    return anomalies


def _check_bans_missing_from_live(ban_repository: Any, adapters: dict[str, Any]) -> list[Anomaly]:
    """Check 4: ban marked active in the database, but not found in the
    live backend (removed outside the app)."""
    anomalies: list[Anomaly] = []
    try:
        active_bans = ban_repository.find_all(status="active")
    except Exception:
        return anomalies

    live_ips_by_backend: dict[str, set[str]] = {}
    for backend, adapter in adapters.items():
        if adapter is None:
            continue
        try:
            if hasattr(adapter, "list_bans"):
                live_bans = adapter.list_bans()
            elif hasattr(adapter, "list_banned_ips"):
                live_bans = adapter.list_banned_ips()
            else:
                continue
            ips = set()
            for item in live_bans:
                ip = item.get("ip") if isinstance(item, dict) else getattr(item, "ip", None)
                if ip:
                    ips.add(str(ip).split("/")[0].strip())
            live_ips_by_backend[backend] = ips
        except Exception:
            continue

    for ban in active_bans:
        backend = getattr(ban, "backend", None)
        ip = getattr(ban, "ip", None)
        if not ip or backend not in live_ips_by_backend:
            continue
        if ip not in live_ips_by_backend[backend]:
            anomalies.append(Anomaly(
                category="Bans",
                description=(
                    f"IP {ip} marquée bannie en base ({backend}) mais absente "
                    f"du live — levée manuellement ?"
                ),
                severity="warning",
            ))
    return anomalies


def _check_unused_backends(registry: Any, rule_repository: Any, ban_repository: Any) -> list[Anomaly]:
    """Check 5: a backend is AVAILABLE but has no rule and no ban
    referencing it — detected but never actually used."""
    anomalies: list[Anomaly] = []
    if registry is None:
        return anomalies

    try:
        rules = rule_repository.find_all() if rule_repository else []
    except Exception:
        rules = []
    try:
        bans = ban_repository.find_all() if ban_repository else []
    except Exception:
        bans = []

    used_backends = {getattr(r, "backend", None) for r in rules} | {getattr(b, "backend", None) for b in bans}

    for backend_id in ("nftables", "iptables", "ip6tables"):
        cap = registry.get(backend_id)
        if cap and cap.status == CapabilityStatus.AVAILABLE and backend_id not in used_backends:
            anomalies.append(Anomaly(
                category="Backends",
                description=(
                    f"Backend '{backend_id}' détecté disponible mais jamais "
                    f"utilisé (aucune règle, aucun ban)."
                ),
                severity="warning",
            ))
    return anomalies


def _check_conflicting_firewall_tools(registry: Any) -> list[Anomaly]:
    """Check 6: multiple firewall management tools active simultaneously
    (e.g. ufw + Omega-Fire's direct nftables management) — risk of
    conflicting or overwritten rules."""
    anomalies: list[Anomaly] = []
    if registry is None:
        return anomalies

    active_tools = []
    for tool_id in _FIREWALL_MANAGER_TOOLS:
        cap = registry.get(tool_id)
        if cap and cap.status == CapabilityStatus.AVAILABLE:
            active_tools.append(tool_id)

    if active_tools:
        tools_str = ", ".join(active_tools)
        anomalies.append(Anomaly(
            category="Sécurité réseau",
            description=(
                f"Outil(s) de gestion de pare-feu détecté(s) en parallèle "
                f"d'Omega-Fire : {tools_str}. Risque de conflit ou "
                f"d'écrasement de règles — envisager de n'en garder qu'un seul."
            ),
            severity="warning",
        ))
    return anomalies

def _aggregate_anomalies(anomalies: list[Anomaly]) -> list[Anomaly]:
    """Group anomalies with identical (category, description-pattern)
    into a single entry with a count, to avoid dozens of near-duplicate
    lines for systemic issues (e.g. many rules with the same problem)."""
    import re
    grouped: dict[tuple[str, str], Anomaly] = {}

    for a in anomalies:
        pattern = re.sub(r"#\S+", "#*", a.description)
        key = (a.category, pattern)
        if key in grouped:
            grouped[key].count += 1
        else:
            grouped[key] = Anomaly(
                category=a.category,
                description=a.description,
                severity=a.severity,
                count=1,
            )

    return list(grouped.values())

def collect_anomalies(
    rule_repository: Any,
    ban_repository: Any,
    registry: Any,
    adapters: dict[str, Any],
) -> list[Anomaly]:
    """Run all anomaly checks and return the combined list (section 8).

    Args:
        rule_repository: RuleRepository instance.
        ban_repository: BanRepository instance.
        registry: CapabilityRegistry instance.
        adapters: mapping of backend name -> resolved adapter, used to
            compare stored state against live state.

    Returns:
        Combined list of Anomaly, in check order. Empty list if nothing
        was detected (not an error — a clean system has none).
    """
    anomalies: list[Anomaly] = []
    anomalies += _check_rules_enabled_without_ref(rule_repository)
    anomalies += _check_rules_missing_from_live(rule_repository, adapters)
    anomalies += _check_fail2ban_consistency(registry)
    anomalies += _check_bans_missing_from_live(ban_repository, adapters)
    anomalies += _check_unused_backends(registry, rule_repository, ban_repository)
    anomalies += _check_conflicting_firewall_tools(registry)
    return _aggregate_anomalies(anomalies)


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Détecte les incohérences entre l'état stocké (base) et l'état live
#   (adapters), plus les outils de sécurité concurrents, pour la
#   section 8 du rapport d'audit (menu 6.3).
#
# Pourquoi dans application/queries/audit_report/ (charte) :
# - Lecture seule, compare des sources déjà résolues par l'appelant
#   (repositories, registry, adapters), jamais d'accès direct à
#   infrastructure/backends/ ou infrastructure/storage/ en dur.
#
# Ce qu'il ne contient PAS :
# ❌ Pas de correction automatique des anomalies détectées (signalement
#   seulement — corriger reste une décision humaine).
#
# Points clés :
# - 6 vérifications indépendantes, chacune défensive (try/except),
#   une panne sur l'une n'empêche jamais les autres de s'exécuter.
# - Check 6 (outils concurrents) réutilise le sous-ensemble
#   "security_network" de infrastructure/probe/known_services.py
#   (repris ici en constante locale plutôt qu'importé, car seul un
#   sous-ensemble — ufw/firewalld/csf/shorewall — est pertinent pour
#   ce signalement, pas la liste complète).
# - collect_anomalies() : point d'entrée unique, combine les 6 checks.
#
# Comment il sera utilisé :
# - report_builder.py (application/queries/audit_report/report_builder.py)
#   appelle collect_anomalies() pour peupler AuditReportData.anomalies.
#----------------------------------------------------------------------
