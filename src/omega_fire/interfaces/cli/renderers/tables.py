# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Reusable Rich table renderers for Omega-Fire CLI.

Provides standardized table rendering for blacklists, rules, jails, etc.
All tables are wrapped in fixed-width Panel containers for compact display.
Tables adapt to content width (no stretching) to avoid excessive whitespace.
Uses theme_registry for consistent styling.

Conforms to Omega-Fire architecture charter:
- Pure rendering logic, no business rules
- Uses theme_registry for all styling (no hardcoded colors)
- All tables wrapped in fixed-width Panel (no expand)
- Tables use expand=False + content-adapted column widths
- No dependency on domain/, application/, or infrastructure/
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from omega_fire.interfaces.cli.themes.registry import theme_registry


# ----------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------
DEFAULT_TABLE_WIDTH = 120  # Largeur fixe des tableaux (ajustable si besoin)


# ----------------------------------------------------------------------
# Helper — Create a compact Table (content-adapted, no stretching)
# ----------------------------------------------------------------------
from rich import box
# Cadre 100% fin et uniforme (mêmes séparateurs partout) — box.SQUARE de
# Rich correspond déjà exactement à ça ; l'ancienne définition maison
# (7, puis 5 caractères par ligne au lieu des 8 lignes de 4 caractères
# attendues par box.Box) ne s'était jamais importée sans erreur, code
# mort jamais exécuté en pratique (zéro appelant réel de ce module).
FINE_UNIFORM_BOX = box.SQUARE
def _create_compact_table() -> Table:
    return Table(
        show_header=True,
        header_style=theme_registry.get_style("table.header"),
        border_style=theme_registry.get_style("border.accent"),
        box=box.SQUARE,  # ← Bordure fine 1-ligne native Rich (aucune erreur de dépaquetage)
        expand=False,
        show_lines=False,
        padding=(0, 1),
    )
# ---------------------------------------------------------
# Helper — Wrap a Table in a fixed-width Panel
# ----------------------------------------------------------------------
def _wrap_table_in_panel(
    table: Table,
    title: str,
    console: Console,
    *,
    width: int = DEFAULT_TABLE_WIDTH,
) -> None:
    """Wrap a Rich Table in a fixed-width Panel and print it.
    
    - width=N : largeur fixe (pas d'étirement)
    - title_align="left"
    - border_style du thème pour cohérence avec dashboard.py
    """
    panel = Panel(
        table,
        title=title,
        title_align="left",
        border_style=theme_registry.get_style("border.default"),
        padding=(0, 1),
        width=width,  # ← Largeur fixe
    )
    console.print(panel)


# ----------------------------------------------------------------------
# Helper — Add a column with content-adapted width
# ----------------------------------------------------------------------
def _add_column(
    table: Table,
    header: str,
    *,
    style: str = "white",
    justify: str = "left",
    width: Optional[int] = None,
    min_width: Optional[int] = None,
    no_wrap: bool = True,
) -> None:
    """Add a column to a Table with content-adapted width.
    
    Args:
        table: Table to add column to.
        header: Column header text.
        style: Rich style for the column.
        justify: Alignment (left, center, right).
        width: Fixed width (None = auto-adapt to content).
        min_width: Minimum width (None = no minimum).
        no_wrap: If True, never wrap content (default for compact display).
    """
    table.add_column(
        header,
        style=style,
        justify=justify,
        width=width,
        min_width=min_width,
        no_wrap=no_wrap,
    )


# ----------------------------------------------------------------------
# Blacklist table
# ----------------------------------------------------------------------
def render_blacklist_table(
    entries: list[dict],
    title: str = "IPs Bannies",
    console: Optional[Console] = None,
) -> None:
    """Render a compact blacklist table wrapped in a fixed-width Panel."""
    console = console or Console()
    
    table = _create_compact_table()
    
    # Largeurs adaptées au contenu (pas d'étirement)
    _add_column(table, "IP", style=theme_registry.get_style("text.main"), width=15)
    _add_column(table, "Backend", style=theme_registry.get_style("text.info"), width=10)
    _add_column(table, "Raison", style=theme_registry.get_style("text.main"), width=25)
    _add_column(table, "Banni le", style=theme_registry.get_style("text.muted"), width=19)
    _add_column(table, "Expire", style=theme_registry.get_style("text.muted"), width=19)
    _add_column(table, "Jail", style=theme_registry.get_style("text.main"), width=12)
    
    for entry in entries:
        ip = entry.get("ip", "N/A")
        backend = entry.get("backend", "N/A")
        reason = entry.get("reason", "")
        banned_at = entry.get("banned_at")
        expires_at = entry.get("expires_at")
        jail = entry.get("jail", "")
        
        banned_str = banned_at.strftime("%Y-%m-%d %H:%M:%S") if banned_at else "N/A"
        expires_str = expires_at.strftime("%Y-%m-%d %H:%M:%S") if expires_at else "Permanent"
        
        table.add_row(ip, backend, reason, banned_str, expires_str, jail)
    
    _wrap_table_in_panel(table, title, console)


