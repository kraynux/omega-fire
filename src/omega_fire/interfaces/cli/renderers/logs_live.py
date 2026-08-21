# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Live log tail renderer for Omega-Fire CLI.

Provides real-time log monitoring (Menu 5.1) with Rich Live display.
Highlights HTTP 4xx/5xx errors and suspicious IPs dynamically.

Conforms to Omega-Fire architecture charter:
- Pure rendering logic, no business rules
- Uses theme_registry for all styling
- Consumes LogsPort via injected provider (no direct file access)
- No dependency on domain/, application/, or infrastructure/
"""
from __future__ import annotations

import select
import sys
import threading
import time
import os
import fcntl
from collections import deque
from typing import Any, Deque, Optional

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
from rich.table import Table
from rich.text import Text

from omega_fire.interfaces.cli.themes.registry import theme_registry


# ----------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------
DEFAULT_BUFFER_SIZE = 50
DEFAULT_REFRESH_RATE = 2.0


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
import os
import fcntl

def _get_key_non_blocking() -> Optional[str]:
    """Lit une touche en ignorant à 100 % la molette et les séquences ANSI complexes."""
    if HAS_TERMIOS and sys.stdin.isatty():
        if select.select([sys.stdin], [], [], 0.0)[0]:
            try:
                # Bascule temporaire en mode non-bloquant
                fd = sys.stdin.fileno()
                old_flags = fcntl.fcntl(fd, fcntl.F_GETFL)
                fcntl.fcntl(fd, fcntl.F_SETFL, old_flags | os.O_NONBLOCK)

                try:
                    data = sys.stdin.read(1024)
                except Exception:
                    data = ""
                finally:
                    # Restauration des flags d'origine
                    fcntl.fcntl(fd, fcntl.F_SETFL, old_flags)

                if not data:
                    return None

                # Si la séquence commence par Escape (\x1b)
                if data.startswith("\x1b"):
                    # Un vrai appui sur la touche ESC envoie STRICTEMENT un seul octet '\x1b'
                    if len(data) == 1:
                        return "esc"

                    # Séquences de navigation reconnues (flèches, Page Up/Down)
                    # — nécessaires pour le défilement du buffer (référentiel
                    # §84). Tout le reste (molette, séquences inconnues) reste
                    # ignoré, comme avant.
                    nav_sequences = {
                        "\x1b[A": "up",
                        "\x1b[B": "down",
                        "\x1b[5~": "pageup",
                        "\x1b[6~": "pagedown",
                    }
                    return nav_sequences.get(data)

                # Si c'est une touche classique (ex: 'q', 'm', 't', 'a')
                return data[0]

            except Exception:
                return None
    return None

def _get_theme_style(style_key: str) -> Style:
    """Récupère impérativement les styles depuis theme_registry de manière sécurisée.
    
    Retourne TOUJOURS un objet Style valide (jamais None) pour éviter les crashs de rendu Rich.
    """
    try:
        style = theme_registry.get_style(style_key)
        if isinstance(style, Style):
            return style
        if isinstance(style, str):
            return Style.parse(style)
    except Exception:
        pass

    # Style neutre conforme à la charte si la clé est introuvable
    return Style.null()


# ----------------------------------------------------------------------
# Log entry provider protocol
# ----------------------------------------------------------------------
class LogEntryProvider:
    def get_recent_logs(self, limit: int = DEFAULT_BUFFER_SIZE) -> list[dict]:
        raise NotImplementedError

# ----------------------------------------------------------------------
# Log buffer (thread-safe ring buffer)
# ----------------------------------------------------------------------
class LogBuffer:
    def __init__(self, max_size: int = DEFAULT_BUFFER_SIZE):
        self._buffer: Deque[dict] = deque(maxlen=max_size)
        self._lock = threading.Lock()
        self._start_time = time.time()
        self._stats = {
            "total": 0,
            "success_2xx": 0,
            "redirect_3xx": 0,
            "errors_4xx": 0,
            "errors_5xx": 0,
            "bytes_total": 0,
            "latency_total": 0,
            "ip_counts": {},
        }

    def add(self, entry: dict) -> None:
        if not isinstance(entry, dict):
            return
        with self._lock:
            self._buffer.appendleft(entry)
            self._stats["total"] += 1

            # 1. Statuts HTTP
            status = entry.get("status_code", 0) or 0
            try:
                status = int(status)
            except (ValueError, TypeError):
                status = 0

            if 200 <= status < 300:
                self._stats["success_2xx"] += 1
            elif 300 <= status < 400:
                self._stats["redirect_3xx"] += 1
            elif 400 <= status < 500:
                self._stats["errors_4xx"] += 1
            elif 500 <= status < 600:
                self._stats["errors_5xx"] += 1

            # 2. Capture de la Taille (avec fallback automatique si 0)
            bytes_sent = 0
            for key in ("bytes_sent", "size", "bytes", "content_length", "body_bytes_sent"):
                val = entry.get(key)
                if val is not None:
                    val_str = str(val).strip()
                    if val_str.isdigit() and int(val_str) > 0:
                        bytes_sent = int(val_str)
                        break

            # Si aucune taille valide n'est extraite (ex: serveur local avec "-"),
            # on estime la taille minimale de la transaction HTTP (en-têtes + chemin)
            if bytes_sent == 0:
                path_len = len(str(entry.get("path", "")))
                bytes_sent = 350 + path_len  # ~350 octets minimum pour une entête HTTP standard

            self._stats["bytes_total"] += bytes_sent

            # 3. Latence (ms)
            latency = 0
            for key in ("response_time_ms", "latency", "duration", "response_time"):
                val = entry.get(key)
                if val is not None:
                    val_str = str(val).strip()
                    if val_str.isdigit():
                        latency = int(val_str)
                        break
            
            if latency == 0:
                latency = 25  # Valeur par défaut si non loguée
                
            self._stats["latency_total"] += latency

            # 4. Tracking IP
            ip = entry.get("source_ip")
            if ip and ip != "N/A":
                self._stats["ip_counts"][ip] = self._stats["ip_counts"].get(ip, 0) + 1

    def get_all(self) -> list[dict]:
        with self._lock:
            return list(self._buffer)

    def get_stats(self) -> dict:
        with self._lock:
            elapsed = max(0.1, time.time() - self._start_time)
            total = self._stats["total"]
            total_errors = self._stats["errors_4xx"] + self._stats["errors_5xx"]

            error_rate = (total_errors / total * 100) if total > 0 else 0.0
            rps = total / elapsed
            bps = self._stats["bytes_total"] / elapsed
            avg_latency = (self._stats["latency_total"] / total) if total > 0 else 0.0
            avg_size = (self._stats["bytes_total"] / total) if total > 0 else 0.0

            top_ip = "N/A"
            if self._stats["ip_counts"]:
                top_ip = max(self._stats["ip_counts"], key=self._stats["ip_counts"].get)

            return {
                "total": total,
                "success_2xx": self._stats["success_2xx"],
                "redirect_3xx": self._stats["redirect_3xx"],
                "errors_4xx": self._stats["errors_4xx"],
                "errors_5xx": self._stats["errors_5xx"],
                "unique_ips": len(self._stats["ip_counts"]),
                "top_ip": top_ip,
                "error_rate": error_rate,
                "rps": rps,
                "bps": bps,
                "bytes_total": self._stats["bytes_total"],
                "avg_latency": avg_latency,
                "avg_size": avg_size,
                "buffer_size": len(self._buffer),
            }
# ----------------------------------------------------------------------
# Rendering functions
# ----------------------------------------------------------------------
def _render_stats_panel(stats: dict, use_emoji: bool) -> Panel:
    content = Text()

    # --- Helper pour formater les tailles ---
    def _format_bytes(size: float) -> str:
        if size > 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        elif size > 1024:
            return f"{size / 1024:.1f} KB"
        return f"{int(size)} B"

    # --- 1. PERFORMANCE & RENDEMENT ---
    content.append("── RENDEMENT ───────────────\n", style=_get_theme_style("menu.title"))
    rps_icon = "⚡" if use_emoji else "RPS"
    lat_icon = "⏱" if use_emoji else "LAT"
    
    content.append(f" {rps_icon} Débit      : {stats['rps']:.1f} req/s\n", style=_get_theme_style("text.info"))
    
    # Latence moyenne avec code couleur
    avg_lat = stats['avg_latency']
    lat_style = "status.available" if avg_lat < 200 else ("text.warning" if avg_lat < 500 else "text.danger")
    content.append(f" {lat_icon} Latence moy: {avg_lat:.0f} ms\n\n", style=_get_theme_style(lat_style))

    # --- 2. TRAFIC & BANDE PASSANTE ---
    content.append("── BANDE PASSANTE ──────────\n", style=_get_theme_style("menu.title"))
    net_icon = "" if use_emoji else "NET"
    tot_icon = "📦" if use_emoji else "VOL"
    
    content.append(f" {net_icon} Débit Réseau: {_format_bytes(stats['bps'])}/s\n", style=_get_theme_style("text.main"))
    content.append(f" {tot_icon} Vol. Total  : {_format_bytes(stats['bytes_total'])}\n", style=_get_theme_style("text.main"))
    content.append(f" 🗜 Taille moy. : {_format_bytes(stats['avg_size'])}\n\n", style=_get_theme_style("text.main"))

    # --- 3. RÉPARTITION DES REQUÊTES ---
    content.append("── STATUTS HTTP ────────────\n", style=_get_theme_style("menu.title"))
    content.append(f" 📊 Total Req.  : {stats['total']}\n", style=_get_theme_style("text.main"))
    content.append(f" √  Succès 2xx  : {stats['success_2xx']}\n", style=_get_theme_style("status.available"))
    content.append(f" ↔  Redir. 3xx  : {stats['redirect_3xx']}\n", style=_get_theme_style("text.info"))
    content.append(f" ⚠  Erreurs 4xx : {stats['errors_4xx']}\n", style=_get_theme_style("text.warning"))
    content.append(f" ❌ Erreurs 5xx : {stats['errors_5xx']}\n\n", style=_get_theme_style("text.danger"))

    # --- 4. RÉSEAU & CLIENTS ---
    content.append("── CLIENTS & RÉSEAU ────────\n", style=_get_theme_style("menu.title"))
    ip_icon = "💻" if use_emoji else "IP "
    content.append(f" {ip_icon} IPs uniques : {stats['unique_ips']}\n", style=_get_theme_style("text.main"))
    content.append(f" 🖧  Top Talker  : {stats['top_ip'][:14]}\n\n", style=_get_theme_style("text.info"))

    # --- 5. TAMPON & ÉTAT DE SANTÉ ---
    content.append("── RAMP & TAMPON ───────────\n", style=_get_theme_style("menu.title"))
    err_rate = stats['error_rate']
    health_style = "status.available" if err_rate < 5 else ("text.warning" if err_rate < 15 else "text.danger")
    health_label = "EXCELLENT" if err_rate < 2 else ("CORRECT" if err_rate < 10 else "DEGRADED")
    
    content.append(f" 🌡 Santé Log   : {health_label} ({err_rate:.1f}% err)\n", style=_get_theme_style(health_style))
    content.append(f" 📥 Tampon Live : {stats['buffer_size']}/{DEFAULT_BUFFER_SIZE}", style=_get_theme_style("text.main"))

    return Panel(
        content,
        title="Statistiques Live",
        title_align="left",
        border_style=_get_theme_style("border.default"),
        box=box.ROUNDED,
        padding=(1, 1),
    )

def _render_logs_table(entries: list[dict], show_help: bool, paused: bool = False, total_buffered: int = 0) -> Panel:
    if show_help:
        help_text = Text()
        help_text.append("=== AIDE LIVE TAIL ===\n\n", style=_get_theme_style("text.heading"))
        help_text.append("• [q] / [m] / [ESC] : Quitter le Live Tail\n", style=_get_theme_style("text.main"))
        help_text.append("• [↑]/[↓] [PgUp]/[PgDn] : Défiler dans l'historique (fige le direct)\n", style=_get_theme_style("text.main"))
        help_text.append("• [t]               : Basculer vers le thème suivant\n", style=_get_theme_style("text.main"))
        help_text.append("• [a]               : Masquer cet écran d'aide\n\n", style=_get_theme_style("text.main"))
        help_text.append("Code couleurs HTTP & Latence :\n", style=_get_theme_style("text.heading"))
        help_text.append("  • 2xx / <200ms  : Optimal\n", style=_get_theme_style("status.available"))
        help_text.append("  • 4xx / <500ms  : Avertissement / Latence moyenne\n", style=_get_theme_style("text.warning"))
        help_text.append("  • 5xx / >500ms  : Erreur / Latence critique\n", style=_get_theme_style("text.danger"))

        return Panel(
            help_text,
            title="Aide & Raccourcis",
            title_align="left",
            border_style=_get_theme_style("border.default"),
            box=box.ROUNDED,
            padding=(1, 2),
        )

    # Récupération du style sans l'attribut bold pour éviter le décalage de ligne sous Terminator
    header_style = _get_theme_style("table.header")
    if hasattr(header_style, "bold"):
        header_style = Style(color=header_style.color, bold=False)

    table = Table(
        show_header=True,
        header_style=header_style,
        border_style=_get_theme_style("border.default"),
        box=box.ROUNDED,
        expand=True,
        padding=(0, 1),
    )

    # Colonnes enrichies et dimensionnées proprement
    table.add_column("Timestamp", style=_get_theme_style("text.muted"), width=19, no_wrap=True)
    table.add_column("IP Source", style=_get_theme_style("text.main"), width=15, no_wrap=True)
    table.add_column("Type", width=8, no_wrap=True)
    table.add_column("Méthode", style=_get_theme_style("text.info"), width=7, no_wrap=True)
    table.add_column("Chemin", style=_get_theme_style("text.main"), ratio=1, no_wrap=True)
    table.add_column("Statut", justify="right", width=6, no_wrap=True)
    table.add_column("Taille", justify="right", style=_get_theme_style("text.muted"), width=8, no_wrap=True)
    table.add_column("Latence", justify="right", width=8, no_wrap=True)

    for entry in entries:
        # 1. Style HTTP Status
        status = entry.get("status_code", 0) or 0
        if 200 <= status < 300:
            status_style = _get_theme_style("status.available")
        elif 400 <= status < 500:
            status_style = _get_theme_style("text.warning")
        elif 500 <= status < 600:
            status_style = _get_theme_style("text.danger")
        else:
            status_style = _get_theme_style("text.muted")

        # 2. Style Latence (ms)
        latency = entry.get("response_time_ms", entry.get("latency", 0)) or 0
        if latency < 200:
            lat_style = _get_theme_style("status.available")
        elif latency < 500:
            lat_style = _get_theme_style("text.warning")
        else:
            lat_style = _get_theme_style("text.danger")
        lat_text = f"{latency}ms" if latency > 0 else "-"

        # 3. Formatage Taille (Octets / KB)
        bytes_sent = entry.get("bytes_sent", entry.get("size", 0)) or 0
        if bytes_sent > 1024 * 1024:
            size_str = f"{bytes_sent / (1024*1024):.1f}MB"
        elif bytes_sent > 1024:
            size_str = f"{bytes_sent / 1024:.1f}KB"
        elif bytes_sent > 0:
            size_str = f"{bytes_sent}B"
        else:
            size_str = "-"

        # 4. Tag de type de client (Bot / Admin / Web)
        user_agent = str(entry.get("user_agent", "")).lower()
        if "bot" in user_agent or "crawler" in user_agent:
            client_type = Text("🤖 Bot", style=_get_theme_style("text.warning"))
        elif "curl" in user_agent or "python" in user_agent or "scanner" in user_agent:
            client_type = Text("⚠ CLI", style=_get_theme_style("text.danger"))
        else:
            client_type = Text("🖧 Web", style=_get_theme_style("text.muted"))

        # Données de base nettoyées
        ts = str(entry.get("timestamp") or "").strip()[:19]
        ip = str(entry.get("source_ip") or "N/A").strip()[:15]
        method = str(entry.get("method") or "-").strip()[:6]
        path = str(entry.get("path") or "-").strip()

        table.add_row(
            ts,
            ip,
            client_type,
            method,
            path,
            Text(str(status), style=status_style),
            size_str,
            Text(lat_text, style=lat_style),
        )

    if paused:
        title = f"⏸ Défilement (figé) — {len(entries)} affichée(s) / {total_buffered} en mémoire"
    else:
        title = f"▶ Logs en temps réel ({len(entries)} / {total_buffered} entrées)"

    return Panel(
        table,
        title=title,
        title_align="left",
        border_style=_get_theme_style("border.default"),
        box=box.ROUNDED,
        padding=(0, 1),
    )


# ----------------------------------------------------------------------
# Main live renderer
# ----------------------------------------------------------------------
def render_logs_live(
    log_provider: LogEntryProvider,
    console: Optional[Console] = None,
    refresh_rate: float = DEFAULT_REFRESH_RATE,
    buffer_size: int = DEFAULT_BUFFER_SIZE,
) -> None:
    console = console or Console()
    buffer = LogBuffer(max_size=buffer_size)
    stop_event = threading.Event()

    state = {
        "show_help": False,
        "scroll_offset": 0,
        # Instantané figé du buffer, capturé au premier appui sur une touche
        # de défilement — évite que la position affichée ne dérive à chaque
        # nouvelle entrée reçue en arrière-plan pendant qu'on parcourt
        # l'historique (référentiel §84).
        "frozen_snapshot": None,
    }

    def visible_rows() -> int:
        """Nombre de lignes de log affichables compte tenu de l'espace
        vertical réel du terminal (header + footer + bordures/titre du
        panel de logs) — évite un nombre de lignes en dur qui déborderait
        ou gâcherait de l'espace selon la taille réelle du terminal."""
        return max(10, console.size.height - 14)

    def fetch_loop():
        while not stop_event.is_set():
            try:
                recent = log_provider.get_recent_logs(limit=buffer_size)
                if recent:
                    for entry in recent:
                        buffer.add(entry)
            except Exception:
                pass
            stop_event.wait(refresh_rate)

    def get_available_themes() -> list[str]:
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

    def get_current_theme() -> str:
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

    def build_layout() -> Layout:
        active_theme_obj = theme_registry.get_active()
        use_emoji = getattr(active_theme_obj, "prefers_emojis", True)

        root = Layout()
        root.split_column(
            Layout(name="header", size=3),
            Layout(name="body", ratio=1),
            Layout(name="footer", size=3),
        )

        # Header
        header_text = Text(no_wrap=True)
        if use_emoji:
            header_text.append("🛡 ", style=_get_theme_style("menu.title"))
        header_text.append("OMEGA-FIRE v3.0", style=_get_theme_style("menu.title"))
        header_text.append("  |  ", style=_get_theme_style("text.muted"))
        header_text.append("Live Logs", style=_get_theme_style("text.heading"))

        root["header"].update(
            Panel(
                header_text,
                border_style=_get_theme_style("border.default"),
                box=box.ROUNDED,
                padding=(0, 2),
            )
        )

        # Body
        body = Layout()
        body.split_row(
            Layout(name="stats", size=32),
            Layout(name="logs", ratio=2),
        )

        stats = buffer.get_stats()

        # En défilement (scroll_offset > 0), on rend depuis l'instantané figé
        # au premier appui flèche/PageUp, jamais depuis le buffer live — voir
        # le commentaire sur "frozen_snapshot" plus haut.
        if state["scroll_offset"] > 0 and state["frozen_snapshot"] is not None:
            source_entries = state["frozen_snapshot"]
        else:
            source_entries = buffer.get_all()

        total_buffered = len(source_entries)
        rows = visible_rows()
        start = min(state["scroll_offset"], max(0, total_buffered - 1))
        windowed_entries = source_entries[start:start + rows]

        body["stats"].update(_render_stats_panel(stats, use_emoji))
        body["logs"].update(
            _render_logs_table(
                windowed_entries,
                show_help=state["show_help"],
                paused=state["scroll_offset"] > 0,
                total_buffered=total_buffered,
            )
        )

        root["body"].update(body)

        # Footer
        footer_text = Text(no_wrap=True)
        footer_text.append("[m]", style=_get_theme_style("footer.key"))
        footer_text.append("enu  ", style=_get_theme_style("footer.label"))
        footer_text.append("|  ", style=_get_theme_style("footer.separator"))
        footer_text.append("[t]", style=_get_theme_style("footer.key"))
        footer_text.append("heme  ", style=_get_theme_style("footer.label"))
        footer_text.append("|  ", style=_get_theme_style("footer.separator"))
        footer_text.append("[a]", style=_get_theme_style("footer.key"))
        footer_text.append("ide  ", style=_get_theme_style("footer.label"))
        footer_text.append("|  ", style=_get_theme_style("footer.separator"))
        footer_text.append("[↑↓/PgUp/PgDn]", style=_get_theme_style("footer.key"))
        footer_text.append(" Défiler  ", style=_get_theme_style("footer.label"))
        footer_text.append("|  ", style=_get_theme_style("footer.separator"))
        footer_text.append("[esc]", style=_get_theme_style("footer.key"))
        footer_text.append(" Retour  ", style=_get_theme_style("footer.label"))
        footer_text.append("|  ", style=_get_theme_style("footer.separator"))
        footer_text.append("[q]", style=_get_theme_style("footer.key"))
        footer_text.append("uitter", style=_get_theme_style("footer.label"))

        root["footer"].update(
            Panel(
                footer_text,
                border_style=_get_theme_style("border.default"),
                box=box.ROUNDED,
                padding=(0, 2),
            )
        )

        return root

    # TTY Setup
    old_settings = None
    if HAS_TERMIOS and sys.stdin.isatty():
        try:
            old_settings = termios.tcgetattr(sys.stdin)
            tty.setcbreak(sys.stdin.fileno())
        except Exception:
            old_settings = None

    fetch_thread = threading.Thread(target=fetch_loop, daemon=True)
    fetch_thread.start()

    try:
        with Live(build_layout(), console=console, screen=True, refresh_per_second=4) as live:
            while not stop_event.is_set():
                key = _get_key_non_blocking()
                if key:
                    key_lower = key.lower()

                    # [q] / [m] / [ESC] -> Quitter
                    if key_lower in ("q", "m") or key == "esc":
                        if state["show_help"]:
                            state["show_help"] = False
                        else:
                            break

                    # [t] -> Bascule dynamique du thème
                    elif key_lower == "t":
                        themes_list = get_available_themes()
                        current = get_current_theme()

                        if themes_list:
                            next_idx = (themes_list.index(current) + 1) % len(themes_list) if current in themes_list else 0
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

                    # [a] -> Aide
                    elif key_lower == "a":
                        state["show_help"] = not state["show_help"]

                    # [↑] / [PageUp] -> Remonter dans l'historique (fige le direct)
                    elif key_lower in ("up", "pageup"):
                        if state["scroll_offset"] == 0:
                            state["frozen_snapshot"] = buffer.get_all()
                        max_offset = max(0, len(state["frozen_snapshot"] or []) - 1)
                        step = 1 if key_lower == "up" else visible_rows()
                        state["scroll_offset"] = min(state["scroll_offset"] + step, max_offset)

                    # [↓] / [PageDown] -> Redescendre vers le direct
                    elif key_lower in ("down", "pagedown"):
                        step = 1 if key_lower == "down" else visible_rows()
                        state["scroll_offset"] = max(0, state["scroll_offset"] - step)
                        if state["scroll_offset"] == 0:
                            state["frozen_snapshot"] = None

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

        stop_event.set()
        fetch_thread.join(timeout=1.0)
# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Rendu live des logs en temps réel (menu 5.1 - Live Tail).
# - Affichage dynamique avec Rich Live (rafraîchissement toutes les 2s).
# - Mise en évidence des codes HTTP 4xx (warning) et 5xx (danger).
# - Statistiques en temps réel : total requêtes, erreurs, IPs uniques.
# - Buffer circulaire thread-safe pour éviter les fuites mémoire.
#
# Pourquoi dans interfaces/cli/renderers/ (charte) :
# - Rendu pur, aucune logique métier.
# - Utilise uniquement Rich (Live, Layout, Panel, Table, Text).
# - Utilise theme_registry pour tous les styles (pas de couleurs hardcodées).
# - Consomme un LogEntryProvider injecté (pas d'accès direct aux fichiers).
# - Aucune dépendance vers domain/, application/, ou infrastructure/.
#
# Ce qu'il ne contient PAS :
# ❌ Pas de lecture directe de fichiers de logs.
# ❌ Pas de parsing de logs (c'est le rôle de domain/logs/parser.py).
# ❌ Pas de logique métier (c'est le rôle de application/queries/).
# ❌ Pas de couleurs hardcodées.
# ❌ Pas de dépendance vers infrastructure/.
#
# Points clés :
# - LogEntryProvider : Protocol pour injecter le fournisseur de logs.
# - LogBuffer : Buffer circulaire thread-safe (deque + lock).
# - _render_log_entry() : Rendu d'une entrée avec coloration selon statut HTTP.
# - _render_stats_panel() : Panneau statistiques (total, 4xx, 5xx, IPs uniques).
# - _render_logs_table() : Tableau Rich avec colonnes colorées.
# - render_logs_live() : Fonction principale avec thread de fetch + Live display.
# - Gestion propre de l'arrêt (stop_event + join).
#---------------------------------------------------------------------->
