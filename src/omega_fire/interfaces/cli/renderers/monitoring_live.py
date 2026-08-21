# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Live monitoring dashboard renderer for Omega-Fire CLI.

Provides real-time monitoring view (Menus 8.1/8.2) with Rich Live display.
Shows conntrack sessions, network throughput, bans per minute, and dynamic graphs.

Conforms to Omega-Fire architecture charter:
- Pure rendering logic, no business rules
- Uses theme_registry for all styling (no hardcoded colors)
- Consumes MonitoringPort via injected provider (no direct system calls)
- No dependency on domain/, application/, or infrastructure/
"""
from __future__ import annotations

import threading
import time
from collections import deque
from datetime import datetime
from typing import Any, Deque, Optional

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from omega_fire.interfaces.cli.themes.registry import theme_registry
from omega_fire.interfaces.cli.renderers.styles import (
    get_terminal_width,
    get_terminal_height,
)


# ----------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------
DEFAULT_REFRESH_RATE = 2  # Refresh every 2 seconds
MAX_GRAPH_POINTS = 30  # Keep last 30 data points for graphs


# ----------------------------------------------------------------------
# Monitoring snapshot provider protocol
# ----------------------------------------------------------------------
class MonitoringSnapshotProvider:
    """Protocol for monitoring snapshot providers (injected from application layer).
    
    Implementations must provide a `get_snapshot()` method that returns
    a MonitoringSnapshot (from ports/monitoring.py).
    """
    
    def get_snapshot(self) -> Any:
        """Return current monitoring snapshot."""
        raise NotImplementedError


# ----------------------------------------------------------------------
# Data buffer for graphs (thread-safe)
# ----------------------------------------------------------------------
class MonitoringBuffer:
    """Thread-safe buffer for monitoring time-series data."""
    
    def __init__(self, max_points: int = MAX_GRAPH_POINTS):
        self._bans_per_minute: Deque[tuple[datetime, int]] = deque(maxlen=max_points)
        self._connections: Deque[tuple[datetime, int]] = deque(maxlen=max_points)
        self._throughput_in: Deque[tuple[datetime, int]] = deque(maxlen=max_points)
        self._throughput_out: Deque[tuple[datetime, int]] = deque(maxlen=max_points)
        self._lock = threading.Lock()
    
    def add_snapshot(self, snapshot: Any) -> None:
        """Add a monitoring snapshot to the buffer."""
        with self._lock:
            now = datetime.now()
            
            # Extract data from snapshot
            active_conns = getattr(snapshot, "active_connections", 0)
            self._connections.append((now, active_conns))
            
            # Bans per minute (if available)
            bans_per_min = getattr(snapshot, "bans_per_minute", {})
            total_bans = sum(bans_per_min.values()) if isinstance(bans_per_min, dict) else 0
            self._bans_per_minute.append((now, total_bans))
            
            # Throughput (if available)
            counters = getattr(snapshot, "counters", None)
            if counters:
                incoming = getattr(counters, "incoming_bytes", 0)
                outgoing = getattr(counters, "outgoing_bytes", 0)
                self._throughput_in.append((now, incoming))
                self._throughput_out.append((now, outgoing))
    
    def get_data(self) -> dict:
        """Return all buffered data."""
        with self._lock:
            return {
                "bans_per_minute": list(self._bans_per_minute),
                "connections": list(self._connections),
                "throughput_in": list(self._throughput_in),
                "throughput_out": list(self._throughput_out),
            }


# ----------------------------------------------------------------------
# Rendering functions
# ----------------------------------------------------------------------
def _render_conntrack_panel(snapshot: Any, use_emoji: bool) -> Panel:
    """Render the conntrack sessions panel."""
    content = Text()
    
    conntrack = getattr(snapshot, "conntrack_entries", [])
    active = getattr(snapshot, "active_connections", 0)
    
    conn_icon = "🔗" if use_emoji else "CONN"
    active_icon = "⚡" if use_emoji else "ACT"
    
    content.append(f"  {conn_icon} Sessions conntrack : {len(conntrack)}\n",
                   style=theme_registry.get_style("text.main"))
    content.append(f"  {active_icon} Connexions actives : {active}\n",
                   style=theme_registry.get_style("text.info"))
    
    # Show top 5 conntrack entries
    if conntrack:
        content.append("\n  Top 5 sessions :\n", style=theme_registry.get_style("text.heading"))
        for i, entry in enumerate(conntrack[:5], 1):
            src_ip = getattr(entry, "source_ip", "N/A")
            dst_ip = getattr(entry, "destination_ip", "N/A")
            state = getattr(entry, "state", "N/A")
            content.append(f"    {i}. {src_ip} → {dst_ip} [{state}]\n",
                          style=theme_registry.get_style("text.main"))
    
    return Panel(
        content,
        title="Conntrack & Connexions",
        title_align="left",
        border_style=theme_registry.get_style("border.default"),
        padding=(0, 1),
    )


def _render_network_panel(snapshot: Any, use_emoji: bool) -> Panel:
    """Render the network throughput panel."""
    content = Text()
    
    counters = getattr(snapshot, "counters", None)
    if counters:
        incoming = getattr(counters, "incoming_bytes", 0)
        outgoing = getattr(counters, "outgoing_bytes", 0)
        dropped = getattr(counters, "dropped_packets", 0)
        accepted = getattr(counters, "accepted_packets", 0)
        
        in_icon = "↓" if use_emoji else "IN"
        out_icon = "↑" if use_emoji else "OUT"
        drop_icon = "🚫" if use_emoji else "DRP"
        acc_icon = "✅" if use_emoji else "ACC"
        
        content.append(f"  {in_icon} Débit entrant  : {_bytes_to_human(incoming)}/s\n",
                       style=theme_registry.get_style("text.info"))
        content.append(f"  {out_icon} Débit sortant  : {_bytes_to_human(outgoing)}/s\n",
                       style=theme_registry.get_style("text.info"))
        content.append(f"  {drop_icon} Paquets dropés : {dropped}\n",
                       style=theme_registry.get_style("text.danger"))
        content.append(f"  {acc_icon} Paquets acceptés: {accepted}\n",
                       style=theme_registry.get_style("status.available"))
    
    return Panel(
        content,
        title="Débit Réseau",
        title_align="left",
        border_style=theme_registry.get_style("border.default"),
        padding=(0, 1),
    )


def _render_bans_panel(snapshot: Any, use_emoji: bool) -> Panel:
    """Render the bans per minute panel."""
    content = Text()
    
    bans_per_min = getattr(snapshot, "bans_per_minute", {})
    
    ban_icon = "🚫" if use_emoji else "BAN"
    
    if isinstance(bans_per_min, dict):
        total = sum(bans_per_min.values())
        content.append(f"  {ban_icon} Bans totaux (1min) : {total}\n",
                       style=theme_registry.get_style("text.danger"))
        
        if bans_per_min:
            content.append("\n  Par backend :\n", style=theme_registry.get_style("text.heading"))
            for backend, count in bans_per_min.items():
                content.append(f"    • {backend:<12} : {count}\n",
                              style=theme_registry.get_style("text.main"))
    else:
        content.append(f"  {ban_icon} Bans (1min) : N/A\n",
                       style=theme_registry.get_style("text.muted"))
    
    return Panel(
        content,
        title="Bans par Minute",
        title_align="left",
        border_style=theme_registry.get_style("border.default"),
        padding=(0, 1),
    )


def _render_graph_panel(data: list[tuple[datetime, int]], title: str, use_emoji: bool) -> Panel:
    """Render a simple ASCII graph."""
    if not data:
        content = Text("  Aucune donnée", style=theme_registry.get_style("text.muted"))
    else:
        # Extract values
        values = [v for _, v in data]
        max_val = max(values) if values else 1
        min_val = min(values) if values else 0
        
        # Simple bar chart
        content = Text()
        for i, (timestamp, value) in enumerate(data[-10:]):  # Last 10 points
            bar_width = int((value / max_val) * 20) if max_val > 0 else 0
            bar = "█" * bar_width
            time_str = timestamp.strftime("%H:%M:%S")
            content.append(f"  {time_str} {bar:<20} {value}\n",
                          style=theme_registry.get_style("text.info"))
    
    return Panel(
        content,
        title=title,
        title_align="left",
        border_style=theme_registry.get_style("border.default"),
        padding=(0, 1),
    )


def _bytes_to_human(num_bytes: int) -> str:
    """Convert bytes to human-readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if num_bytes < 1024:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} TB"