# ----------------------------------------------------------------------
# Rules table
# ----------------------------------------------------------------------
def render_rules_table(
    rules: list[dict],
    title: str = "Règles Firewall",
    console: Optional[Console] = None,
) -> None:
    """Render a compact firewall rules table wrapped in a fixed-width Panel."""
    console = console or Console()
    
    table = _create_compact_table()
    
    # Largeurs adaptées au contenu
    _add_column(table, "ID", style=theme_registry.get_style("text.muted"), width=8)
    _add_column(table, "Chaîne", style=theme_registry.get_style("text.info"), width=8)
    _add_column(table, "Proto", style=theme_registry.get_style("text.main"), width=6)
    _add_column(table, "Port", style=theme_registry.get_style("text.main"), width=8)
    _add_column(table, "Source", style=theme_registry.get_style("text.main"), width=15)
    _add_column(table, "Dest", style=theme_registry.get_style("text.main"), width=15)
    _add_column(table, "Action", style=theme_registry.get_style("text.warning"), width=8)
    _add_column(table, "Packets", justify="right", style=theme_registry.get_style("text.main"), width=8)
    _add_column(table, "Bytes", justify="right", style=theme_registry.get_style("text.main"), width=10)
    
    for rule in rules:
        rule_id = rule.get("id", "N/A")
        chain = rule.get("chain", "N/A")
        protocol = rule.get("protocol", "N/A")
        port = rule.get("port", "any")
        source = rule.get("source", "any")
        destination = rule.get("destination", "any")
        action = rule.get("action", "N/A")
        packets = rule.get("packets", 0)
        bytes_val = rule.get("bytes", 0)
        
        if action == "accept":
            action_style = theme_registry.get_style("status.available")
        elif action == "drop":
            action_style = theme_registry.get_style("text.danger")
        elif action == "reject":
            action_style = theme_registry.get_style("text.warning")
        else:
            action_style = theme_registry.get_style("text.main")
        
        table.add_row(
            rule_id,
            chain,
            protocol,
            port,
            source,
            destination,
            Text(action, style=action_style),
            str(packets),
            _bytes_to_human(bytes_val),
        )
    
    _wrap_table_in_panel(table, title, console)


# ----------------------------------------------------------------------
# Jails table
# ----------------------------------------------------------------------
def render_jails_table(
    jails: list[dict],
    title: str = "Jails Fail2ban",
    console: Optional[Console] = None,
) -> None:
    """Render a compact fail2ban jails table wrapped in a fixed-width Panel."""
    console = console or Console()
    
    table = _create_compact_table()
    
    # Largeurs adaptées au contenu
    _add_column(table, "Nom", style=theme_registry.get_style("text.main"), width=12)
    _add_column(table, "Statut", style=theme_registry.get_style("text.info"), width=8)
    _add_column(table, "Bannis", justify="right", style=theme_registry.get_style("text.danger"), width=7)
    _add_column(table, "Filtre", style=theme_registry.get_style("text.main"), width=12)
    _add_column(table, "Log Path", style=theme_registry.get_style("text.muted"), width=25)
    _add_column(table, "Max Retry", justify="right", style=theme_registry.get_style("text.main"), width=9)
    _add_column(table, "Ban Time", justify="right", style=theme_registry.get_style("text.main"), width=9)
    
    for jail in jails:
        name = jail.get("name", "N/A")
        active = jail.get("active", False)
        banned_count = jail.get("banned_count", 0)
        filter_name = jail.get("filter", "N/A")
        log_path = jail.get("log_path", "N/A")
        max_retry = jail.get("max_retry", 0)
        ban_time = jail.get("ban_time", 0)
        
        if active:
            status_text = Text("Actif", style=theme_registry.get_style("status.available"))
        else:
            status_text = Text("Inactif", style=theme_registry.get_style("text.muted"))
        
        table.add_row(
            name,
            status_text,
            str(banned_count),
            filter_name,
            log_path,
            str(max_retry),
            f"{ban_time}s",
        )
    
    _wrap_table_in_panel(table, title, console)


