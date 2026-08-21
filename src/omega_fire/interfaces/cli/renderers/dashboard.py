# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Dashboard renderer for Omega-Fire CLI.

Provides the general state view (Quick View - Section 9) and global frame container.
Handles dynamic footer rendering based on the current mode (MENU, SUBMENU, INPUT, etc.).

Conforms to Omega-Fire architecture charter:
- Pure rendering logic, no business rules
- Uses theme_registry for all styling (no hardcoded colors)
- Reads capabilities from capability_registry (NO direct system probing)
- Consumes dynamic stats (OS + Firewall/Conntrack) injected from application/queries
- No dependency on domain/, application/, or infrastructure/ implementations
"""
import fcntl
import os
import select
import shutil
import sys
import threading
import time
from typing import Optional, List, Dict, Any

try:
    import termios
    import tty
    HAS_TERMIOS = True
except ImportError:
    HAS_TERMIOS = False

import psutil
from rich.console import Console, RenderableType, Group
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich.layout import Layout
from rich.table import Table

from omega_fire.interfaces.cli.themes.registry import theme_registry
from omega_fire.interfaces.cli.renderers.gauge import gauge_status
from omega_fire.interfaces.cli.renderers.styles import (
    get_terminal_width,
    get_terminal_height,
)
from omega_fire.infrastructure.probe.known_services import KNOWN_SERVICES
# ----------------------------------------------------------------------
# Mapping des capacités du registre vers les catégories d'affichage UI
# ----------------------------------------------------------------------
REFERENCE_CAPABILITIES = {
    "backends": ["nftables", "iptables", "ip6tables", "fail2ban_client"],
    **KNOWN_SERVICES,
}

STATUS_MAPPING = {
    "AVAILABLE": "active",
    "DEGRADED": "inactive",
    "MISSING": "not_installed",
    "DISQUALIFIED": "failed",
}

# ----------------------------------------------------------------------
# Lecture clavier non bloquante (menu 8.1) — même mécanisme que
# renderers/logs_live.py (5.1) et views/log_stats_view.py (5.8), copié
# ici plutôt que factorisé : aucun module partagé n'existe encore pour
# ce primitif bas niveau, et en créer un maintenant serait une
# abstraction non demandée pour ce chantier.
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

# ----------------------------------------------------------------------
# Frame modes for dynamic footer
# ----------------------------------------------------------------------
class FrameMode:
    MENU = "menu"
    SUBMENU = "submenu"
    INPUT = "input"
    CONFIRM = "confirm"
    LIST = "list"

# ----------------------------------------------------------------------
# Capability detection helpers
# ----------------------------------------------------------------------
def _get_capabilities_state(capability_registry: Any) -> Dict[str, List[Dict[str, str]]]:
    result: Dict[str, List[Dict[str, str]]] = {}

    for category, cap_ids in REFERENCE_CAPABILITIES.items():
        detected = []
        for cap_id in cap_ids:
            try:
                cap = capability_registry.get(cap_id)
                if cap and cap.status.name != "MISSING":
                    ui_status = STATUS_MAPPING.get(cap.status.name, "not_installed")
                    detected.append({
                        "name": cap_id,
                        "status": ui_status,
                        "reason": getattr(cap, "reason", "")
                    })
            except Exception:
                pass
        
        if detected:
            result[category] = detected

    return result

def _render_single_service(service: Dict[str, str], use_emoji: bool = True) -> Text:
    name = service["name"]
    status = service["status"]

    if status == "active":
        symbol = "✔ " if use_emoji else "[+]"
        style = theme_registry.get_style("status.available")
    elif status == "inactive" or status == "degraded":
        symbol = "~" if use_emoji else "[~]"
        style = theme_registry.get_style("status.degraded")
    else:
        symbol = "✗" if use_emoji else "[-]"
        style = theme_registry.get_style("status.missing")

    text = Text()
    text.append(f"  {name:<15}", style=theme_registry.get_style("text.main"))
    text.append(symbol, style=style)
    return text

# ----------------------------------------------------------------------
# System stats collection (OS level via psutil)
# ----------------------------------------------------------------------
def collect_os_stats() -> dict:
    cpu = psutil.cpu_percent(interval=0)
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    load = psutil.getloadavg()
    pids = len(psutil.pids())
    boot = psutil.boot_time()
    uptime = time.time() - boot

    temps = {}
    try:
        sensors = psutil.sensors_temperatures()
        if sensors:
            for name, entries in sensors.items():
                for entry in entries:
                    temps[entry.label or name] = entry.current
    except Exception:
        pass

    fans = {}
    try:
        fan_sensors = psutil.sensors_fans()
        if fan_sensors:
            for name, entries in fan_sensors.items():
                for entry in entries:
                    fans[entry.label or name] = entry.current
    except Exception:
        pass

    net_io = psutil.net_io_counters()
    tcp_conns = psutil.net_connections(kind='tcp')
    established = len([c for c in tcp_conns if c.status == 'ESTABLISHED'])
    users = psutil.users()
    disk = psutil.disk_usage('/')

    # Réseau avancé
    outbound_ip = "N/A"
    interfaces = []
    gateway = "N/A"
    dns = []

    # socket.gethostbyname(socket.gethostname()) retombe fréquemment sur
    # 127.0.0.1/127.0.1.1 (résolution locale de /etc/hosts, piège classique
    # Debian/Ubuntu) plutôt que sur une IP réseau utilisable. La technique
    # de connexion UDP factice n'envoie aucun paquet (UDP ne fait pas de
    # handshake) — elle demande juste au noyau quelle IP locale serait
    # utilisée pour joindre cette destination, ce qui fonctionne même hors
    # ligne (le noyau résout la route sans dépendre d'une connectivité
    # réelle) et sans appel réseau externe. C'est l'IP de sortie de la
    # machine (LAN derrière un routeur le cas échéant), pas la véritable
    # IP publique internet — d'où le renommage du libellé affiché.
    try:
        import socket
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            probe.connect(("8.8.8.8", 80))
            outbound_ip = probe.getsockname()[0]
        finally:
            probe.close()
    except Exception:
        pass

    try:
        for iface, addrs in psutil.net_if_addrs().items():
            for addr in addrs:
                if addr.family == socket.AF_INET:
                    interfaces.append({"name": iface, "ip": addr.address})
    except Exception:
        pass

    try:
        from omega_fire.infrastructure.probe.network_probe import get_default_gateway
        detected_gateway = get_default_gateway()
        if detected_gateway:
            gateway = detected_gateway
    except Exception:
        pass

    try:
        with open('/etc/resolv.conf', 'r') as f:
            for line in f:
                if line.startswith('nameserver'):
                    dns.append(line.split()[1])
    except Exception:
        pass

    return {
        "cpu": cpu,
        "mem_total": mem.total,
        "mem_used": mem.used,
        "mem_percent": mem.percent,
        "swap_total": swap.total,
        "swap_used": swap.used,
        "swap_percent": swap.percent,
        "load_1": load[0],
        "load_5": load[1],
        "load_15": load[2],
        "num_processes": pids,
        "temps": temps,
        "fans": fans,
        "uptime": uptime,
        "net_bytes_sent": net_io.bytes_sent,
        "net_bytes_recv": net_io.bytes_recv,
        "net_packets_sent": net_io.packets_sent,
        "net_packets_recv": net_io.packets_recv,
        "tcp_established": established,
        "users": users,
        "disk_total": disk.total,
        "disk_used": disk.used,
        "disk_percent": disk.percent,
        "outbound_ip": outbound_ip,
        "interfaces": interfaces,
        "gateway": gateway,
        "dns": dns,
    }

def _bytes_to_human(num_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if num_bytes < 1024:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} TB"

def _render_progress_bar(percent: float, width: int = 20) -> str:
    filled = int(width * percent / 100)
    empty = width - filled
    return f"[{'█' * filled}{'░' * empty}] {percent:5.1f}%"

# ----------------------------------------------------------------------
# Container 2: System metrics
# ----------------------------------------------------------------------
def _render_system_metrics_box(use_emoji: bool, stats: dict) -> Panel:
    content = Text()
    cpu_icon = "🗲" if use_emoji else "CPU"
    ram_icon = "🖤" if use_emoji else "RAM"
    disk_icon = "💿" if use_emoji else "DSK"
    swap_icon = "🗘" if use_emoji else "SWP"
    load_icon = "⚖" if use_emoji else "Load"
    proc_icon = "⚙" if use_emoji else "Proc"

    cpu_bar = _render_progress_bar(stats['cpu'])
    content.append(f"  {cpu_icon}  CPU : {cpu_bar}\n", style=theme_registry.get_style("text.main"))

    if stats.get("temps"):
        temp_str = " / ".join(f"{v:.0f}°C" for v in list(stats["temps"].values())[:3])
        content.append(f"       Temp: {temp_str}\n", style=theme_registry.get_style("text.main"))
    if stats.get("fans"):
        fan_str = " / ".join(f"{v:.0f} RPM" for v in list(stats["fans"].values())[:2])
        content.append(f"       Fans: {fan_str}\n", style=theme_registry.get_style("text.main"))

    content.append("\n")
    ram_bar = _render_progress_bar(stats['mem_percent'])
    content.append(f"  {ram_icon} RAM : {ram_bar}\n", style=theme_registry.get_style("text.main"))
    content.append(f"       ({_bytes_to_human(stats['mem_used'])} / {_bytes_to_human(stats['mem_total'])})\n",
                   style=theme_registry.get_style("text.muted"))

    content.append("\n")
    disk_bar = _render_progress_bar(stats['disk_percent'])
    content.append(f"  {disk_icon} Disk: {disk_bar}\n", style=theme_registry.get_style("text.main"))
    content.append(f"       ({_bytes_to_human(stats['disk_used'])} / {_bytes_to_human(stats['disk_total'])})\n",
                   style=theme_registry.get_style("text.muted"))

    content.append("\n")
    content.append(f"  {swap_icon} Swap: {stats['swap_percent']:5.1f}% "
                   f"({_bytes_to_human(stats['swap_used'])} / {_bytes_to_human(stats['swap_total'])})\n",
                   style=theme_registry.get_style("text.main"))

    content.append("\n")
    content.append(f"  {load_icon} Load: {stats['load_1']:.2f} {stats['load_5']:.2f} {stats['load_15']:.2f}\n",
                   style=theme_registry.get_style("text.main"))

    content.append("\n")
    content.append(f"  {proc_icon} Processus: {stats['num_processes']}", style=theme_registry.get_style("text.main"))

    return Panel(
        content,
        title="Système",
        title_align="left",
        border_style=theme_registry.get_style("border.default"),
        padding=(0, 1),
    )

# ----------------------------------------------------------------------
# Container 3: Counters
# ----------------------------------------------------------------------
def _render_counters_box(use_emoji: bool, stats: dict) -> Panel:
    banned = stats.get("banned_count", 0)
    rules = stats.get("rules_count", 0)
    jails = stats.get("jails_count", 0)
    alerts = stats.get("active_alerts", 0)
    
    ban_icon = "󰦞" if use_emoji else "BAN"
    rule_icon = "󱁝" if use_emoji else "RUL"
    jail_icon = "󰦝" if use_emoji else "JAIL"
    alert_icon = "⚠" if use_emoji else "ALT"

    content = Text()
    content.append(f"  {ban_icon} IPs bannies   : {banned:<5}\n", style=theme_registry.get_style("text.danger"))
    content.append(f"  {rule_icon} Règles actives: {rules:<5}\n", style=theme_registry.get_style("text.main"))
    content.append(f"  {jail_icon} Jails actifs  : {jails:<5}\n", style=theme_registry.get_style("text.warning"))
    if alerts > 0:
        content.append(f"  {alert_icon} Alertes       : {alerts:<5}\n", style=theme_registry.get_style("text.danger"))

    return Panel(
        content,
        title="Compteurs Temps Réel",
        title_align="left",
        border_style=theme_registry.get_style("border.default"),
        padding=(0, 1),
    )

# ----------------------------------------------------------------------
# Container 4: Network
# ----------------------------------------------------------------------
def _render_network_box(use_emoji: bool, stats: dict) -> Panel:
    content = Text()
    net_icon = "🖧" if use_emoji else "Net"
    tcp_icon = "" if use_emoji else "TCP"
    user_icon = "" if use_emoji else "Usr"
    fw_icon = "🛡" if use_emoji else "FW"

    content.append(f"  {tcp_icon} Connexions TCP (OS) : {stats.get('tcp_established', 0)}\n",
                   style=theme_registry.get_style("text.main"))
    
    conntrack_count = stats.get("conntrack_count", "N/A")
    dropped = stats.get("dropped_packets", 0)
    content.append(f"  {fw_icon} Sessions Conntrack  : {conntrack_count}\n",
                   style=theme_registry.get_style("text.info"))
    if dropped > 0:
        content.append(f"       Paquets dropés  : {dropped}\n", style=theme_registry.get_style("text.danger"))

    users = stats.get("users", [])
    if users:
        user_names = ", ".join(u.name for u in users[:3])
        content.append(f"  {user_icon} Utilisateurs: {user_names}\n", style=theme_registry.get_style("text.main"))
    else:
        content.append(f"  {user_icon} Aucun utilisateur connecté\n", style=theme_registry.get_style("text.main"))

    sent = _bytes_to_human(stats.get("net_bytes_sent", 0))
    recv = _bytes_to_human(stats.get("net_bytes_recv", 0))
    content.append(f"  {net_icon} Réseau: ↓{recv}  ↑{sent}\n",
                   style=theme_registry.get_style("text.main"))

    return Panel(
        content,
        title="Réseau & Firewall",
        title_align="left",
        border_style=theme_registry.get_style("border.default"),
        padding=(0, 1),
    )

# ----------------------------------------------------------------------
# Container 5: Uptime
# ----------------------------------------------------------------------
def _render_uptime_box(use_emoji: bool, stats: dict) -> Panel:
    uptime_sec = stats.get("uptime", 0)
    days = int(uptime_sec // 86400)
    hours = int((uptime_sec % 86400) // 3600)
    minutes = int((uptime_sec % 3600) // 60)
    uptime_str = f"{days}j {hours}h {minutes}m"
    clock_icon = "🕒" if use_emoji else "Up"
    content = Text(f"  {clock_icon} Uptime: {uptime_str}", style=theme_registry.get_style("text.main"))

    return Panel(
        content,
        title="Disponibilité",
        title_align="left",
        border_style=theme_registry.get_style("border.default"),
        padding=(0, 1),
    )

# ----------------------------------------------------------------------
# Container 6: Politique + Sync (Colonne 3)
# ----------------------------------------------------------------------
def _render_policy_sync_box(use_emoji: bool, stats: dict) -> Panel:
    policy = stats.get("active_policy", "N/A")
    last_sync = stats.get("last_sync_time", "N/A")
    sync_status = stats.get("last_sync_status", "N/A")
    
    policy_icon = "󱁞" if use_emoji else "POL"
    sync_icon = "" if use_emoji else "SYN"

    content = Text()
    content.append(f"  {policy_icon} Politique active : ", style=theme_registry.get_style("text.main"))
    content.append(f"[{policy.upper()}]\n", style=theme_registry.get_style("text.warning"))
    
    content.append(f"  {sync_icon} Dernière sync    : {last_sync}\n", style=theme_registry.get_style("text.main"))
    if sync_status == "success":
        content.append(f"       Statut          : ✔ Réussie\n", style=theme_registry.get_style("status.available"))
    elif sync_status == "failed":
        content.append(f"       Statut          : ❌ Échouée\n", style=theme_registry.get_style("status.missing"))
    else:
        content.append(f"       Statut          : {sync_status}\n", style=theme_registry.get_style("text.muted"))

    return Panel(
        content,
        title="Politique & Synchronisation",
        title_align="left",
        border_style=theme_registry.get_style("border.default"),
        padding=(0, 1),
    )

# ----------------------------------------------------------------------
# Container 7: Bans + Alertes (Colonne 3)
# ----------------------------------------------------------------------
def _render_bans_alerts_box(use_emoji: bool, stats: dict) -> Panel:
    last_ban = stats.get("last_ban", {})
    last_unban = stats.get("last_unban", {})
    active_alerts = stats.get("fail2ban_alerts", [])
    
    ban_icon = "󰫜" if use_emoji else "BAN"
    unban_icon = "󰫝" if use_emoji else "UNB"
    alert_icon = "⚠" if use_emoji else "ALT"

    content = Text()
    
    if last_ban:
        content.append(f"  {ban_icon} Dernier ban   : {last_ban.get('ip', 'N/A')}\n",
                      style=theme_registry.get_style("text.danger"))
        content.append(f"       Backend     : {last_ban.get('backend', 'N/A')}\n",
                      style=theme_registry.get_style("text.muted"))
        content.append(f"       Timestamp   : {last_ban.get('time', 'N/A')}\n",
                      style=theme_registry.get_style("text.muted"))
    else:
        content.append(f"  {ban_icon} Dernier ban   : Aucun\n", style=theme_registry.get_style("text.muted"))

    content.append("\n")
    
    if last_unban:
        content.append(f"  {unban_icon} Dernier unban : {last_unban.get('ip', 'N/A')}\n",
                      style=theme_registry.get_style("status.available"))
        content.append(f"       Timestamp   : {last_unban.get('time', 'N/A')}\n",
                      style=theme_registry.get_style("text.muted"))

    content.append("\n")
    
    if active_alerts:
        content.append(f"  {alert_icon} Alertes F2B   :\n", style=theme_registry.get_style("text.warning"))
        for alert in active_alerts[:3]:
            content.append(f"       • {alert}\n", style=theme_registry.get_style("text.main"))
    else:
        content.append(f"  {alert_icon} Alertes F2B   : Aucune\n", style=theme_registry.get_style("text.muted"))

    return Panel(
        content,
        title="Bans & Alertes Récentes",
        title_align="left",
        border_style=theme_registry.get_style("border.default"),
        padding=(0, 1),
    )

# ----------------------------------------------------------------------
# Container 8: Top attaquants (Colonne 3)
# ----------------------------------------------------------------------
def _render_top_attackers_box(use_emoji: bool, stats: dict) -> Panel:
    top_ips = stats.get("top_attackers", [])
    
    if not top_ips:
        content = Text("  Aucune attaque détectée", style=theme_registry.get_style("text.muted"))
    else:
        content = Text()
        attack_icon = "" if use_emoji else "ATK"
        for i, (ip, count) in enumerate(top_ips[:5], 1):
            content.append(f"  {i}. {attack_icon} {ip:<15} ({count} tentatives)\n",
                          style=theme_registry.get_style("text.danger" if count > 50 else "text.warning"))

    return Panel(
        content,
        title="Top IPs Attaquantes",
        title_align="left",
        border_style=theme_registry.get_style("border.default"),
        padding=(0, 1),
    )

# ----------------------------------------------------------------------
# Container 9: Actions récentes (Colonne 3)
# ----------------------------------------------------------------------
def _render_recent_actions_box(use_emoji: bool, stats: dict) -> Panel:
    actions = stats.get("recent_actions", [])
    
    if not actions:
        content = Text("  Aucune action récente", style=theme_registry.get_style("text.muted"))
    else:
        content = Text()
        action_icon = "" if use_emoji else "ACT"
        for action in actions[:5]:
            timestamp = action.get("time", "")
            desc = action.get("description", "")
            content.append(f"  {action_icon} [{timestamp}] {desc}\n",
                          style=theme_registry.get_style("text.main"))

    return Panel(
        content,
        title="Dernières Actions",
        title_align="left",
        border_style=theme_registry.get_style("border.default"),
        padding=(0, 1),
    )

# ----------------------------------------------------------------------
# Container 10: Métriques Performance Firewall (Colonne 4 -)
# ----------------------------------------------------------------------
def _render_firewall_metrics_box(use_emoji: bool, stats: dict) -> Panel:
    latency = stats.get("backend_latency", {})
    ratio = stats.get("drop_accept_ratio", {})
    jail_load = stats.get("jail_load", [])
    
    latency_icon = "🗱" if use_emoji else "LAT"
    ratio_icon = "📊" if use_emoji else "RAT"
    jail_icon = "󰦝" if use_emoji else "JL"

    content = Text()
    
    content.append(f"  {latency_icon} Latence backends :\n", style=theme_registry.get_style("text.heading"))
    for backend, ms in latency.items():
        content.append(f"       {backend:<12} : {ms} ms\n", style=theme_registry.get_style("text.main"))
    
    content.append("\n")
    
    if ratio:
        drop_pct = ratio.get("drop_percent", 0)
        accept_pct = ratio.get("accept_percent", 100)
        content.append(f"  {ratio_icon} Ratio Drop/Accept :\n", style=theme_registry.get_style("text.heading"))
        content.append(f"       Drop   : {drop_pct}%\n", style=theme_registry.get_style("text.danger"))
        content.append(f"       Accept : {accept_pct}%\n", style=theme_registry.get_style("status.available"))
    
    content.append("\n")
    
    if jail_load:
        content.append(f"  {jail_icon} Charge des jails :\n", style=theme_registry.get_style("text.heading"))
        for jail_name, count in jail_load[:3]:
            content.append(f"       {jail_name:<12} : {count} bans\n", style=theme_registry.get_style("text.main"))

    return Panel(
        content,
        title="Métriques Performance Firewall",
        title_align="left",
        border_style=theme_registry.get_style("border.default"),
        padding=(0, 1),
    )

# ----------------------------------------------------------------------
# Container 11: Réseau Avancé (Colonne 4 - NOUVEAU)
# ----------------------------------------------------------------------
def _render_advanced_network_box(use_emoji: bool, stats: dict) -> Panel:
    outbound_ip = stats.get("outbound_ip", "N/A")
    interfaces = stats.get("interfaces", [])
    gateway = stats.get("gateway", "N/A")
    dns = stats.get("dns", [])
    
    ip_icon = "🌍" if use_emoji else "IP"
    iface_icon = "" if use_emoji else "IF"
    gw_icon = "🖥" if use_emoji else "GW"
    dns_icon = "🔍" if use_emoji else "DNS"

    content = Text()
    
    content.append(f"  {ip_icon} IP réseau (sortante) : {outbound_ip}\n", style=theme_registry.get_style("text.info"))
    
    content.append(f"\n  {iface_icon} Interfaces   :\n", style=theme_registry.get_style("text.heading"))
    for iface in interfaces[:4]:
        content.append(f"       {iface['name']:<10} : {iface['ip']}\n", style=theme_registry.get_style("text.main"))
    
    content.append(f"\n  {gw_icon} Passerelle   : {gateway}\n", style=theme_registry.get_style("text.main"))
    
    content.append(f"  {dns_icon} DNS          : ", style=theme_registry.get_style("text.main"))
    if dns:
        content.append(", ".join(dns[:3]) + "\n", style=theme_registry.get_style("text.main"))
    else:
        content.append("Non configuré\n", style=theme_registry.get_style("text.muted"))

    return Panel(
        content,
        title="Réseau Avancé",
        title_align="left",
        border_style=theme_registry.get_style("border.default"),
        padding=(0, 1),
    )

# ----------------------------------------------------------------------
# Container 12: Maintenance & Santé (Colonne 4 - NOUVEAU)
# ----------------------------------------------------------------------
def _render_maintenance_box(use_emoji: bool, stats: dict) -> Panel:
    last_backup = stats.get("last_backup", {})
    config_integrity = stats.get("config_integrity", "N/A")
    plugins = stats.get("plugins", {})
    version = stats.get("version", "N/A")
    registry_update = stats.get("registry_update", "N/A")
    
    backup_icon = "🗜" if use_emoji else "BKP"
    config_icon = "" if use_emoji else "CFG"
    plugin_icon = "" if use_emoji else "PLG"
    version_icon = "📦" if use_emoji else "VER"

    content = Text()
    
    if last_backup:
        content.append(f"  {backup_icon} Dernier backup :\n", style=theme_registry.get_style("text.heading"))
        content.append(f"       Date : {last_backup.get('date', 'N/A')}\n", style=theme_registry.get_style("text.main"))
        content.append(f"       Taille: {last_backup.get('size', 'N/A')}\n", style=theme_registry.get_style("text.main"))
        status = last_backup.get('status', 'N/A')
        if status == "ok":
            content.append(f"       Statut: ✔ OK\n", style=theme_registry.get_style("status.available"))
        elif status == "late":
            content.append(f"       Statut: ⚠ En retard\n", style=theme_registry.get_style("text.warning"))
        else:
            content.append(f"       Statut: ❌ Échoué\n", style=theme_registry.get_style("status.missing"))
    else:
        content.append(f"  {backup_icon} Dernier backup : Aucun\n", style=theme_registry.get_style("text.muted"))
    
    content.append("\n")
    
    content.append(f"  {config_icon} Intégrité config : ", style=theme_registry.get_style("text.main"))
    if config_integrity == "ok":
        content.append("✔ OK\n", style=theme_registry.get_style("status.available"))
    elif config_integrity == "error":
        content.append("❌ Erreur\n", style=theme_registry.get_style("status.missing"))
    else:
        content.append(f"{config_integrity}\n", style=theme_registry.get_style("text.muted"))
    
    content.append("\n")
    
    if plugins:
        active = plugins.get("active", 0)
        errors = plugins.get("errors", 0)
        content.append(f"  {plugin_icon} Plugins chargés : {active} actifs", style=theme_registry.get_style("text.main"))
        if errors > 0:
            content.append(f", {errors} en erreur\n", style=theme_registry.get_style("text.danger"))
        else:
            content.append("\n")
    
    content.append(f"\n  {version_icon} Version Omega-Fire : {version}\n", style=theme_registry.get_style("text.info"))
    content.append(f"       MAJ registre     : {registry_update}\n", style=theme_registry.get_style("text.muted"))

    return Panel(
        content,
        title="Maintenance & Santé",
        title_align="left",
        border_style=theme_registry.get_style("border.default"),
        padding=(0, 1),
    )

# ----------------------------------------------------------------------
# Container 1: Services (Colonne 1 - compact)
# ----------------------------------------------------------------------
SERVICES_DISPLAY_BUDGET = 20  # Nombre total de lignes de service affichables sans troncature


def _build_services_layout(
    capabilities_state: Dict[str, List[Dict[str, str]]],
    use_emoji: bool,
) -> Layout:
    layout = Layout()
    categories = list(capabilities_state.keys())
    if not categories:
        layout.update(Text("Aucune capacité détectée", style=theme_registry.get_style("text.muted")))
        return layout

    total_services = sum(len(capabilities_state[cat]) for cat in categories)
    overflow_total = max(0, total_services - SERVICES_DISPLAY_BUDGET)

    # Répartition de la troncature : on retire l'excédent en priorité
    # aux catégories les plus chargées, jamais aux plus légères.
    display_limits: Dict[str, int] = {cat: len(capabilities_state[cat]) for cat in categories}

    remaining_to_cut = overflow_total
    while remaining_to_cut > 0:
        largest_cat = max(display_limits, key=lambda c: display_limits[c])
        if display_limits[largest_cat] <= 1:
            break
        display_limits[largest_cat] -= 1
        remaining_to_cut -= 1

    content = Text()
    content.append("Services détectés\n", style=theme_registry.get_style("text.heading"))
    content.append("─" * 25 + "\n", style=theme_registry.get_style("border.default"))

    for cat_key in categories:
        services = capabilities_state[cat_key]
        label = {
            "backends": "Backends",
            "system_services": "Système",
            "servers": "Serveurs",
            "bureau_distant": "Bureau",
            "security_network": "Sécurité Réseau",
        }.get(cat_key, cat_key)

        content.append(f"\n── {label} ──\n", style=theme_registry.get_style("text.muted"))

        limit = display_limits[cat_key]
        visible_services = services[:limit]
        overflow_count = len(services) - len(visible_services)

        for svc in visible_services:
            content.append_text(_render_single_service(svc, use_emoji))
            content.append("\n")

        if overflow_count > 0:
            content.append(f"  … +{overflow_count} autre(s) (voir 1.1)\n", style=theme_registry.get_style("text.muted"))

    layout.update(
        Panel(content, title="Services", border_style=theme_registry.get_style("border.default"), padding=(1, 1))
    )

    return layout

# ----------------------------------------------------------------------
# Quick View renderer (Section 9) - 4 colonnes, 12 containers
# ----------------------------------------------------------------------
def render_general_state(
    capability_registry: Any,
    console: Optional[Console] = None,
    wait_for_key: bool = True,
    fw_stats_provider: Optional[Any] = None,
) -> None:
    console = console or Console()
    theme = theme_registry.get_active()
    use_emoji = theme.prefers_emojis

    capabilities_state = _get_capabilities_state(capability_registry)
    state = {"show_help": False}

    def _build_help_legend() -> Panel:
        legend = Text()
        legend.append("=== AIDE TABLEAU DE BORD ===\n\n", style=theme_registry.get_style("text.heading"))
        legend.append("• [q] / [m] / [ESC] : Quitter, retour au menu\n", style=theme_registry.get_style("text.main"))
        legend.append("• [t]               : Basculer vers le thème suivant\n", style=theme_registry.get_style("text.main"))
        legend.append("• [a]               : Masquer cet écran d'aide\n", style=theme_registry.get_style("text.main"))
        legend.append("\nLe tableau de bord se rafraîchit automatiquement toutes les 2 secondes.\n", style=theme_registry.get_style("text.muted"))
        return Panel(
            legend,
            title="Aide & Raccourcis",
            title_align="left",
            border_style=theme_registry.get_style("border.default"),
            padding=(1, 2),
        )

    def build_layout() -> Layout:
        root = Layout()
        root.split_column(
            Layout(name="header", size=3),
            Layout(name="body", ratio=1),
            Layout(name="footer", size=3),
        )

        # Header
        header_texts = []
        shield = "\U0001f6e1 " if use_emoji else ""
        title_line = Text(f"{shield}OMEGA-FIRE v3.0", style=theme_registry.get_style("menu.title"))
        theme_name = theme.display_name
        term_width = get_terminal_width()
        term_height = get_terminal_height()
        title_line.append(f"  |  Theme: {theme_name}  |  ", style=theme_registry.get_style("text.muted"))
        title_line.append(f"Terminal: {term_width}x{term_height}", style=theme_registry.get_style("text.muted"))
        header_texts.append(title_line)

        sep_width = max(40, term_width - 4)
        header_texts.append(Text("─" * sep_width, style=theme_registry.get_style("border.default")))

        section_title = Text(
            ">> ETAT GENERAL" if not use_emoji else "▸ ÉTAT GÉNÉRAL",
            style=theme_registry.get_style("text.heading"),
        )
        header_texts.append(section_title)

        header_group = Group(*header_texts)
        root["header"].update(
            Panel(header_group, border_style=theme_registry.get_style("border.default"), padding=(0, 2))
        )

        # Body - légende d'aide (si activée) ou 4 colonnes normales
        if state["show_help"]:
            root["body"].update(_build_help_legend())
            footer_text = _render_footer_text(FrameMode.MENU, use_emoji)
            root["footer"].update(
                Panel(footer_text, border_style=theme_registry.get_style("border.default"), padding=(0, 2))
            )
            return root

        body = Layout()
        body.split_row(
            Layout(name="services", ratio=1),
            Layout(name="system", ratio=1),
            Layout(name="firewall", ratio=1),
            Layout(name="monitoring", ratio=1),
        )
        
        # Colonne 1 : Services (1 container)
        services_layout = _build_services_layout(capabilities_state, use_emoji)
        body["services"].update(services_layout)

        # Colonne 2 : Système (4 containers)
        system_col = Layout()
        system_col.split_column(
            Layout(name="system_metrics", ratio=2),
            Layout(name="counters", size=5),
            Layout(name="network", ratio=1),
            Layout(name="uptime", size=3),
        )

        # Colonne 3 : Firewall (4 containers)
        firewall_col = Layout()
        firewall_col.split_column(
            Layout(name="policy_sync", size=6),
            Layout(name="bans_alerts", size=8),
            Layout(name="top_attackers", ratio=1),
            Layout(name="recent_actions", ratio=1),
        )

        # Colonne 4 : Monitoring & Santé (3 containers)
        monitoring_col = Layout()
        monitoring_col.split_column(
            Layout(name="firewall_metrics", ratio=1),
            Layout(name="advanced_network", ratio=1),
            Layout(name="maintenance", ratio=1),
        )

        # Stats OS + Firewall
        os_stats = collect_os_stats()
        fw_stats = {}
        if fw_stats_provider:
            try:
                snapshot = fw_stats_provider.get_snapshot()
                fw_stats = {
                    "conntrack_count": snapshot.active_connections,
                    "dropped_packets": snapshot.counters.dropped_packets,
                    "banned_count": getattr(snapshot, "banned_count", 0),
                    "rules_count": getattr(snapshot, "rules_count", 0),
                    "jails_count": getattr(snapshot, "jails_count", 0),
                    "active_alerts": getattr(snapshot, "active_alerts", 0),
                    "top_attackers": getattr(snapshot, "top_attackers", []),
                    "recent_actions": getattr(snapshot, "recent_actions", []),
                    "active_policy": getattr(snapshot, "active_policy", "N/A"),
                    "last_sync_time": getattr(snapshot, "last_sync_time", "N/A"),
                    "last_sync_status": getattr(snapshot, "last_sync_status", "N/A"),
                    "last_ban": getattr(snapshot, "last_ban", {}),
                    "last_unban": getattr(snapshot, "last_unban", {}),
                    "fail2ban_alerts": getattr(snapshot, "fail2ban_alerts", []),
                    "backend_latency": getattr(snapshot, "backend_latency", {}),
                    "drop_accept_ratio": getattr(snapshot, "drop_accept_ratio", {}),
                    "jail_load": getattr(snapshot, "jail_load", []),
                    "last_backup": getattr(snapshot, "last_backup", {}),
                    "config_integrity": getattr(snapshot, "config_integrity", "N/A"),
                    "plugins": getattr(snapshot, "plugins", {}),
                    "version": getattr(snapshot, "version", "N/A"),
                    "registry_update": getattr(snapshot, "registry_update", "N/A"),
                }
            except Exception:
                fw_stats = _default_fw_stats()
        else:
            fw_stats = _default_fw_stats()

        display_stats = {**os_stats, **fw_stats}

        # Colonne 2
        system_col["system_metrics"].update(_render_system_metrics_box(use_emoji, display_stats))
        system_col["counters"].update(_render_counters_box(use_emoji, display_stats))
        system_col["network"].update(_render_network_box(use_emoji, display_stats))
        system_col["uptime"].update(_render_uptime_box(use_emoji, display_stats))
        body["system"].update(system_col)

        # Colonne 3
        firewall_col["policy_sync"].update(_render_policy_sync_box(use_emoji, display_stats))
        firewall_col["bans_alerts"].update(_render_bans_alerts_box(use_emoji, display_stats))
        firewall_col["top_attackers"].update(_render_top_attackers_box(use_emoji, display_stats))
        firewall_col["recent_actions"].update(_render_recent_actions_box(use_emoji, display_stats))
        body["firewall"].update(firewall_col)

        # Colonne 4
        monitoring_col["firewall_metrics"].update(_render_firewall_metrics_box(use_emoji, display_stats))
        monitoring_col["advanced_network"].update(_render_advanced_network_box(use_emoji, display_stats))
        monitoring_col["maintenance"].update(_render_maintenance_box(use_emoji, display_stats))
        body["monitoring"].update(monitoring_col)

        root["body"].update(body)

        # Footer
        footer_text = _render_footer_text(FrameMode.MENU, use_emoji)
        root["footer"].update(
            Panel(footer_text, border_style=theme_registry.get_style("border.default"), padding=(0, 2))
        )

        return root

    console.clear()
    stop_event = threading.Event()
    refresh_thread = None

    # build_layout() collecte les stats OS + firewall/fail2ban en direct
    # (vrais sous-processus) avant le tout premier affichage — sans
    # spinner, l'écran restait noir pendant ce chargement.
    with gauge_status(console, "Chargement du tableau de bord..."):
        initial_layout = build_layout()

    try:
        with Live(initial_layout, console=console, screen=True, refresh_per_second=4) as live:
            def refresh_loop():
                while not stop_event.is_set():
                    live.update(build_layout())
                    stop_event.wait(2)

            refresh_thread = threading.Thread(target=refresh_loop, daemon=True)
            refresh_thread.start()

            if wait_for_key:
                # Footer identique (texte) à celui du 5.1 depuis toujours,
                # mais ici seule la touche Entrée était réellement
                # interceptée — [m]/[t]/[a]/[esc]/[q] étaient des touches
                # mortes. Même boucle de lecture clavier non bloquante que
                # 5.1 (renderers/logs_live.py), pour que chaque touche
                # annoncée fonctionne réellement.
                old_settings = None
                if HAS_TERMIOS and sys.stdin.isatty():
                    try:
                        old_settings = termios.tcgetattr(sys.stdin)
                        tty.setcbreak(sys.stdin.fileno())
                    except Exception:
                        old_settings = None

                try:
                    while not stop_event.is_set():
                        key = _get_key_non_blocking()
                        if key:
                            key_lower = key.lower()

                            if key_lower in ("q", "m") or key == "esc":
                                if state["show_help"]:
                                    state["show_help"] = False
                                    live.update(build_layout())
                                else:
                                    break

                            elif key_lower == "t":
                                themes_list = []
                                try:
                                    if hasattr(theme_registry, "get_available_themes"):
                                        themes_list = list(theme_registry.get_available_themes())
                                    elif hasattr(theme_registry, "_themes"):
                                        themes_list = list(theme_registry._themes.keys())
                                except Exception:
                                    pass

                                if themes_list:
                                    try:
                                        current = theme_registry.get_active().name
                                        next_idx = (themes_list.index(current) + 1) % len(themes_list) if current in themes_list else 0
                                        theme_registry.set_active(themes_list[next_idx], silent=True)
                                    except Exception:
                                        pass
                                live.update(build_layout())

                            elif key_lower == "a":
                                state["show_help"] = not state["show_help"]
                                live.update(build_layout())

                        time.sleep(0.05)
                except (EOFError, KeyboardInterrupt):
                    pass
                finally:
                    if old_settings is not None and HAS_TERMIOS and sys.stdin.isatty():
                        try:
                            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                        except Exception:
                            pass
            else:
                try:
                    while not stop_event.is_set():
                        time.sleep(0.5)
                except KeyboardInterrupt:
                    pass
    finally:
        stop_event.set()
        if refresh_thread and refresh_thread.is_alive():
            refresh_thread.join(timeout=1.0)

def _default_fw_stats() -> dict:
    return {
        "conntrack_count": "N/A", "dropped_packets": 0,
        "banned_count": 0, "rules_count": 0, "jails_count": 0,
        "active_alerts": 0, "top_attackers": [], "recent_actions": [],
        "active_policy": "N/A", "last_sync_time": "N/A", "last_sync_status": "N/A",
        "last_ban": {}, "last_unban": {}, "fail2ban_alerts": [],
        "backend_latency": {}, "drop_accept_ratio": {}, "jail_load": [],
        "last_backup": {}, "config_integrity": "N/A", "plugins": {},
        "version": "N/A", "registry_update": "N/A"
    }

# ----------------------------------------------------------------------
# Footer text generation
# ----------------------------------------------------------------------
def _render_footer_text(mode: str, use_emoji: bool) -> Text:
    def icon(emoji: str, ascii_fallback: str) -> str:
        return emoji if use_emoji else ascii_fallback

    key_s = theme_registry.get_style("footer.key")
    label_s = theme_registry.get_style("footer.label")
    sep_s = theme_registry.get_style("footer.separator")
    ctx_s = theme_registry.get_style("footer.context")
    sep = "  |  "

    footer = Text()
    if mode == FrameMode.MENU:
        footer.append("[m]", style=key_s)
        footer.append("enu  ", style=label_s)
        footer.append("|  ", style=sep_s)
        footer.append("[t]", style=key_s)
        footer.append("heme  ", style=label_s)
        footer.append("|  ", style=sep_s)
        footer.append("[a]", style=key_s)
        footer.append("ide  ", style=label_s)
        footer.append("|  ", style=sep_s)
        footer.append("[esc]", style=key_s)
        footer.append(" Retour  ", style=label_s)
        footer.append("|  ", style=sep_s)
        footer.append("[q]", style=key_s)
        footer.append("uitter", style=label_s)
    elif mode == FrameMode.SUBMENU:
        footer.append(icon("\U0001f4c2", "[>]") + " Sous-menu", style=ctx_s)
        footer.append(sep, style=sep_s)
        footer.append("[t]", style=key_s)
        footer.append("hème  ", style=label_s)
        footer.append("|  ", style=sep_s)
        footer.append("[a]", style=key_s)
        footer.append("ide  ", style=label_s)
        footer.append("|  ", style=sep_s)
        footer.append("[m]", style=key_s)
        footer.append("enu principal  ", style=label_s)
        footer.append("|  ", style=sep_s)
        footer.append("[r]", style=key_s)
        footer.append("etour  ", style=label_s)
        footer.append("|  ", style=sep_s)
        footer.append("[q]", style=key_s)
        footer.append("uitter", style=label_s)
    elif mode == FrameMode.INPUT:
        footer.append(icon("\u270f\ufe0f", "[_]") + " Saisie", style=ctx_s)
        footer.append(sep, style=sep_s)
        footer.append("Enter", style=key_s)
        footer.append(" Valider  ", style=label_s)
        footer.append("|  ", style=sep_s)
        footer.append("Esc", style=key_s)
        footer.append(" Annuler  ", style=label_s)
        footer.append("|  ", style=sep_s)
        footer.append("Tab", style=key_s)
        footer.append(" Champ suivant", style=label_s)
    elif mode == FrameMode.CONFIRM:
        footer.append(icon("\u26a0\ufe0f", "[!]") + " Confirmation", style=ctx_s)
        footer.append(sep, style=sep_s)
        footer.append("[o]", style=key_s)
        footer.append("ui  ", style=label_s)
        footer.append("|  ", style=sep_s)
        footer.append("[n]", style=key_s)
        footer.append("on  ", style=label_s)
        footer.append("|  ", style=sep_s)
        footer.append("Esc", style=key_s)
        footer.append(" Annuler", style=label_s)
    elif mode == FrameMode.LIST:
        footer.append(icon("\U0001f4cb", "[L]") + " Sélection", style=ctx_s)
        footer.append(sep, style=sep_s)
        footer.append("^v", style=key_s)
        footer.append(" Naviguer  ", style=label_s)
        footer.append("|  ", style=sep_s)
        footer.append("Enter", style=key_s)
        footer.append(" Valider  ", style=label_s)
        footer.append("|  ", style=sep_s)
        footer.append("Esc", style=key_s)
        footer.append(" Annuler", style=label_s)

    return footer

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Rendu du tableau de bord général (Quick View) avec 4 colonnes et 12 containers.
# - Colonne 1 : Services (toutes catégories regroupées en 1 container compact).
# - Colonne 2 : Système (CPU/RAM/Disk/Swap/Load, Compteurs, Réseau basique, Uptime).
# - Colonne 3 : Firewall (Politique+Sync, Bans+Alertes, Top attaquants, Actions récentes).
# - Colonne 4 : Monitoring & Santé (Métriques perf, Réseau avancé, Maintenance).
# - Footer dynamique selon le mode actif (MENU, SUBMENU, INPUT, CONFIRM, LIST).
# - Affichage temps réel des métriques système avec barres de progression ASCII.
# - Affichage des métriques Firewall (Conntrack, paquets dropés, bans, règles)
#   via injection de données depuis application/queries (fw_stats_provider).
#
# Pourquoi dans interfaces/cli/renderers/ (charte) :
# - Rendu pur, aucune logique métier ni appel système direct (sauf psutil pour l'OS).
# - Utilise uniquement Rich (Layout, Live, Panel, Text), theme_registry et styles.py.
# - Lit l'état des capacités exclusivement via capability_registry (pas de probe direct).
# - Pas de logique ad-hoc, pas de couleurs hardcodées.
#
# Ce qu'il ne contient PAS :
# ❌ Pas de sondage système direct (service_probe) dans le renderer.
# ❌ Pas de compteurs hardcodés ("42 IPs bannies").
# ❌ Pas de logique métier, d'appels nft/iptables ou de SQL.
# ❌ Pas de dépendance vers domain/, application/, ou infrastructure/ implementations.
#
# Points clés :
# - 12 containers répartis sur 4 colonnes :
#   1. Services (compact, toutes catégories)
# - REFERENCE_CAPABILITIES : fusion de "backends" (fixe) et de
#   infrastructure/probe/known_services.py::KNOWN_SERVICES (source
#   unique partagée avec le scanner, évite toute duplication/dérive).
# - SERVICES_DISPLAY_BUDGET (20) : limite globale d'affichage. Si
#   dépassée, la troncature cible en priorité les catégories les plus
#   chargées, jamais celles avec peu d'entrées.
#   2. Système (métriques OS + compteurs + réseau basique + uptime)
#   3. Firewall (politique, sync, bans, alertes, top attaquants, actions)
#   4. Monitoring & Santé (métriques perf, réseau avancé, maintenance)
# - Barres de progression ASCII pour CPU, RAM, Disk
# - _render_policy_sync_box() : politique active + dernière synchronisation
# - _render_bans_alerts_box() : dernier ban/unban + alertes fail2ban actives
# - _render_firewall_metrics_box() : latence backends, ratio drop/accept, charge jails
# - _render_advanced_network_box() : IP réseau sortante, interfaces, passerelle, DNS
# - _render_maintenance_box() : backup, intégrité config, plugins, version
# - render_general_state() : dashboard réactif avec Live, thread sécurisé (try/finally)
# - _get_key_non_blocking() : lecture clavier non bloquante (même mécanisme
#   que 5.1/renderers/logs_live.py et 5.8/views/log_stats_view.py) — chaque
#   touche du footer ([m]/[t]/[a]/[esc]/[q]) est réellement interceptée,
#   plus une simple attente bloquante sur Entrée.
# - state["show_help"] + [a] : bascule vers une légende de raccourcis en
#   plein écran (remplace temporairement les 4 colonnes), même principe
#   que le 5.1.
# - Footer strictement conforme au modèle : [m]enu | [t]heme | [a]ide | [esc] Retour | [q]uitter
#---------------------------------------------------------------------->
