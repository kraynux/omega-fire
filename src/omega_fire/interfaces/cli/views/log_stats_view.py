# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Log Stats View Renderer for Omega-Fire CLI.

Provides interactive Log Statistics dashboard (Menu 5.8).
Calculates stats dynamically, listens to key bindings ('1', '2', '3', 'r', 't', 'q', ESC)
without screen flickering or layout distortion.

Conforms to Omega-Fire architecture charter:
- Uses theme_registry for all styling via safe lookup
- Non-blocking TTY keyboard input matching logs_live.py
"""
from __future__ import annotations

import fcntl
import os
import select
import sys
import threading
import time
from typing import Optional

try:
    import termios
    import tty
    HAS_TERMIOS = True
except ImportError:
    HAS_TERMIOS = False

from rich import box
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.style import Style
from rich.text import Text

from omega_fire.infrastructure.logging.stats.log_aggregator import LogAggregator
from omega_fire.interfaces.cli.themes.registry import theme_registry
from omega_fire.interfaces.cli.renderers.styles import (
    get_terminal_width,
    get_terminal_height,
)
from omega_fire.interfaces.cli.renderers.stats.kpi_cards import render_kpi_cards
from omega_fire.interfaces.cli.renderers.stats.ascii_charts import render_hourly_chart
from omega_fire.interfaces.cli.renderers.stats.stat_tables import render_stat_tables


# ----------------------------------------------------------------------
# Helpers (Identiques à logs_live.py)
# ----------------------------------------------------------------------
def _get_key_non_blocking() -> Optional[str]:
    """Lit une touche en ignorant la molette et les séquences ANSI complexes."""
    if HAS_TERMIOS and sys.stdin.isatty():
        if select.select([sys.stdin], [], [], 0.0)[0]:
            try:
                fd = sys.stdin.fileno()
                old_flags = fcntl.fcntl(fd, fcntl.F_GETFL)
                fcntl.fcntl(fd, fcntl.F_SETFL, old_flags | os.O_NONBLOCK)

                try:
                    data = sys.stdin.read(1024)
                except Exception:
                    data = ""
                finally:
                    fcntl.fcntl(fd, fcntl.F_SETFL, old_flags)

                if not data:
                    return None

                if data.startswith("\x1b"):
                    if len(data) == 1:
                        return "esc"
                    return None

                return data[0]

            except Exception:
                return None
    return None


def _get_theme_style(style_key: str) -> Style:
    """Récupère impérativement les styles depuis theme_registry de manière sécurisée."""
    try:
        style = theme_registry.get_style(style_key)
        if isinstance(style, Style):
            return style
        if isinstance(style, str):
            return Style.parse(style)
    except Exception:
        pass
    return Style.null()


def _get_available_themes() -> list[str]:
    try:
        if hasattr(theme_registry, "get_available_themes"):
            return list(theme_registry.get_available_themes())
        elif hasattr(theme_registry, "list_themes"):
            return list(theme_registry.list_themes())
        elif hasattr(theme_registry, "_themes"):
            return list(theme_registry._themes.keys())
    except Exception:
        pass
    return []


def _get_current_theme() -> str:
    try:
        if hasattr(theme_registry, "get_active_theme_name"):
            return theme_registry.get_active_theme_name()
        elif hasattr(theme_registry, "_active_theme_name"):
            return theme_registry._active_theme_name
        elif hasattr(theme_registry, "get_active"):
            active = theme_registry.get_active()
            return getattr(active, "name", "")
    except Exception:
        pass
    return ""


# ----------------------------------------------------------------------
# Main Dashboard Renderer
# ----------------------------------------------------------------------
def show_log_stats_dashboard(console: Optional[Console] = None) -> None:
    """Affiche le Dashboard Interactif 5.8 sur le modèle strict de logs_live.py."""
    console = console or Console()
    aggregator = LogAggregator()

    state = {
        "period": "24h",
        "show_help": False,
    }

    def build_layout() -> Layout:
        active_theme_obj = theme_registry.get_active()
        use_emoji = getattr(active_theme_obj, "prefers_emojis", True)
        summary = aggregator.get_summary(period_code=state["period"])

        root = Layout()
        root.split_column(
            Layout(name="header", size=3),
            Layout(name="body", ratio=1),
            Layout(name="footer", size=3),
        )

        # --- Header ---
        header_text = Text(no_wrap=True)
        if use_emoji:
            header_text.append("📊 ", style=_get_theme_style("menu.title"))
        header_text.append("STATISTIQUES DES LOGS", style=_get_theme_style("menu.title"))
        header_text.append("  │  ", style=_get_theme_style("text.muted"))
        header_text.append(f"Période: {state['period']}", style=_get_theme_style("text.heading"))
        header_text.append("  │  ", style=_get_theme_style("text.muted"))
        header_text.append(f"Source: {summary.data_source}", style=_get_theme_style("text.muted"))
        header_text.append("  │  ", style=_get_theme_style("text.muted"))
        header_text.append(
            f"Terminal: {get_terminal_width()}x{get_terminal_height()}",
            style=_get_theme_style("text.muted"),
        )

        root["header"].update(
            Panel(
                header_text,
                border_style=_get_theme_style("border.default"),
                box=box.ROUNDED,
                padding=(0, 2),
            )
        )

        # --- Body ---
        body = Layout()
        body.split_column(
            Layout(name="kpi", size=5),
            Layout(name="chart", size=9),
            Layout(name="tables", ratio=1),
        )

        body["kpi"].update(render_kpi_cards(summary))
        body["chart"].update(render_hourly_chart(summary, height=4))
        body["tables"].update(render_stat_tables(summary))
        root["body"].update(body)

        # --- Footer ---
        footer_text = Text(no_wrap=True)
        footer_text.append("[1]", style=_get_theme_style("footer.key"))
        footer_text.append(" 24h  ", style=_get_theme_style("footer.label"))
        footer_text.append("|  ", style=_get_theme_style("footer.separator"))

        footer_text.append("[2]", style=_get_theme_style("footer.key"))
        footer_text.append(" 7d  ", style=_get_theme_style("footer.label"))
        footer_text.append("|  ", style=_get_theme_style("footer.separator"))

        footer_text.append("[3]", style=_get_theme_style("footer.key"))
        footer_text.append(" 30d  ", style=_get_theme_style("footer.label"))
        footer_text.append("|  ", style=_get_theme_style("footer.separator"))

        footer_text.append("[r]", style=_get_theme_style("footer.key"))
        footer_text.append(" efresh  ", style=_get_theme_style("footer.label"))
        footer_text.append("|  ", style=_get_theme_style("footer.separator"))

        footer_text.append("[t]", style=_get_theme_style("footer.key"))
        footer_text.append(" heme  ", style=_get_theme_style("footer.label"))
        footer_text.append("|  ", style=_get_theme_style("footer.separator"))

        footer_text.append("[q]", style=_get_theme_style("footer.key"))
        footer_text.append(" uitter", style=_get_theme_style("footer.label"))

        root["footer"].update(
            Panel(
                footer_text,
                border_style=_get_theme_style("border.default"),
                box=box.ROUNDED,
                padding=(0, 2),
            )
        )

        return root

    # Config TTY initiale
    old_settings = None
    if HAS_TERMIOS and sys.stdin.isatty():
        try:
            old_settings = termios.tcgetattr(sys.stdin)
            tty.setcbreak(sys.stdin.fileno())
        except Exception:
            old_settings = None

    try:
        with Live(build_layout(), console=console, screen=True, refresh_per_second=4) as live:
            while True:
                key = _get_key_non_blocking()
                if key:
                    key_lower = key.lower()

                    # [q] / [m] / [ESC] -> Quitter
                    if key_lower in ("q", "m") or key == "esc":
                        break

                    # [1] -> Période 24h
                    elif key_lower == "1":
                        state["period"] = "24h"

                    # [2] -> Période 7d
                    elif key_lower == "2":
                        state["period"] = "7d"

                    # [3] -> Période 30d
                    elif key_lower == "3":
                        state["period"] = "30d"

                    # [r] -> Rafraîchir
                    elif key_lower == "r":
                        pass

                    # [t] -> Bascule dynamique du thème
                    elif key_lower == "t":
                        themes_list = _get_available_themes()
                        current = _get_current_theme()

                        if themes_list:
                            next_idx = (
                                (themes_list.index(current) + 1) % len(themes_list)
                                if current in themes_list
                                else 0
                            )
                            target_theme = themes_list[next_idx]

                            try:
                                if hasattr(theme_registry, "set_active"):
                                    theme_registry.set_active(target_theme, silent=True)
                                elif hasattr(theme_registry, "activate"):
                                    theme_registry.activate(target_theme)
                                elif hasattr(theme_registry, "set_theme"):
                                    theme_registry.set_theme(target_theme)
                            except Exception:
                                pass

                    live.update(build_layout())
                time.sleep(0.05)

    except KeyboardInterrupt:
        pass
    finally:
        if old_settings is not None and HAS_TERMIOS and sys.stdin.isatty():
            try:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            except Exception:
                pass
