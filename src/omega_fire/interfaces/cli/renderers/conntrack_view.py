# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Conntrack status renderer for Omega-Fire CLI (menu 8.2).

Renders the current tracked network connections as a Rich Table, with
a summary panel above (totals by protocol/state). Replaces the plain-
text format_conntrack_table() previously living in
application/queries/conntrack_status.py — a charter violation the
query's own docstring documented but never respected (rendering
belongs in interfaces/, never in application/).

Conforms to Omega-Fire architecture charter:
- Pure rendering logic, no business rules
- Uses theme_registry for all styling (no hardcoded colors)
- Consumes ConntrackStatusResult (application/queries/conntrack_status.py)
  as plain data, never fetches or filters connections itself
"""
from rich.box import ROUNDED
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from omega_fire.interfaces.cli.themes.registry import theme_registry


def _state_style(state: str):
    """Map a connection state to a theme style, consistent with the
    color conventions already used across the project (established =
    healthy/available, transitional = warning/muted)."""
    if state == "ESTABLISHED":
        return theme_registry.get_style("status.available")
    elif state in ("TIME_WAIT", "CLOSE_WAIT", "LAST_ACK", "FIN_WAIT", "CLOSED"):
        return theme_registry.get_style("text.muted")
    elif state in ("SYN_SENT", "SYN_RECV", "NEW"):
        return theme_registry.get_style("text.warning")
    return theme_registry.get_style("text.main")


def render_conntrack_summary(result) -> Panel:
    """Render the summary panel (totals by protocol/state)."""
    style_main = theme_registry.get_style("text.main")
    style_info = theme_registry.get_style("text.info")
    style_muted = theme_registry.get_style("text.muted")
    border_style = theme_registry.get_style("border.default")

    content = Text()
    content.append(f"Total connexions : ", style=style_main)
    content.append(f"{result.total_count}\n", style=style_info)

    if result.by_protocol:
        content.append("Par protocole    : ", style=style_main)
        proto_parts = []
        for proto, count in result.by_protocol.items():
            proto_parts.append(f"{proto}: {count}")
        content.append(" | ".join(proto_parts), style=style_muted)
        content.append("\n")

    if result.by_state:
        content.append("Par état         : ", style=style_main)
        state_parts = []
        for state, count in result.by_state.items():
            state_parts.append(f"{state}: {count}")
        content.append(" | ".join(state_parts), style=style_muted)

    return Panel(content, title="Résumé", title_align="left", border_style=border_style, expand=True)


def render_conntrack_table(result) -> Table:
    """Render the detailed connections table."""
    style_border = theme_registry.get_style("border.default")
    style_heading = theme_registry.get_style("text.heading")
    style_muted = theme_registry.get_style("text.muted")
    style_main = theme_registry.get_style("text.main")

    table = Table(box=ROUNDED, border_style=style_border, header_style=style_heading, expand=True)
    table.add_column("Proto", style=style_muted, width=6)
    table.add_column("Source", style=style_main)
    table.add_column("Destination", style=style_main)
    table.add_column("État", justify="center", width=14)
    table.add_column("Paquets", justify="right", style=style_muted, width=9)
    table.add_column("Octets", justify="right", style=style_muted, width=10)

    if not result.entries:
        table.add_row("-", "Aucune connexion trouvée", "-", "-", "-", "-")
        return table

    for entry in result.entries:
        source = f"{entry.source_ip}:{entry.source_port}" if entry.source_port else entry.source_ip
        dest = f"{entry.destination_ip}:{entry.destination_port}" if entry.destination_port else entry.destination_ip

        # Champs vides rendus explicites plutôt que silencieusement
        # blancs — signale un trou de collecte côté ConntrackAdapter
        # au lieu de le masquer dans l'alignement du tableau.
        source_display = source if source.strip(":") else "?"
        dest_display = dest if dest.strip(":") else "?"

        table.add_row(
            entry.protocol or "?",
            source_display[:28],
            dest_display[:28],
            Text(entry.state or "?", style=_state_style(entry.state)),
            str(entry.packets),
            str(entry.bytes),
        )

    return table


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Rendu Rich de l'état des connexions conntrack (menu 8.2) : panneau
#   résumé (totaux par protocole/état) + tableau détaillé coloré par
#   état de connexion.
# - Remplace format_conntrack_table() (application/queries/
#   conntrack_status.py, retirée) — correction d'une violation de
#   charte documentée mais jamais respectée dans ce fichier (rendu en
#   texte brut construit dans application/, alors que la charte exige
#   que tout rendu vive dans interfaces/).
#
# Pourquoi dans interfaces/cli/renderers/ (charte) :
# - Rendu pur, aucune logique métier ni collecte de données.
# - Consomme ConntrackStatusResult tel quel, ne filtre ni ne calcule
#   rien lui-même (délégué à get_conntrack_status()).
# - Utilise uniquement theme_registry, aucune couleur codée en dur.
#
# Ce qu'il ne contient PAS :
# ❌ Pas d'appel à MonitoringPort ni à ConntrackAdapter
# ❌ Pas de filtrage par protocole/état (délégué en amont)
# ❌ Pas de dépendance vers domain/, application/, ou infrastructure/
#
# Points clés :
# - _state_style() : mapping état → style thème (ESTABLISHED = healthy,
#   états transitoires = warning/muted), cohérent avec les conventions
#   déjà utilisées ailleurs dans le projet
# - render_conntrack_summary() : panneau totaux par protocole/état
# - render_conntrack_table() : tableau détaillé, champs vides affichés
#   comme "?" plutôt que silencieusement blancs (bug de collecte
#   observé en test réel : certaines entrées ConntrackAdapter arrivent
#   avec source_ip="" — visible ici, non corrigé dans ce chantier)
#
# Comment il sera utilisé (aperçu) :
# - interfaces/cli/actions.py (menu 8.2) appellera les deux fonctions
#   directement pour l'affichage CLI
#---------------------------------------------------------------------->