# ----------------------------------------------------------------------
# Main live renderer
# ----------------------------------------------------------------------
def render_monitoring_live(
    snapshot_provider: MonitoringSnapshotProvider,
    console: Optional[Console] = None,
    refresh_rate: float = DEFAULT_REFRESH_RATE,
) -> None:
    """Render live monitoring dashboard with real-time updates.
    
    Args:
        snapshot_provider: Provider that supplies monitoring snapshots.
        console: Rich console (created if None).
        refresh_rate: Refresh interval in seconds.
    """
    console = console or Console()
    theme = theme_registry.get_active()
    use_emoji = theme.prefers_emojis
    
    buffer = MonitoringBuffer()
    stop_event = threading.Event()
    
    def fetch_loop():
        """Background thread to fetch new snapshots."""
        while not stop_event.is_set():
            try:
                snapshot = snapshot_provider.get_snapshot()
                buffer.add_snapshot(snapshot)
            except Exception:
                pass  # Silently ignore provider errors
            stop_event.wait(refresh_rate)
    
    def build_layout() -> Layout:
        """Build the live layout."""
        root = Layout()
        root.split_column(
            Layout(name="header", size=3),
            Layout(name="body", ratio=1),
            Layout(name="footer", size=3),
        )
        
        # Header
        header_text = Text()
        shield = "\U0001f6e1\ufe0f " if use_emoji else ""
        header_text.append(f"{shield}OMEGA-FIRE v3.0", style=theme_registry.get_style("menu.title"))
        header_text.append("  |  ", style=theme_registry.get_style("text.muted"))
        header_text.append("Live Monitoring", style=theme_registry.get_style("text.heading"))
        
        root["header"].update(
            Panel(header_text, border_style=theme_registry.get_style("border.default"), padding=(0, 2))
        )
        
        # Body - 2x2 grid
        body = Layout()
        body.split_row(
            Layout(name="left", ratio=1),
            Layout(name="right", ratio=1),
        )
        
        left = Layout()
        left.split_column(
            Layout(name="conntrack", ratio=1),
            Layout(name="network", ratio=1),
        )
        
        right = Layout()
        right.split_column(
            Layout(name="bans", ratio=1),
            Layout(name="graphs", ratio=1),
        )
        
        # Get latest snapshot and buffered data
        try:
            snapshot = snapshot_provider.get_snapshot()
        except Exception:
            snapshot = None
        
        data = buffer.get_data()
        
        if snapshot:
            left["conntrack"].update(_render_conntrack_panel(snapshot, use_emoji))
            left["network"].update(_render_network_panel(snapshot, use_emoji))
            right["bans"].update(_render_bans_panel(snapshot, use_emoji))
        else:
            left["conntrack"].update(Panel("N/A", border_style=theme_registry.get_style("border.default")))
            left["network"].update(Panel("N/A", border_style=theme_registry.get_style("border.default")))
            right["bans"].update(Panel("N/A", border_style=theme_registry.get_style("border.default")))
        
        # Graphs
        graphs_layout = Layout()
        graphs_layout.split_column(
            Layout(name="conn_graph", ratio=1),
            Layout(name="ban_graph", ratio=1),
        )
        
        graphs_layout["conn_graph"].update(
            _render_graph_panel(data["connections"], "Graphique Connexions", use_emoji)
        )
        graphs_layout["ban_graph"].update(
            _render_graph_panel(data["bans_per_minute"], "Graphique Bans", use_emoji)
        )
        
        right["graphs"].update(graphs_layout)
        
        body["left"].update(left)
        body["right"].update(right)
        root["body"].update(body)
        
        # Footer (Strictement conforme à la demande)
        footer_text = Text()
        footer_text.append("[m]", style=theme_registry.get_style("footer.key"))
        footer_text.append("enu  ", style=theme_registry.get_style("footer.label"))
        footer_text.append("|  ", style=theme_registry.get_style("footer.separator"))
        footer_text.append("[t]", style=theme_registry.get_style("footer.key"))
        footer_text.append("heme  ", style=theme_registry.get_style("footer.label"))
        footer_text.append("|  ", style=theme_registry.get_style("footer.separator"))
        footer_text.append("[a]", style=theme_registry.get_style("footer.key"))
        footer_text.append("ide  ", style=theme_registry.get_style("footer.label"))
        footer_text.append("|  ", style=theme_registry.get_style("footer.separator"))
        footer_text.append("[esc]", style=theme_registry.get_style("footer.key"))
        footer_text.append(" Retour  ", style=theme_registry.get_style("footer.label"))
        footer_text.append("|  ", style=theme_registry.get_style("footer.separator"))
        footer_text.append("[q]", style=theme_registry.get_style("footer.key"))
        footer_text.append("uitter", style=theme_registry.get_style("footer.label"))
        
        root["footer"].update(
            Panel(footer_text, border_style=theme_registry.get_style("border.default"), padding=(0, 2))
        )
        
        return root
    
    # Start background fetch thread
    fetch_thread = threading.Thread(target=fetch_loop, daemon=True)
    fetch_thread.start()
    
    try:
        with Live(build_layout(), console=console, screen=True, refresh_per_second=2) as live:
            while not stop_event.is_set():
                live.update(build_layout())
                time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        fetch_thread.join(timeout=1.0)


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Rendu live du monitoring en temps réel (menus 8.1/8.2).
# - Affichage dynamique avec Rich Live (rafraîchissement toutes les 2s).
# - Affiche : conntrack sessions, débit réseau, bans par minute, graphiques.
# - Buffer circulaire thread-safe pour les séries temporelles.
#
# Pourquoi dans interfaces/cli/renderers/ (charte) :
# - Rendu pur, aucune logique métier.
# - Utilise uniquement Rich (Live, Layout, Panel, Table, Text).
# - Utilise theme_registry pour tous les styles (pas de couleurs hardcodées).
# - Consomme un MonitoringSnapshotProvider injecté (pas d'appels système directs).
# - Aucune dépendance vers domain/, application/, ou infrastructure/.
#
# Ce qu'il ne contient PAS :
# ❌ Pas d'appels système directs (conntrack -L, etc.).
# ❌ Pas de logique métier (c'est le rôle de application/queries/).
# ❌ Pas de couleurs hardcodées.
# ❌ Pas de dépendance vers infrastructure/.
#
# Points clés :
# - MonitoringSnapshotProvider : Protocol pour injecter le fournisseur de snapshots.
# - MonitoringBuffer : Buffer circulaire thread-safe pour séries temporelles.
# - _render_conntrack_panel() : Panneau conntrack avec top 5 sessions.
# - _render_network_panel() : Panneau débit réseau (entrant/sortant/drop/accept).
# - _render_bans_panel() : Panneau bans par minute (par backend).
# - _render_graph_panel() : Graphique ASCII simple (barres horizontales).
# - render_monitoring_live() : Fonction principale avec thread de fetch + Live display.
# - Gestion propre de l'arrêt (stop_event + join).
#---------------------------------------------------------------------->
