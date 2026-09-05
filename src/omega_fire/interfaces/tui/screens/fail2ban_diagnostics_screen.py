# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 4.9 — Verification et diagnostic complet de la configuration
Fail2ban. Ecran d'affichage seul (aucune saisie utilisateur, exactement
comme interfaces/cli/actions.py::action_4_9_verify_config, un rapport
instantane) — collecte (subprocess fail2ban-client --version, lecture de
/etc/fail2ban/jail.d/*.conf|.local, Fail2banPort.verify_config()/
is_available()) portee ligne a ligne, memes appels systeme, seule la
presentation change. Bouton Rafraichir ajoute pour re-scanner sans
rouvrir l'ecran (le CLI, lui, affiche une seule fois puis revient)."""
from __future__ import annotations

import os
import re
import subprocess
from typing import TYPE_CHECKING

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, DataTable, Footer, Header, Static

from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.support.action_audit import log_action_result

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ACTION_TITLE = "4.9 Verification de la configuration Fail2ban"
_JAIL_D_DIR = "/etc/fail2ban/jail.d"
_SOCKET_PATH = "/var/run/fail2ban/fail2ban.sock"
_SQLITE_DB_PATH = "/var/lib/fail2ban/fail2ban.sqlite3"


class Fail2banDiagnosticsScreen(OmegaScreen):
    """4.9 — rapport de sante Fail2ban : service, syntaxe, jails, filtres, logs."""

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="omega-panel"):
            yield Static("DIAGNOSTIC & CONFIGURATION FAIL2BAN", classes="omega-title")
            yield DataTable(id="system-table")
            yield DataTable(id="jails-table")
            yield Static(id="box-summary", classes="omega-dash-box")
            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button("Rafraichir", id="refresh", variant="primary")
                with Container(classes="omega-btn-frame"):
                    yield Button("Retour", id="back")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#system-table", DataTable).add_columns("Composant / Indicateur", "Valeur / Etat")
        self.query_one("#jails-table", DataTable).add_columns(
            "Nom Jail", "Statut", "IPs Ban", "Filtre Source", "Log Surveille", "Regles (r/find/ban)"
        )
        self._refresh()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss()
            return
        if event.button.id == "refresh":
            self._refresh()

    def _colors(self) -> dict[str, str]:
        v = self.app.get_css_variables()
        return {
            "main": v.get("foreground", ""),
            "danger": v.get("error", ""),
            "warning": v.get("warning", ""),
            "available": v.get("status-available", ""),
            "heading": f"bold {v.get('primary', '')}".strip(),
        }

    def _refresh(self) -> None:
        colors = self._colors()

        fail2ban_port = None
        try:
            fail2ban_port = self._container.get_fail2ban_port()
        except Exception:
            pass

        # --- 1. Inspection systeme & demon ---
        f2b_version = "Inconnue"
        try:
            v_res = subprocess.run(["fail2ban-client", "--version"], capture_output=True, text=True)
            if v_res.returncode == 0:
                v_match = re.search(r'v?(\d+\.\d+\.\d+)', v_res.stdout)
                f2b_version = v_match.group(1) if v_match else v_res.stdout.strip().splitlines()[0]
        except Exception:
            pass

        socket_ok = os.path.exists(_SOCKET_PATH)
        sqlite_size = "Absent"
        if os.path.exists(_SQLITE_DB_PATH):
            try:
                sqlite_size = f"{os.path.getsize(_SQLITE_DB_PATH) / (1024 * 1024):.2f} MB"
            except Exception:
                sqlite_size = "Present"

        service_running = False
        if fail2ban_port is not None and hasattr(fail2ban_port, "is_available"):
            try:
                service_running = fail2ban_port.is_available()
            except Exception:
                service_running = False

        # --- 2. Audit de la syntaxe configuration ---
        syntax_ok = False
        syntax_output = "Port Fail2banPort non disponible."
        if fail2ban_port is not None and hasattr(fail2ban_port, "verify_config"):
            try:
                syntax_ok, errors = fail2ban_port.verify_config()
                syntax_output = "OK (Aucune erreur de syntaxe detectee)" if syntax_ok else ("\n".join(errors) or "Erreur de configuration")
            except Exception as e:
                syntax_output = f"Impossible de tester la syntaxe : {e}"

        # --- 3. Extraction et diagnostic des jails ---
        active_jails_data: dict[str, dict] = {}
        if service_running:
            try:
                from omega_fire.application.queries.jail_status import get_jail_status
                status_result = get_jail_status(fail2ban_port=fail2ban_port)
                active_jails_data = {j.name: {"banned": j.banned_count} for j in status_result.jails}
            except Exception:
                pass

        jail_files_info: list[dict] = []
        if os.path.exists(_JAIL_D_DIR):
            for fname in sorted(os.listdir(_JAIL_D_DIR)):
                if not (fname.endswith(".conf") or fname.endswith(".local")):
                    continue
                fpath = os.path.join(_JAIL_D_DIR, fname)
                j_name_from_file = fname.rsplit(".", 1)[0]
                filter_found, logpath_found = "Inconnu", "Inconnu"
                maxretry_found, findtime_found, bantime_found = "-", "-", "-"

                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        content = f.read()
                        sec_match = re.search(r'\[([^\]]+)\]', content)
                        if sec_match and sec_match.group(1) not in ("DEFAULT", "INCLUDES"):
                            j_name_from_file = sec_match.group(1).strip()
                        if m := re.search(r'^\s*filter\s*=\s*(.+)$', content, re.MULTILINE):
                            filter_found = m.group(1).strip()
                        if m := re.search(r'^\s*logpath\s*=\s*(.+)$', content, re.MULTILINE):
                            logpath_found = m.group(1).strip()
                        if m := re.search(r'^\s*maxretry\s*=\s*(.+)$', content, re.MULTILINE):
                            maxretry_found = m.group(1).strip()
                        if m := re.search(r'^\s*findtime\s*=\s*(.+)$', content, re.MULTILINE):
                            findtime_found = m.group(1).strip()
                        if m := re.search(r'^\s*bantime\s*=\s*(.+)$', content, re.MULTILINE):
                            bantime_found = m.group(1).strip()
                except Exception:
                    pass

                filter_exists = False
                if filter_found != "Inconnu":
                    filter_exists = (
                        os.path.exists(f"/etc/fail2ban/filter.d/{filter_found}.conf")
                        or os.path.exists(f"/etc/fail2ban/filter.d/{filter_found}.local")
                    )
                log_exists = os.path.exists(logpath_found) if logpath_found != "Inconnu" else False
                is_active = j_name_from_file in active_jails_data

                jail_files_info.append({
                    "name": j_name_from_file, "active": is_active,
                    "banned": active_jails_data.get(j_name_from_file, {}).get("banned", 0),
                    "filter": filter_found, "filter_ok": filter_exists,
                    "logpath": logpath_found, "log_ok": log_exists,
                    "params": f"{maxretry_found} r / {findtime_found} / {bantime_found}",
                })

        # --- Rendu ---
        sys_table = self.query_one("#system-table", DataTable)
        sys_table.clear()
        sys_table.add_row("Version de Fail2ban", f2b_version)
        sys_table.add_row("Statut du Demon", Text("Actif (En execution)", style=colors["available"]) if service_running else Text("Inactif / Deconnecte", style=colors["danger"]))
        sys_table.add_row("Socket Unix (/var/run/fail2ban/)", Text("Accessible", style=colors["available"]) if socket_ok else Text("Inaccessible / Absent", style=colors["danger"]))
        sys_table.add_row("Base SQLite (/var/lib/fail2ban/)", sqlite_size)
        sys_table.add_row("Test de syntaxe global (-t)", Text("Valide", style=colors["available"]) if syntax_ok else Text("Erreur detectee", style=colors["danger"]))

        jails_table = self.query_one("#jails-table", DataTable)
        jails_table.clear()
        total_banned_global = 0
        if jail_files_info:
            for item in jail_files_info:
                st = Text("Actif", style=colors["available"]) if item["active"] else Text("Inactif", style="dim")
                ban_str = str(item["banned"]) if item["active"] else "-"
                if item["active"]:
                    total_banned_global += item["banned"]
                f_str = Text(item["filter"] + (" (OK)" if item["filter_ok"] else " (Absent)"),
                             style=colors["main"] if item["filter_ok"] else colors["warning"])
                l_str = Text(item["logpath"] + (" (OK)" if item["log_ok"] else " (Introuvable)"),
                             style=colors["main"] if item["log_ok"] else colors["warning"])
                jails_table.add_row(item["name"], st, ban_str, f_str, l_str, item["params"])
        else:
            jails_table.add_row("(Aucun)", "Inactif", "0", "-", "-", "-")

        content = Text()
        content.append("Bilan du Diagnostic de Sante\n\n", style=colors["heading"])
        if service_running:
            content.append("✔ Le service Fail2ban est actif et repond correctement au socket.\n", style=colors["available"])
        else:
            content.append("❌ Le service Fail2ban ne repond pas. Verifiez s'il est demarre.\n", style=colors["danger"])

        if syntax_ok:
            content.append("✔ La verification de syntaxe 'fail2ban-client -t' a reussi.\n", style=colors["available"])
        else:
            content.append(f"❌ Erreur de syntaxe dans la configuration : {syntax_output}\n", style=colors["danger"])

        missing_filters = {i["filter"] for i in jail_files_info if not i["filter_ok"] and i["filter"] != "Inconnu"}
        if missing_filters:
            content.append(f"⚠ Certains filtres sont introuvables dans filter.d : {', '.join(missing_filters)}\n", style=colors["warning"])
        else:
            content.append("✔ Tous les filtres declares sont bien presents dans /etc/fail2ban/filter.d/.\n", style=colors["available"])

        missing_logs = {i["logpath"] for i in jail_files_info if not i["log_ok"] and i["logpath"] != "Inconnu"}
        if missing_logs:
            content.append(f"⚠ Certains journaux surveilles n'existent pas sur le disque : {', '.join(missing_logs)}\n", style=colors["warning"])
        else:
            content.append("✔ Tous les fichiers journaux cibles existent physiquement.\n", style=colors["available"])

        content.append(
            f"\nSynthese globale : {len(jail_files_info)} Jail(s) repertorie(s), "
            f"{len(active_jails_data)} actif(s), {total_banned_global} IP(s) actuellement bannie(s).",
            style=colors["main"],
        )
        self.query_one("#box-summary", Static).update(content)

        log_action_result(self._container, _ACTION_TITLE, status="success")
