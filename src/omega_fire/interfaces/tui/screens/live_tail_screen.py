# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 5.1 (alias 8.5) — Visualiser les logs en direct (Live Tail).
Meme logique que interfaces/cli/actions.py::action_5_1_live_tail : selection
d'une source (epingles/historique/saisie manuelle) via ManageLiveTailPinsCommand,
puis lancement d'un tableau de bord temps reel consommant la meme classe
LogProvider (parsing generique JSON/Combined/heuristique, portee ligne a
ligne) et le meme LogBuffer (interfaces/cli/renderers/logs_live.py — classe
publique pure, sans dependance Rich/theme, reutilisee telle quelle). Le
rafraichissement est un Screen.set_interval(2s) natif Textual, remplacant le
thread+Live bricole a la main de logs_live.py::render_logs_live (Phase 4).

Deux etats bascules via `.omega-hidden` (meme patron que les champs
conditionnels des formulaires) : selection de la source, puis suivi live."""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from typing import TYPE_CHECKING

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.timer import Timer
from textual.widgets import Button, DataTable, Footer, Header, Input, Static

from omega_fire.application.commands.manage_live_tail_pins import ManageLiveTailPinsCommand
from omega_fire.infrastructure.config.paths import RUNTIME_DIR
from omega_fire.infrastructure.storage.files.json_store import JsonStore
from omega_fire.interfaces.cli.renderers.logs_live import LogBuffer
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.support.action_audit import log_action_result
from omega_fire.shared.i18n import _

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ACTION_TITLE = "8.5 Visualiser les logs serveurs avec Tail"
_REFRESH_SECONDS = 2.0
_BUFFER_SIZE = 500


class _LogProvider:
    """Portee verbatim depuis action_5_1_live_tail::LogProvider (parsing
    JSON/Combined/heuristique, lecture incrementale tail -f avec detection
    de rotation) — aucune logique metier modifiee, seulement extraite de
    la fonction imbriquee pour etre instanciable depuis cet ecran."""

    def __init__(self, source: str):
        self.source = source
        self._offset = 0
        self._primed = False

    def _parse_generic_line(self, line: str) -> dict | None:
        line_str = line.strip()
        if not line_str:
            return None

        if line_str.startswith("{") and line_str.endswith("}"):
            try:
                data = json.loads(line_str)
                size = (
                    data.get("size")
                    or data.get("bytes_sent")
                    or data.get("response_size")
                    or data.get("body_bytes_sent")
                    or data.get("res", {}).get("size", 0)
                    or 0
                )
                status = data.get("status") or data.get("status_code") or data.get("res", {}).get("status", 200)
                latency = data.get("duration") or data.get("latency") or data.get("response_time", 0)
                if isinstance(latency, float) and latency < 10:
                    latency = int(latency * 1000)

                return {
                    "timestamp": str(data.get("ts") or data.get("time") or data.get("timestamp") or "")[:19],
                    "source_ip": str(data.get("client_ip") or data.get("remote_ip") or data.get("ip") or "127.0.0.1"),
                    "method": str(data.get("method") or data.get("req", {}).get("method") or "GET"),
                    "path": str(data.get("uri") or data.get("path") or data.get("req", {}).get("uri") or "/"),
                    "status_code": int(status),
                    "bytes_sent": int(size) if str(size).isdigit() else 0,
                    "user_agent": str(data.get("user_agent") or "Web"),
                    "response_time_ms": int(latency) if str(latency).isdigit() else 25,
                }
            except Exception:
                pass

        combined_match = re.search(
            r'(?P<ip>\S+)\s+\S+\s+\S+\s+\[(?P<time>[^\]]+)\]\s+"(?P<method>\S+)\s+(?P<path>\S+)[^"]*"\s+(?P<status>\d+)\s+(?P<size>\d+|-)',
            line_str,
        )
        if combined_match:
            raw_size = combined_match.group("size")
            bytes_sent = int(raw_size) if raw_size and raw_size.isdigit() else 0
            tail = line_str[combined_match.end():].strip().split()
            latency = 35
            for token in reversed(tail):
                clean_token = token.strip('"').replace(".", "")
                if clean_token.isdigit() and len(clean_token) <= 6:
                    latency = int(clean_token)
                    break

            return {
                "timestamp": combined_match.group("time"),
                "source_ip": combined_match.group("ip"),
                "method": combined_match.group("method"),
                "path": combined_match.group("path"),
                "status_code": int(combined_match.group("status")),
                "bytes_sent": bytes_sent,
                "user_agent": "Mozilla/5.0",
                "response_time_ms": latency,
            }

        ip_match = re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", line_str)
        status_match = re.search(r'\b(200|201|204|301|302|304|400|401|403|404|500|502|503)\b', line_str)
        method_match = re.search(r'\b(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\b', line_str)

        all_numbers = re.findall(r'\b\d+\b', line_str)
        extracted_bytes = 0
        for num in all_numbers:
            val = int(num)
            if val > 0 and val not in (80, 443, 8080, 8443) and val < 100000000 and val != int(status_match.group(0) if status_match else 0):
                extracted_bytes = val
                break

        return {
            "timestamp": "",
            "source_ip": ip_match.group(0) if ip_match else "N/A",
            "method": method_match.group(0) if method_match else "LOG",
            "path": line_str[:60],
            "status_code": int(status_match.group(0)) if status_match else 200,
            "bytes_sent": extracted_bytes if extracted_bytes > 0 else len(line_str),
            "user_agent": "System",
            "response_time_ms": 15,
        }

    def _read_last_lines(self, path: str, limit: int, chunk_size: int = 65536) -> list[str]:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            file_size = f.tell()
            pos = file_size
            data = b""
            while pos > 0 and data.count(b"\n") <= limit:
                read_size = min(chunk_size, pos)
                pos -= read_size
                f.seek(pos)
                data = f.read(read_size) + data
        text = data.decode("utf-8", errors="ignore")
        lines = text.splitlines()
        if pos > 0 and lines:
            lines = lines[1:]
        return lines[-limit:]

    def get_recent_logs(self, limit: int = 50) -> list[dict]:
        try:
            if self.source.startswith("http://") or self.source.startswith("https://"):
                separator = "&" if "?" in self.source else "?"
                fresh_url = f"{self.source}{separator}_cb={int(time.time() * 1000)}"
                with urllib.request.urlopen(fresh_url, timeout=5) as response:
                    content = response.read().decode("utf-8", errors="ignore")
                    lines = content.splitlines()[-limit:]
            else:
                if not self._primed:
                    lines = self._read_last_lines(self.source, limit)
                    with open(self.source, "rb") as f:
                        f.seek(0, os.SEEK_END)
                        self._offset = f.tell()
                    self._primed = True
                else:
                    with open(self.source, "rb") as f:
                        f.seek(0, os.SEEK_END)
                        current_size = f.tell()
                        if current_size < self._offset:
                            self._offset = 0
                        f.seek(self._offset)
                        new_bytes = f.read()
                        self._offset = f.tell()
                    lines = new_bytes.decode("utf-8", errors="ignore").splitlines()

            parsed_logs = []
            for line in lines:
                parsed = self._parse_generic_line(line)
                if parsed:
                    parsed_logs.append(parsed)
            return parsed_logs
        except Exception as e:
            return [{
                "timestamp": "",
                "source_ip": "ERR",
                "method": "ERR",
                "path": _("Erreur de lecture ({source}) : {e}").format(source=self.source, e=e),
                "status_code": 500,
                "bytes_sent": 0,
                "user_agent": "Système/Erreur",
                "response_time_ms": 0,
            }]


class LiveTailScreen(OmegaScreen):
    """5.1/8.5 — selection de source puis suivi live (tableau + stats)."""

    def __init__(self, *, container: DependencyContainer, source: str | None = None) -> None:
        """source : ouverture directe sur ce log (lecteur Simple de 5.2 Favoris / 5.3 Voir
        les logs) — sans passer par la selection, sans toucher a l'historique de 8.5 ;
        « Arreter / Retour » revient alors a l'ecran appelant."""
        super().__init__()
        self._container = container
        self._direct_source = source
        self._command = ManageLiveTailPinsCommand(JsonStore(RUNTIME_DIR))
        self._display_items: dict[str, dict] = {}
        self._provider: _LogProvider | None = None
        self._buffer: LogBuffer | None = None
        self._timer: Timer | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="setup-panel", classes="omega-panel"):
            yield Static(_("VISUALISER LES LOGS EN DIRECT (LIVE TAIL)"), classes="omega-title")
            yield Static("", id="setup-hint", classes="omega-hint")
            yield DataTable(id="sources-table")
            yield Input(placeholder=_("Nom de l'épingle (uniquement pour 'Épingler')"), id="pin-name-input")
            yield Input(placeholder=_("Chemin du fichier ou URL http(s)://..."), id="source-input")
            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Lancer"), id="launch", variant="primary")
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Épingler"), id="pin")
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Retirer"), id="unpin", variant="error")
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Purger tout"), id="purge", variant="error")
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Retour"), id="back")

        with Vertical(id="live-panel", classes="omega-panel omega-hidden"):
            yield Static("", id="live-title", classes="omega-title")
            with Horizontal(id="live-body"):
                yield Static(id="stats-box", classes="omega-dash-box")
                yield DataTable(id="logs-table")
            with Horizontal(classes="omega-actions"), Container(classes="omega-btn-frame"):
                yield Button(_("Arrêter / Retour"), id="stop")
        yield Footer()

    def on_mount(self) -> None:
        # cursor_type par defaut = "cell" : DataTable.RowHighlighted (ecoute
        # par on_data_table_row_highlighted plus bas) n'est POSTE que si
        # cursor_type == "row" — sans ceci, le curseur bouge visuellement
        # au clic mais l'evenement n'est jamais emis, donc rien ne se
        # peuple jamais (retour utilisateur reel : "bloque sur la premiere
        # ligne, rien a selectionner").
        self.query_one("#sources-table", DataTable).cursor_type = "row"
        self.query_one("#sources-table", DataTable).add_columns(_("Type"), _("Nom"), _("Chemin"))
        self.query_one("#logs-table", DataTable).add_columns(
            _("Heure"), _("IP Source"), _("Type"), _("Méthode"), _("Chemin"), _("Statut"), _("Taille"), _("Latence")
        )
        self._refresh_sources_table()
        if self._direct_source:
            self.query_one("#source-input", Input).value = self._direct_source
            self.call_after_refresh(self._launch)

    def action_back(self) -> None:
        self._stop_live()
        self.dismiss()

    # ------------------------------------------------------------------
    # Panneau de selection de source
    # ------------------------------------------------------------------
    def _refresh_sources_table(self) -> None:
        table = self.query_one("#sources-table", DataTable)
        table.clear()
        self._display_items = {}
        idx = 1

        for name, path in self._command.list_active_pinned().items():
            key = str(idx)
            self._display_items[key] = {"type": "pinned", "name": name, "path": path}
            table.add_row(_("Épingle"), name, path, key=key)
            idx += 1

        for h_path in self._command.list_history()[:5]:
            key = str(idx)
            self._display_items[key] = {"type": "history", "name": _("Historique récent"), "path": h_path}
            table.add_row(_("Historique"), _("Historique récent"), h_path, key=key)
            idx += 1

        hint = self.query_one("#setup-hint", Static)
        if self._display_items:
            hint.update(_("Sélectionnez une ligne, ou saisissez un chemin/URL manuellement."))
            # Le curseur du tableau demarre automatiquement sur la 1ere
            # ligne (deja "en surbrillance") : cliquer PRECISEMENT cette
            # ligne ne declenche aucun RowHighlighted (la coordonnee ne
            # change pas), donc ne peuplait jamais les champs — bug reel
            # ("source invalide" au premier clic sur la 1ere ligne).
            # Synchronisation explicite ici pour rester coherent avec ce
            # que la surbrillance affiche deja.
            first_key = next(iter(self._display_items))
            self._apply_selected_item(self._display_items[first_key])
        else:
            hint.update(_("Aucune source épinglée. Saisissez un chemin/URL manuellement."))

    def _apply_selected_item(self, item: dict) -> None:
        self.query_one("#source-input", Input).value = item["path"]
        self.query_one("#pin-name-input", Input).value = item["name"] if item["type"] == "pinned" else ""

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        # Ouverture directe (5.2 / 5.3) : la surbrillance automatique de la 1re epingle
        # arrive APRES le montage et remplacait le log choisi (retour utilisateur 2026-10-28 :
        # log omega-serv choisi, /var/log/apache2/access.log ouvert).
        if event.data_table.id != "sources-table" or self._direct_source:
            return
        item = self._display_items.get(str(event.row_key.value))
        if item is None:
            return
        self._apply_selected_item(item)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id in ("back", "stop"):
            self.action_back()
            return
        if button_id == "launch":
            self._launch()
            return
        if button_id == "pin":
            self._pin()
            return
        if button_id == "unpin":
            self._unpin()
            return
        if button_id == "purge":
            self._purge()

    def _pin(self) -> None:
        name = self.query_one("#pin-name-input", Input).value.strip()
        path = self.query_one("#source-input", Input).value.strip()
        if not name or not path:
            self.app.notify(_("Nom et chemin requis pour épingler."), severity="warning")
            return
        result = self._command.add_pinned(name, path)
        if result.success:
            self.app.notify(result.message)
            self._refresh_sources_table()
        else:
            self.app.notify(result.message, severity="error")

    def _unpin(self) -> None:
        table = self.query_one("#sources-table", DataTable)
        if table.cursor_row is None or table.row_count == 0:
            self.app.notify(_("Aucune ligne sélectionnée."), severity="warning")
            return
        row_key = table.coordinate_to_cell_key((table.cursor_row, 0)).row_key
        item = self._display_items.get(str(row_key.value))
        if item is None:
            self.app.notify(_("Aucune ligne sélectionnée."), severity="warning")
            return
        if item["type"] == "pinned":
            result = self._command.remove_pinned(item["name"])
        else:
            result = self._command.remove_history_entry(item["path"])
        if result.success:
            self.app.notify(result.message)
            self._refresh_sources_table()
        else:
            self.app.notify(result.message, severity="error")

    def _purge(self) -> None:
        self._command.purge_all()
        self.app.notify(_("Historique et épingles purges avec succès."))
        self._refresh_sources_table()

    # ------------------------------------------------------------------
    # Panneau live
    # ------------------------------------------------------------------
    def _launch(self) -> None:
        source = self._direct_source or self.query_one("#source-input", Input).value.strip()
        if not source:
            self.app.notify(_("Source invalide. Saisissez un chemin ou une URL."), severity="warning")
            return

        if not self._direct_source and source not in self._command.list_all_known_paths():
            self._command.record_history(source)

        if self._timer is not None:
            self._timer.stop()

        self._provider = _LogProvider(source)
        self._buffer = LogBuffer(max_size=_BUFFER_SIZE)
        self.query_one("#live-title", Static).update(_("LIVE TAIL — {source}").format(source=source))

        self.query_one("#setup-panel").set_class(True, "omega-hidden")
        self.query_one("#live-panel").set_class(False, "omega-hidden")

        log_action_result(self._container, _ACTION_TITLE, status="success")
        self._poll()
        self._timer = self.set_interval(_REFRESH_SECONDS, self._poll)

    def _stop_live(self) -> None:
        if self._timer is not None:
            self._timer.stop()
            self._timer = None
        self.query_one("#live-panel").set_class(True, "omega-hidden")
        self.query_one("#setup-panel").set_class(False, "omega-hidden")

    def _poll(self) -> None:
        if self._provider is None or self._buffer is None:
            return
        for entry in self._provider.get_recent_logs(limit=_BUFFER_SIZE):
            self._buffer.add(entry)

        variables = self.app.get_css_variables()
        colors = {
            "main": variables.get("foreground", ""),
            "muted": "dim",
            "danger": variables.get("error", ""),
            "warning": variables.get("warning", ""),
            "info": variables.get("secondary", ""),
            "heading": f"bold {variables.get('secondary', '')}".strip(),
            "available": variables.get("status-available", ""),
        }

        self.query_one("#stats-box", Static).update(self._render_stats(colors, self._buffer.get_stats()))
        # Tout le tampon, du plus ancien au plus recent, comme le viewer Simple d'omega-serv (reference,
        # retour utilisateur 2026-11-02) : avant, seules les 30 plus recentes en tete, sans ascenseur.
        self._render_logs_table(colors, list(reversed(self._buffer.get_all())))

    def _render_stats(self, colors: dict, stats: dict) -> Text:
        def _format_bytes(size: float) -> str:
            if size > 1024 * 1024:
                return f"{size / (1024 * 1024):.1f} MB"
            if size > 1024:
                return f"{size / 1024:.1f} KB"
            return f"{int(size)} B"

        content = Text()
        content.append(_("── RENDEMENT ───────────────\n"), style=colors["heading"])
        content.append(_(" ⚡ Débit      : {rps:.1f} req/s\n").format(rps=stats['rps']), style=colors["info"])
        avg_lat = stats["avg_latency"]
        lat_style = colors["available"] if avg_lat < 200 else (colors["warning"] if avg_lat < 500 else colors["danger"])
        content.append(_(" ⏱ Latence moy: {avg_lat:.0f} ms\n\n").format(avg_lat=avg_lat), style=lat_style)

        content.append(_("── BANDE PASSANTE ──────────\n"), style=colors["heading"])
        content.append(_(" 🌐 Débit réseau: {value}/s\n").format(value=_format_bytes(stats['bps'])), style=colors["main"])
        content.append(_(" 📦 Vol. total  : {value}\n").format(value=_format_bytes(stats['bytes_total'])), style=colors["main"])
        content.append(_(" 🗜 Taille moy. : {value}\n\n").format(value=_format_bytes(stats['avg_size'])), style=colors["main"])

        content.append(_("── STATUTS HTTP ────────────\n"), style=colors["heading"])
        content.append(_(" 📊 Total Req.  : {total}\n").format(total=stats['total']), style=colors["main"])
        content.append(_(" √  Succès 2xx  : {success_2xx}\n").format(success_2xx=stats['success_2xx']), style=colors["available"])
        content.append(_(" ↔  Redir. 3xx  : {redirect_3xx}\n").format(redirect_3xx=stats['redirect_3xx']), style=colors["info"])
        content.append(_(" ⚠  Erreurs 4xx : {errors_4xx}\n").format(errors_4xx=stats['errors_4xx']), style=colors["warning"])
        content.append(_(" ❌ Erreurs 5xx : {errors_5xx}\n\n").format(errors_5xx=stats['errors_5xx']), style=colors["danger"])

        content.append(_("── CLIENTS & RÉSEAU ────────\n"), style=colors["heading"])
        content.append(_(" 💻 IPs uniques : {unique_ips}\n").format(unique_ips=stats['unique_ips']), style=colors["main"])
        content.append(_(" 🖧 Top Talker  : {value}\n\n").format(value=stats['top_ip'][:14]), style=colors["info"])

        content.append(_("── SANTÉ & TAMPON ──────────\n"), style=colors["heading"])
        err_rate = stats["error_rate"]
        health_style = colors["available"] if err_rate < 5 else (colors["warning"] if err_rate < 15 else colors["danger"])
        health_label = "EXCELLENT" if err_rate < 2 else ("CORRECT" if err_rate < 10 else _("DÉGRADÉ"))
        content.append(_(" 🌡 Santé Log   : {health_label} ({err_rate:.1f}% err)\n").format(health_label=health_label, err_rate=err_rate), style=health_style)
        content.append(_(" 📥 Tampon Live : {buffer_size}/{BUFFER_SIZE}").format(buffer_size=stats['buffer_size'], BUFFER_SIZE=_BUFFER_SIZE), style=colors["main"])
        return content

    def _render_logs_table(self, colors: dict, entries: list[dict]) -> None:
        table = self.query_one("#logs-table", DataTable)
        # Suivi automatique seulement si on etait deja en bas : jamais arrache d'une lecture plus haut.
        follow = table.scroll_y >= table.max_scroll_y - 1
        table.clear()
        for entry in entries:
            status = entry.get("status_code", 0) or 0
            if 200 <= status < 300:
                status_style = colors["available"]
            elif 400 <= status < 500:
                status_style = colors["warning"]
            elif 500 <= status < 600:
                status_style = colors["danger"]
            else:
                status_style = "dim"

            latency = entry.get("response_time_ms", entry.get("latency", 0)) or 0
            if latency < 200:
                lat_style = colors["available"]
            elif latency < 500:
                lat_style = colors["warning"]
            else:
                lat_style = colors["danger"]
            lat_text = f"{latency}ms" if latency > 0 else "-"

            bytes_sent = entry.get("bytes_sent", entry.get("size", 0)) or 0
            if bytes_sent > 1024 * 1024:
                size_str = f"{bytes_sent / (1024 * 1024):.1f}MB"
            elif bytes_sent > 1024:
                size_str = f"{bytes_sent / 1024:.1f}KB"
            elif bytes_sent > 0:
                size_str = f"{bytes_sent}B"
            else:
                size_str = "-"

            user_agent = str(entry.get("user_agent", "")).lower()
            if "bot" in user_agent or "crawler" in user_agent:
                client_type = Text(_("🤖 Bot"), style=colors["warning"])
            elif "curl" in user_agent or "python" in user_agent or "scanner" in user_agent:
                client_type = Text(_("⚠ CLI"), style=colors["danger"])
            else:
                client_type = Text(_("🖧 Web"), style="dim")

            table.add_row(
                str(entry.get("timestamp") or "").strip()[:19],
                str(entry.get("source_ip") or "N/A").strip()[:15],
                client_type,
                str(entry.get("method") or "-").strip()[:6],
                str(entry.get("path") or "-").strip(),
                Text(str(status), style=status_style),
                size_str,
                Text(lat_text, style=lat_style),
            )
        if follow:
            table.call_after_refresh(table.scroll_end, animate=False)
