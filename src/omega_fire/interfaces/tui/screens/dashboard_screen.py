# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 8.1 — Tableau de bord en temps reel. Meme source de donnees que
interfaces/cli/actions.py::action_8_1_live_dashboard (DashboardSnapshotProvider
+ collect_os_stats()), mais rafraichissement natif Textual (Screen.set_interval,
2s) au lieu du thread+Live bricole a la main de interfaces/cli/renderers/
dashboard.py. Les 12 conteneurs sont portes ligne a ligne depuis les fonctions
_render_*_box de ce meme fichier (contenu/donnees identiques), en remplacant
theme_registry.get_style(...) par la palette d'extension omega-fire
(theme_extensions.py, Phase 0) resolue via App.get_css_variables() — c'est
l'ecran qui consomme le plus cette palette (statuts de capacite + identite de
backend), donc son test le plus complet. Le cadre de chaque conteneur est un
Static borde en CSS (`.omega-dash-box`) avec `border_title`, plutot qu'un
Rich Panel : meme convention que le reste de interfaces/tui/ (bordure = CSS,
contenu = Rich seulement pour le texte colore, jamais empiler les deux
mecanismes de bordure)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Static

from omega_fire.application.queries.dashboard_snapshot import DashboardSnapshotProvider
from omega_fire.infrastructure.logging.stats.log_aggregator import LogAggregator
from omega_fire.interfaces.cli.renderers.dashboard import (
    _bytes_to_human,
    _get_capabilities_state,
    _render_progress_bar,
    collect_os_stats,
)
from omega_fire.interfaces.tui.screens._base import OmegaScreen

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ACTION_TITLE = "8.1 Tableau de bord en temps reel"
_REFRESH_SECONDS = 2.0
_SERVICES_DISPLAY_BUDGET = 20

_CATEGORY_LABELS: dict[str, str] = {
    "backends": "Backends",
    "system_services": "Systeme",
    "servers": "Serveurs",
    "bureau_distant": "Bureau",
    "security_network": "Securite Reseau",
}