# ----------------------------------------------------------------------
# Capabilities table
# ----------------------------------------------------------------------
def render_capabilities_table(
    capabilities: list[dict],
    title: str = "Capacités Système",
    console: Optional[Console] = None,
) -> None:
    """Render a compact capabilities table wrapped in a fixed-width Panel."""
    console = console or Console()
    
    table = _create_compact_table()
    
    # Largeurs adaptées au contenu
    _add_column(table, "ID", style=theme_registry.get_style("text.main"), width=20)
    _add_column(table, "Statut", style=theme_registry.get_style("text.info"), width=12)
    _add_column(table, "Raison", style=theme_registry.get_style("text.main"), width=30)
    _add_column(table, "Détail", style=theme_registry.get_style("text.muted"), width=25)
    _add_column(table, "Dernière vérif.", style=theme_registry.get_style("text.muted"), width=19)
    
    for cap in capabilities:
        cap_id = cap.get("id", "N/A")
        status = cap.get("status", "N/A")
        # Convertir l'enum en string si nécessaire
        if hasattr(status, 'value'):
            status = status.value
        elif not isinstance(status, str):
            status = str(status)
        reason = cap.get("reason", "")
        detail = cap.get("detail", "")
        last_checked = cap.get("last_checked")
        
        if status == "AVAILABLE":
            status_style = theme_registry.get_style("status.available")
        elif status == "DEGRADED":
            status_style = theme_registry.get_style("text.warning")
        elif status == "MISSING":
            status_style = theme_registry.get_style("text.muted")
        elif status == "DISQUALIFIED":
            status_style = theme_registry.get_style("text.danger")
        else:
            status_style = theme_registry.get_style("text.main")
        
        last_checked_str = last_checked.strftime("%Y-%m-%d %H:%M:%S") if last_checked else "N/A"
        
        table.add_row(
            cap_id,
            Text(status, style=status_style),
            reason,
            detail,
            last_checked_str,
        )
    
    _wrap_table_in_panel(table, title, console)


# ----------------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------------
def _bytes_to_human(num_bytes: int) -> str:
    """Convert bytes to human-readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if num_bytes < 1024:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} TB"

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Rendu de tableaux Rich réutilisables pour tous les affichages en tableau.
# - Fournit : blacklist, règles firewall, jails fail2ban, capacités système.
# - Tous les tableaux sont WRAPPÉS dans un Panel à LARGEUR FIXE (width=120).
# - Les tableaux s'ADAPTENT au contenu (pas d'étirement) :
#   - expand=False sur Table (largeur naturelle)
#   - Largeurs fixes sur colonnes adaptées au contenu (width=N)
#   - no_wrap=True partout (pas de wrapping)
#   - padding=(0, 0) (compact, pas d'espace entre colonnes)
# - Utilise theme_registry pour un style cohérent avec le reste de l'UI.
#
# Pourquoi dans interfaces/cli/renderers/ (charte) :
# - Rendu pur, aucune logique métier.
# - Utilise uniquement Rich (Table, Panel, Text).
# - Utilise theme_registry pour tous les styles (pas de couleurs hardcodées).
# - Aucune dépendance vers domain/, application/, ou infrastructure/.
#
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier (c'est le rôle de application/queries/).
# ❌ Pas de couleurs hardcodées.
# ❌ Pas de dépendance vers infrastructure/.
# ❌ Pas de récupération de données (les données sont injectées).
# ❌ Pas d'étirement (expand=False, width=N sur colonnes).
# ❌ Pas de wrapping (no_wrap=True partout).
# ❌ Pas de padding excessif (padding=(0, 0)).
#
# Points clés :
# - DEFAULT_TABLE_WIDTH = 120 : largeur fixe des tableaux (ajustable si besoin).
# - _create_compact_table() : crée une Table COMPACTE (expand=False, padding=(0,0),
#   box=None, show_lines=False). La table prend sa largeur naturelle.
# - _wrap_table_in_panel() : encapsule la Table dans un Panel à LARGEUR FIXE
#   (width=120, title_align="left", border_style du thème, padding=(0,1)).
# - _add_column() : helper pour ajouter une colonne avec largeur adaptée au contenu :
#   - width=N : largeur fixe (pas d'étirement)
#   - no_wrap=True : jamais de wrapping (compact)
# - Stratégie de rendu : Panel fixe + Table compacte + colonnes ajustées = pas de blanc.
# - render_blacklist_table() : Panel fixe + Table compacte (IP, backend, raison, dates, jail).
# - render_rules_table() : Panel fixe + Table compacte (avec compteurs packets/bytes colorés).
# - render_jails_table() : Panel fixe + Table compacte (statut coloré, bannis, config).
# - render_capabilities_table() : Panel fixe + Table compacte (statut coloré, raison, détail).
# - _bytes_to_human() : helper pour formater les tailles en Ko/Mo/Go.
#---------------------------------------------------------------------->
