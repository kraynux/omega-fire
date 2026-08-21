# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Capability status rendering for Omega-Fire CLI.

Builds the Rich renderables for the capability registry screens
(menu 1.1 vue d'ensemble, 1.2 détail, 1.4 diagnostics, 1.6 recherche).

Moved here from application/queries/capability_status.py (2026-08-16) :
c'était un module de rendu Rich complet (badges, tableaux, panels)
mal placé dans application/, qui importait en plus theme_registry
depuis interfaces/cli/themes/registry.py — dépendance inversée
contraire à la charte (application/ ne doit jamais dépendre de
interfaces/). Les couleurs fixes en dur ("bold green", etc.) ont été
remplacées par les clés de thème status.* déjà prévues pour cet usage
précis (cf. themes/omega_base.py).

Conforme à la charte Omega-Fire :
- Rendu pur, aucune logique métier.
- Toutes les couleurs passent par theme_registry.get_style(...).
- Ne modifie jamais le registre (lecture seule via CapabilityRegistry).
"""
from __future__ import annotations

from typing import Any

from rich.console import Group
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from rich import box

from omega_fire.core.capability_registry import CapabilityRegistry
from omega_fire.core.enums import CapabilityStatus
from omega_fire.interfaces.cli.themes.registry import theme_registry


_STATUS_STYLE_KEYS = {
    CapabilityStatus.AVAILABLE: "status.available",
    CapabilityStatus.DEGRADED: "status.degraded",
    CapabilityStatus.MISSING: "status.missing",
    CapabilityStatus.DISQUALIFIED: "status.disqualified",
}

_STATUS_LABELS = {
    CapabilityStatus.AVAILABLE: "✔ AVAILABLE",
    CapabilityStatus.DEGRADED: "⚠️ DEGRADED",
    CapabilityStatus.MISSING: "❌ MISSING",
    CapabilityStatus.DISQUALIFIED: "⊘ DISQUALIFIED",
}


def _get_status_badge(status: CapabilityStatus) -> Text:
    """Badge de statut — couleur pilotée par le thème actif (status.*)."""
    style = theme_registry.get_style(_STATUS_STYLE_KEYS.get(status, "text.muted"))
    label = _STATUS_LABELS.get(status, "❓ UNKNOWN")
    return Text(label, style=style)


def get_all_capabilities(registry: CapabilityRegistry) -> Any:
    """1.1: Return a formatted Rich renderable of all capabilities."""
    capabilities = registry.list_all()

    if not capabilities:
        return Panel(
            Text("⚠️ Aucune capacité enregistrée dans le système.\nLancez un re-scan via le menu (1.3).", justify="center"),
            title="[ Registre des Capacités ]",
            border_style=theme_registry.get_style("action.warning"),
        )

    # 1. Tableau principal (Bordures fines et en-tête alignés sur la couleur de bordure)
    table = Table(
        title="REGISTRE DES CAPACITÉS SYSTÈME",
        title_style=theme_registry.get_style("text.heading"),
        expand=True,
        show_header=True,
        border_style=theme_registry.get_style("border.accent"),
        box=box.SQUARE,                              # ← 1. Bordures fines uniformes (supprime le gras)
        header_style=theme_registry.get_style("border.accent"),  # ← 2. Police des titres de colonnes à la couleur de bordure
    )
    table.add_column("Statut", style="bold", width=16)
    table.add_column("Capacité (ID)", style=theme_registry.get_style("text.main"), width=24)
    table.add_column("Raison / Diagnostics", style=theme_registry.get_style("text.muted"))

    for cap in sorted(capabilities, key=lambda c: c.id):
        badge = _get_status_badge(cap.status)
        reason_text = cap.reason if cap.reason else "—"
        table.add_row(badge, cap.id.upper(), reason_text)

    # 2. Cartouche de résumé (Statuts en couleurs pilotées par le thème)
    summary = registry.get_summary()
    summary_text = Text()
    summary_text.append(f"Total: {summary.get('total', 0)}  │  ", style=theme_registry.get_style("text.main"))
    summary_text.append(f"✔ Disponible: {summary.get('available', 0)}  │  ", style=theme_registry.get_style("status.available"))
    summary_text.append(f"⚠️ Dégradé: {summary.get('degraded', 0)}  │  ", style=theme_registry.get_style("status.degraded"))
    summary_text.append(f"❌ Manquant: {summary.get('missing', 0)}  │  ", style=theme_registry.get_style("status.missing"))
    summary_text.append(f"⊘ Disqualifié: {summary.get('disqualified', 0)}", style=theme_registry.get_style("status.disqualified"))

    summary_panel = Panel(
        summary_text,
        title="[ Bilan Synthétique ]",
        title_align="left",
        border_style=theme_registry.get_style("border.accent"),
        padding=(0, 1),
    )

    return Group(table, Text(""), summary_panel)


def get_capability_detail(registry: CapabilityRegistry, capability_id: str) -> Any:
    """1.2: Return detailed information about a specific capability."""
    cap = registry.get(capability_id)

    if not cap:
        return Panel(
            Text(f"❌ Capacité '{capability_id}' introuvable dans le registre.", style=theme_registry.get_style("action.error")),
            title="[ Erreur ]",
            border_style=theme_registry.get_style("action.error"),
        )

    # Contenu détaillé
    info_table = Table(show_header=False, box=None, padding=(0, 1), expand=True)
    info_table.add_column("Propriété", style=theme_registry.get_style("text.info"), width=22)
    info_table.add_column("Valeur", style=theme_registry.get_style("text.main"))

    info_table.add_row("Identifiant :", cap.id.upper())
    info_table.add_row("Statut Actuel :", _get_status_badge(cap.status))

    if cap.reason:
        info_table.add_row("Raison / Cause :", Text(cap.reason, style=theme_registry.get_style("status.degraded")))

    if hasattr(cap, "detail") and cap.detail:
        info_table.add_row("Détails Techniques :", Text(str(cap.detail), style=theme_registry.get_style("text.muted")))

    if hasattr(cap, "last_checked") and cap.last_checked:
        dt_str = cap.last_checked.strftime("%Y-%m-%d %H:%M:%S") if hasattr(cap.last_checked, "strftime") else str(cap.last_checked)
        info_table.add_row("Dernier Scan :", Text(dt_str, style=theme_registry.get_style("text.muted")))

    # Directives basées sur le statut, couleur pilotée par le thème
    action_text = Text()
    if cap.status == CapabilityStatus.AVAILABLE:
        action_text.append("✔ Cette capacité est pleinement opérationnelle et disponible.", style=theme_registry.get_style("status.available"))
    elif cap.status == CapabilityStatus.DEGRADED:
        action_text.append("⚠️ Capacité partiellement fonctionnelle. Vérifiez la configuration des dépendances.", style=theme_registry.get_style("status.degraded"))
    elif cap.status == CapabilityStatus.MISSING:
        action_text.append("❌ Composant système manquant. Veuillez installer le package/outil requis.", style=theme_registry.get_style("status.missing"))
    elif cap.status == CapabilityStatus.DISQUALIFIED:
        action_text.append("⊘ Capacité disqualifiée par la politique système. Vérifiez les prérequis.", style=theme_registry.get_style("status.disqualified"))

    main_panel = Panel(
        Group(
            info_table,
            Text(""),
            Rule("Évaluation & Directives", style=theme_registry.get_style("border.accent")),
            Text(""),
            action_text,
        ),
        title=f"[ Fiche Capacité : {capability_id.upper()} ]",
        title_align="left",
        border_style=theme_registry.get_style("border.accent"),
        padding=(1, 2),
    )

    return main_panel


def get_diagnostics(registry: CapabilityRegistry) -> Any:
    """1.4: Return recent diagnostics (missing/degraded capabilities)."""
    capabilities = registry.list_all()

    issues = [
        cap for cap in capabilities
        if cap.status in (
            CapabilityStatus.MISSING,
            CapabilityStatus.DEGRADED,
            CapabilityStatus.DISQUALIFIED,
        )
    ]

    if not issues:
        return Panel(
            Text("✔ Aucun incident ni diagnostic d'erreur. Tout le système est opérationnel.", style=theme_registry.get_style("status.available"), justify="center"),
            title="[ Diagnostic Système ]",
            border_style=theme_registry.get_style("action.success"),
            padding=(1, 2),
        )

    table = Table(
        title="DÉTAIL DE LA CAPACITÉ",
        title_style=theme_registry.get_style("text.heading"),
        expand=True,
        show_header=True,
        border_style=theme_registry.get_style("border.accent"),
        box=box.SQUARE,                              # ← 1. Trait fin uniforme (supprime le trait lourd)
        header_style=theme_registry.get_style("border.accent"),  # ← 2. Police des titres de colonnes à la couleur de la bordure
    )
    table.add_column("Statut", width=16)
    table.add_column("Capacité", style=theme_registry.get_style("text.main"), width=24)
    table.add_column("Anomalie / Motif d'échec", style=theme_registry.get_style("status.degraded"))

    for cap in sorted(issues, key=lambda c: c.id):
        table.add_row(_get_status_badge(cap.status), cap.id.upper(), cap.reason or "Aucun motif fourni")

    return table


def search_diagnostics(registry: CapabilityRegistry, keyword: str = "") -> Any:
    """1.6: Search diagnostics by keyword."""
    capabilities = registry.list_all()

    if keyword:
        kw = keyword.lower()
        capabilities = [
            cap for cap in capabilities
            if kw in cap.id.lower()
            or kw in (cap.reason or "").lower()
            or kw in str(getattr(cap, "detail", "") or "").lower()
        ]

    if not capabilities:
        msg = f"🔍 Aucun diagnostic ou composant ne correspond à la recherche '{keyword}'." if keyword else "✔ Aucun diagnostic d'erreur récent."
        return Panel(Text(msg, justify="center"), title="[ Recherche ]", border_style=theme_registry.get_style("action.warning"))

    table = Table(
        title=f"RÉSULTATS DE RECHERCHE : '{keyword}'" if keyword else "TOUS LES DIAGNOSTICS",
        title_style=theme_registry.get_style("text.heading"),
        expand=True,
        border_style=theme_registry.get_style("border.accent"),
        box=box.SQUARE,
        header_style=theme_registry.get_style("border.accent"),
    )
    table.add_column("Statut", width=16)
    table.add_column("Capacité", width=24)
    table.add_column("Diagnostics / Raison")

    for cap in sorted(capabilities, key=lambda c: c.id):
        table.add_row(_get_status_badge(cap.status), cap.id.upper(), cap.reason or "—")

    return Group(table, Text(""), Text(f"  Total trouvé(s) : {len(capabilities)} élément(s)", style=theme_registry.get_style("text.muted")))


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Rendu Rich (badges, tableaux, panels) pour les écrans de capacités
#   (Section 1 du menu : 1.1 vue d'ensemble, 1.2 détail, 1.4 diagnostics,
#   1.6 recherche).
# - Ne modifie jamais le registre, seulement lecture via CapabilityRegistry.
#
# Pourquoi dans interfaces/cli/renderers/ (charte) :
# - C'est du rendu pur (Panel/Table/Text/Group), pas une query de données.
# - Utilise theme_registry (interfaces/cli/themes/) — dépendance légitime
#   à ce niveau, contrairement à application/queries/ d'où ce module a
#   été déplacé le 2026-08-16 (dépendance inversée corrigée).
#
# Ce qu'il ne contient PAS :
# ❌ Pas de couleur codée en dur (tout passe par theme_registry.get_style())
# ❌ Pas de modification du registre
# ❌ Pas d'appels système
# ❌ Pas de logique métier (domain/)
#
# Points clés :
# - _get_status_badge() : badge coloré via status.available/degraded/
#   missing/disqualified (clés de thème dédiées à cet usage précis).
# - get_all_capabilities() : Menu 1.1, toutes les capacités + résumé.
# - get_capability_detail() : Menu 1.2, fiche détaillée d'une capacité.
# - get_diagnostics() : Menu 1.4, uniquement les capacités en incident.
# - search_diagnostics() : Menu 1.6, recherche par mot-clé.
# - get_available_capabilities()/get_capability_count() (ancien fichier) :
#   confirmées sans appelant réel, non reprises ici — code mort retiré,
#   pas déplacé.
#---------------------------------------------------------------------->