class DashboardScreen(OmegaScreen):
    """8.1 — 12 conteneurs (4 colonnes) rafraichis toutes les 2s."""

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container
        self._provider: DashboardSnapshotProvider | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="dashboard-body"):
            with Vertical(id="col-services", classes="dash-col"):
                yield Static(id="box-services", classes="omega-dash-box")
            with Vertical(id="col-system", classes="dash-col"):
                yield Static(id="box-system", classes="omega-dash-box dash-box-tall")
                yield Static(id="box-counters", classes="omega-dash-box")
                yield Static(id="box-network", classes="omega-dash-box")
                yield Static(id="box-uptime", classes="omega-dash-box dash-box-short")
            with Vertical(id="col-firewall", classes="dash-col"):
                yield Static(id="box-policy-sync", classes="omega-dash-box")
                yield Static(id="box-bans-alerts", classes="omega-dash-box")
                yield Static(id="box-top-attackers", classes="omega-dash-box")
                yield Static(id="box-recent-actions", classes="omega-dash-box")
            with Vertical(id="col-monitoring", classes="dash-col"):
                yield Static(id="box-firewall-metrics", classes="omega-dash-box")
                yield Static(id="box-advanced-network", classes="omega-dash-box")
                yield Static(id="box-maintenance", classes="omega-dash-box")
        yield Footer()

    def on_mount(self) -> None:
        titles = {
            "box-services": "Services",
            "box-system": "Systeme",
            "box-counters": "Compteurs Temps Reel",
            "box-network": "Reseau & Firewall",
            "box-uptime": "Disponibilite",
            "box-policy-sync": "Politique & Synchronisation",
            "box-bans-alerts": "Bans & Alertes Recentes",
            "box-top-attackers": "Top IPs Attaquantes",
            "box-recent-actions": "Dernieres Actions",
            "box-firewall-metrics": "Metriques Performance Firewall",
            "box-advanced-network": "Reseau Avance",
            "box-maintenance": "Maintenance & Sante",
        }
        for widget_id, title in titles.items():
            self.query_one(f"#{widget_id}", Static).border_title = title

        try:
            self._provider = DashboardSnapshotProvider(
                monitoring_port=self._safe(self._container.get_monitoring_port),
                audit_port=self._safe(self._container.get_audit_port),
                rule_repository=getattr(self._container, "rule_repository", None),
                log_aggregator=LogAggregator(),
                ban_repository=getattr(self._container, "ban_repository", None),
                fail2ban_port=self._safe(self._container.get_fail2ban_port),
                firewall_ports={
                    backend: self._safe(lambda b=backend: self._container.get_firewall_port(b))
                    for backend in ("nftables", "iptables", "ip6tables")
                },
                capability_registry=getattr(self._container, "capability_registry", None),
            )
        except Exception:
            self._provider = None

        self._refresh()
        self.set_interval(_REFRESH_SECONDS, self._refresh)

    @staticmethod
    def _safe(factory):
        try:
            return factory()
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Rafraichissement
    # ------------------------------------------------------------------
    def _colors(self) -> dict[str, str]:
        v = self.app.get_css_variables()
        return {
            "main": v.get("foreground", ""),
            "danger": v.get("error", ""),
            "warning": v.get("warning", ""),
            "info": v.get("secondary", ""),
            "heading": f"bold {v.get('primary', '')}".strip(),
            "available": v.get("status-available", ""),
            "degraded": v.get("status-degraded", ""),
            "missing": v.get("status-missing", ""),
            "disqualified": v.get("status-disqualified", ""),
        }

    def _build_stats(self) -> dict:
        stats = dict(collect_os_stats())
        if self._provider is None:
            return stats
        try:
            snapshot = self._provider.get_snapshot()
        except Exception:
            return stats
        stats.update({
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
        })
        return stats

    def _refresh(self) -> None:
        # _build_stats() collecte os/psutil + le lot "lent" du provider
        # (nftables/iptables/fail2ban) — execute dans un thread (run_blocking,
        # voir _base.py) : en synchrone ici, chaque tick de set_interval (2s)
        # gelerait TOUTE l'app le temps de la collecte, ce qui rendait le
        # dashboard non fluide plutot que "live" (retour utilisateur reel).
        self.run_blocking(self._build_stats, self._apply_stats, busy_message=None)

    def _apply_stats(self, stats: dict) -> None:
        colors = self._colors()

        self.query_one("#box-services", Static).update(self._panel_services(colors))
        self.query_one("#box-system", Static).update(self._panel_system(colors, stats))
        self.query_one("#box-counters", Static).update(self._panel_counters(colors, stats))
        self.query_one("#box-network", Static).update(self._panel_network(colors, stats))
        self.query_one("#box-uptime", Static).update(self._panel_uptime(colors, stats))
        self.query_one("#box-policy-sync", Static).update(self._panel_policy_sync(colors, stats))
        self.query_one("#box-bans-alerts", Static).update(self._panel_bans_alerts(colors, stats))
        self.query_one("#box-top-attackers", Static).update(self._panel_top_attackers(colors, stats))
        self.query_one("#box-recent-actions", Static).update(self._panel_recent_actions(colors, stats))
        self.query_one("#box-firewall-metrics", Static).update(self._panel_firewall_metrics(colors, stats))
        self.query_one("#box-advanced-network", Static).update(self._panel_advanced_network(colors, stats))
        self.query_one("#box-maintenance", Static).update(self._panel_maintenance(colors, stats))

    # ------------------------------------------------------------------
    # Conteneur 1 : Services (registre des capacites)
    # ------------------------------------------------------------------
    def _panel_services(self, colors: dict) -> Text:
        registry = getattr(self._container, "capability_registry", None)
        if registry is None:
            return Text("Registre des capacites indisponible", style="dim")

        capabilities_state = _get_capabilities_state(registry)
        categories = list(capabilities_state.keys())
        if not categories:
            return Text("Aucune capacite detectee", style="dim")

        total_services = sum(len(capabilities_state[cat]) for cat in categories)
        overflow_total = max(0, total_services - _SERVICES_DISPLAY_BUDGET)
        display_limits = {cat: len(capabilities_state[cat]) for cat in categories}
        remaining_to_cut = overflow_total
        while remaining_to_cut > 0:
            largest_cat = max(display_limits, key=lambda c: display_limits[c])
            if display_limits[largest_cat] <= 1:
                break
            display_limits[largest_cat] -= 1
            remaining_to_cut -= 1

        content = Text()
        for cat_key in categories:
            services = capabilities_state[cat_key]
            label = _CATEGORY_LABELS.get(cat_key, cat_key)
            content.append(f"── {label} ──\n", style="dim")

            limit = display_limits[cat_key]
            visible_services = services[:limit]
            overflow_count = len(services) - len(visible_services)

            for svc in visible_services:
                status = svc["status"]
                if status == "active":
                    symbol, style = "✔", colors["available"]
                elif status in ("inactive", "degraded"):
                    symbol, style = "~", colors["degraded"]
                else:
                    symbol, style = "✗", colors["missing"]
                content.append(f"  {svc['name']:<15}", style=colors["main"])
                content.append(f"{symbol}\n", style=style)

            if overflow_count > 0:
                content.append(f"  … +{overflow_count} autre(s) (voir 1.1)\n", style="dim")

        return content

    # ------------------------------------------------------------------
    # Conteneur 2 : Systeme
    # ------------------------------------------------------------------
    def _panel_system(self, colors: dict, stats: dict) -> Text:
        content = Text()
        content.append(f"  🗲 CPU : {_render_progress_bar(stats['cpu'])}\n", style=colors["main"])
        if stats.get("temps"):
            temp_str = " / ".join(f"{v:.0f}°C" for v in list(stats["temps"].values())[:3])
            content.append(f"       Temp: {temp_str}\n", style=colors["main"])
        if stats.get("fans"):
            fan_str = " / ".join(f"{v:.0f} RPM" for v in list(stats["fans"].values())[:2])
            content.append(f"       Fans: {fan_str}\n", style=colors["main"])

        content.append("\n")
        content.append(f"  🖤 RAM : {_render_progress_bar(stats['mem_percent'])}\n", style=colors["main"])
        content.append(
            f"       ({_bytes_to_human(stats['mem_used'])} / {_bytes_to_human(stats['mem_total'])})\n",
            style="dim",
        )

        content.append("\n")
        content.append(f"  💿 Disk: {_render_progress_bar(stats['disk_percent'])}\n", style=colors["main"])
        content.append(
            f"       ({_bytes_to_human(stats['disk_used'])} / {_bytes_to_human(stats['disk_total'])})\n",
            style="dim",
        )

        content.append("\n")
        content.append(
            f"  🗘 Swap: {stats['swap_percent']:5.1f}% "
            f"({_bytes_to_human(stats['swap_used'])} / {_bytes_to_human(stats['swap_total'])})\n",
            style=colors["main"],
        )

        content.append("\n")
        content.append(
            f"  ⚖ Load: {stats['load_1']:.2f} {stats['load_5']:.2f} {stats['load_15']:.2f}\n",
            style=colors["main"],
        )

        content.append("\n")
        content.append(f"  ⚙ Processus: {stats['num_processes']}", style=colors["main"])
        return content

    # ------------------------------------------------------------------
    # Conteneur 3 : Compteurs temps reel
    # ------------------------------------------------------------------
    def _panel_counters(self, colors: dict, stats: dict) -> Text:
        banned = stats.get("banned_count", 0)
        rules = stats.get("rules_count", 0)
        jails = stats.get("jails_count", 0)
        alerts = stats.get("active_alerts", 0)

        content = Text()
        content.append(f"  󰦞 IPs bannies   : {banned:<5}\n", style=colors["danger"])
        content.append(f"  󱁝 Regles actives: {rules:<5}\n", style=colors["main"])
        content.append(f"  󰦝 Jails actifs  : {jails:<5}\n", style=colors["warning"])
        if alerts > 0:
            content.append(f"  ⚠ Alertes       : {alerts:<5}\n", style=colors["danger"])
        return content

    # ------------------------------------------------------------------
    # Conteneur 4 : Reseau & Firewall
    # ------------------------------------------------------------------
    def _panel_network(self, colors: dict, stats: dict) -> Text:
        content = Text()
        content.append(f"  TCP Connexions TCP (OS) : {stats.get('tcp_established', 0)}\n", style=colors["main"])

        conntrack_count = stats.get("conntrack_count", "N/A")
        dropped = stats.get("dropped_packets", 0)
        content.append(f"  🛡 Sessions Conntrack  : {conntrack_count}\n", style=colors["info"])
        if dropped:
            content.append(f"       Paquets dropes  : {dropped}\n", style=colors["danger"])

        users = stats.get("users", [])
        if users:
            user_names = ", ".join(u.name for u in users[:3])
            content.append(f"  Usr Utilisateurs: {user_names}\n", style=colors["main"])
        else:
            content.append("  Usr Aucun utilisateur connecte\n", style=colors["main"])

        sent = _bytes_to_human(stats.get("net_bytes_sent", 0))
        recv = _bytes_to_human(stats.get("net_bytes_recv", 0))
        content.append(f"  🖧 Reseau: ↓{recv}  ↑{sent}\n", style=colors["main"])
        return content

    # ------------------------------------------------------------------
    # Conteneur 5 : Disponibilite
    # ------------------------------------------------------------------
    def _panel_uptime(self, colors: dict, stats: dict) -> Text:
        uptime_sec = stats.get("uptime", 0)
        days = int(uptime_sec // 86400)
        hours = int((uptime_sec % 86400) // 3600)
        minutes = int((uptime_sec % 3600) // 60)
        return Text(f"  🕒 Uptime: {days}j {hours}h {minutes}m", style=colors["main"])

    # ------------------------------------------------------------------
    # Conteneur 6 : Politique & Synchronisation
    # ------------------------------------------------------------------
    def _panel_policy_sync(self, colors: dict, stats: dict) -> Text:
        policy = stats.get("active_policy", "N/A")
        last_sync = stats.get("last_sync_time", "N/A")
        sync_status = stats.get("last_sync_status", "N/A")

        content = Text()
        content.append("  Politique active : ", style=colors["main"])
        content.append(f"[{policy.upper()}]\n", style=colors["warning"])
        content.append(f"  Derniere sync    : {last_sync}\n", style=colors["main"])
        if sync_status == "success":
            content.append("       Statut          : ✔ Reussie\n", style=colors["available"])
        elif sync_status == "failed":
            content.append("       Statut          : ❌ Echouee\n", style=colors["missing"])
        else:
            content.append(f"       Statut          : {sync_status}\n", style="dim")
        return content

    # ------------------------------------------------------------------
    # Conteneur 7 : Bans & Alertes recentes
    # ------------------------------------------------------------------
    def _panel_bans_alerts(self, colors: dict, stats: dict) -> Text:
        last_ban = stats.get("last_ban", {})
        last_unban = stats.get("last_unban", {})
        active_alerts = stats.get("fail2ban_alerts", [])

        content = Text()
        if last_ban:
            content.append(f"  Dernier ban   : {last_ban.get('ip', 'N/A')}\n", style=colors["danger"])
            content.append(f"       Backend     : {last_ban.get('backend', 'N/A')}\n", style="dim")
            content.append(f"       Timestamp   : {last_ban.get('time', 'N/A')}\n", style="dim")
        else:
            content.append("  Dernier ban   : Aucun\n", style="dim")

        content.append("\n")
        if last_unban:
            content.append(f"  Dernier unban : {last_unban.get('ip', 'N/A')}\n", style=colors["available"])
            content.append(f"       Timestamp   : {last_unban.get('time', 'N/A')}\n", style="dim")

        content.append("\n")
        if active_alerts:
            content.append("  ⚠ Alertes F2B   :\n", style=colors["warning"])
            for alert in active_alerts[:3]:
                content.append(f"       • {alert}\n", style=colors["main"])
        else:
            content.append("  ⚠ Alertes F2B   : Aucune\n", style="dim")
        return content

    # ------------------------------------------------------------------
    # Conteneur 8 : Top IPs attaquantes
    # ------------------------------------------------------------------
    def _panel_top_attackers(self, colors: dict, stats: dict) -> Text:
        top_ips = stats.get("top_attackers", [])
        if not top_ips:
            return Text("  Aucune attaque detectee", style="dim")

        content = Text()
        for i, (ip, count) in enumerate(top_ips[:5], 1):
            style = colors["danger"] if count > 50 else colors["warning"]
            content.append(f"  {i}. {ip:<15} ({count} tentatives)\n", style=style)
        return content

    # ------------------------------------------------------------------
    # Conteneur 9 : Dernieres actions
    # ------------------------------------------------------------------
    def _panel_recent_actions(self, colors: dict, stats: dict) -> Text:
        actions = stats.get("recent_actions", [])
        if not actions:
            return Text("  Aucune action recente", style="dim")

        content = Text()
        for action in actions[:5]:
            timestamp = action.get("time", "")
            desc = action.get("description", "")
            content.append(f"  [{timestamp}] {desc}\n", style=colors["main"])
        return content

    # ------------------------------------------------------------------
    # Conteneur 10 : Metriques performance firewall
    # ------------------------------------------------------------------
    def _panel_firewall_metrics(self, colors: dict, stats: dict) -> Text:
        latency = stats.get("backend_latency", {})
        content = Text()
        content.append("  Latence backends :\n", style=colors["heading"])
        if latency:
            for backend, ms in latency.items():
                content.append(f"       {backend:<12} : {ms} ms\n", style=colors["main"])
        else:
            content.append("       (aucune mesure)\n", style="dim")
        return content

    # ------------------------------------------------------------------
    # Conteneur 11 : Reseau avance
    # ------------------------------------------------------------------
    def _panel_advanced_network(self, colors: dict, stats: dict) -> Text:
        outbound_ip = stats.get("outbound_ip", "N/A")
        interfaces = stats.get("interfaces", [])
        gateway = stats.get("gateway", "N/A")
        dns = stats.get("dns", [])

        content = Text()
        content.append(f"  🌍 IP reseau (sortante) : {outbound_ip}\n", style=colors["info"])
        content.append("\n  Interfaces   :\n", style=colors["heading"])
        for iface in interfaces[:4]:
            content.append(f"       {iface['name']:<10} : {iface['ip']}\n", style=colors["main"])
        content.append(f"\n  🖥 Passerelle   : {gateway}\n", style=colors["main"])
        content.append("  🔍 DNS          : ", style=colors["main"])
        if dns:
            content.append(", ".join(dns[:3]) + "\n", style=colors["main"])
        else:
            content.append("Non configure\n", style="dim")
        return content

    # ------------------------------------------------------------------
    # Conteneur 12 : Maintenance & Sante
    # ------------------------------------------------------------------
    def _panel_maintenance(self, colors: dict, stats: dict) -> Text:
        last_backup = stats.get("last_backup", {})
        config_integrity = stats.get("config_integrity", "N/A")
        version = stats.get("version", "N/A")
        registry_update = stats.get("registry_update", "N/A")

        content = Text()
        if last_backup:
            content.append("  🗜 Dernier backup :\n", style=colors["heading"])
            content.append(f"       Date : {last_backup.get('date', 'N/A')}\n", style=colors["main"])
            status = last_backup.get("status", "N/A")
            if status == "ok":
                content.append("       Statut: ✔ OK\n", style=colors["available"])
            elif status == "late":
                content.append("       Statut: ⚠ En retard\n", style=colors["warning"])
            else:
                content.append("       Statut: ❌ Echoue\n", style=colors["missing"])
        else:
            content.append("  🗜 Dernier backup : Aucun\n", style="dim")

        content.append("\n")
        content.append("  Integrite config : ", style=colors["main"])
        if config_integrity == "ok":
            content.append("✔ OK\n", style=colors["available"])
        elif config_integrity == "error":
            content.append("❌ Erreur\n", style=colors["missing"])
        else:
            content.append(f"{config_integrity}\n", style="dim")

        content.append(f"\n  📦 Version Omega-Fire : {version}\n", style=colors["info"])
        content.append(f"       MAJ registre     : {registry_update}\n", style="dim")
        return content
