# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 5.1 (alias 8.5) — Visualiser les logs en direct (Live Tail), viewer Simple.
Selection d'une source (Bibliotheque, epingles, historique, saisie manuelle) via ManageLiveTailPinsCommand,
puis suivi temps reel (Screen.set_interval de 2 s).

Depuis le 2026-11-21 (A_FAIRE §9), le suivi est ALIGNE sur le viewer Simple d'omega-serv (reference) :
lignes analysees par domain/log_stats/parser.py, cadre de stats par domain/log_stats/analytics.py::
compute_traffic_stats (valeurs reellement lues, debits rapportes a la periode des horodatages), memes
colonnes (ligne entiere coloree par information, Service, Duree). Propre a omega-fire : lecture d'une URL
http(s) et colonne Type (Bot / CLI / Web, d'apres le vrai User-Agent).

Deux etats bascules via `.omega-hidden` (meme patron que les champs
conditionnels des formulaires) : selection de la source, puis suivi live."""

from __future__ import annotations

import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING

from rich.cells import cell_len, set_cell_size
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.timer import Timer
from textual.widgets import Button, DataTable, Footer, Header, Input, Static

from omega_fire.application.commands.manage_live_tail_pins import (
    ManageLiveTailPinsCommand,
)
from omega_fire.domain.log_stats.analytics import compute_traffic_stats
from omega_fire.domain.log_stats.models import LogEntry, TrafficStats
from omega_fire.domain.log_stats.parser import extract_user_agent, parse_log_line
from omega_fire.infrastructure.config.paths import RUNTIME_DIR
from omega_fire.infrastructure.storage.files.json_store import JsonStore
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.screens._log_sources import library_paths
from omega_fire.interfaces.tui.screens.log_line_highlight import (
    LinePalette,
    highlight_log_line,
    palette_from_theme,
)
from omega_fire.interfaces.tui.support.action_audit import log_action_result
from omega_fire.shared.i18n import _

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ACTION_TITLE = "8.5 Visualiser les logs serveurs avec Tail"
_REFRESH_SECONDS = 2.0
_BUFFER_SIZE = 500


class _LogReader:
    """Lecture d'une source (fichier suivi comme `tail -f`, rotation detectee, ou URL http(s)) - repris de
    l'ancien _LogProvider, SANS son parseur (2026-11-21, viewer Simple aligne sur omega-serv) : les lignes
    sont analysees par domain/log_stats/parser.py, qui ne suppose jamais une taille, une duree ou un
    User-Agent absents du log (l'ancien mettait 350 octets, 25 ms et « Mozilla/5.0 »)."""

    def __init__(self, source: str):
        self.source = source
        self._offset = 0
        self._primed = False
        self._previous_url_lines: list[str] = []

    def _read_last_lines(self, path: str, limit: int, chunk_size: int = 65536) -> list[str]:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            pos = f.tell()
            data = b""
            while pos > 0 and data.count(b"\n") <= limit:
                read_size = min(chunk_size, pos)
                pos -= read_size
                f.seek(pos)
                data = f.read(read_size) + data
        lines = data.decode("utf-8", errors="ignore").splitlines()
        if pos > 0 and lines:
            lines = lines[1:]
        return lines[-limit:]

    def read_new_lines(self, limit: int) -> list[str]:
        """Lignes apparues depuis l'appel precedent (au premier : les `limit` dernieres). OSError ou
        urllib.error.URLError si la source est illisible."""
        if self.source.startswith(("http://", "https://")):
            return self._read_url(limit)
        if not self._primed:
            lines = self._read_last_lines(self.source, limit)
            with open(self.source, "rb") as f:
                f.seek(0, os.SEEK_END)
                self._offset = f.tell()
            self._primed = True
            return lines
        with open(self.source, "rb") as f:
            f.seek(0, os.SEEK_END)
            if f.tell() < self._offset:  # fichier tronque ou remplace (rotation)
                self._offset = 0
            f.seek(self._offset)
            new_bytes = f.read()
            self._offset = f.tell()
        return new_bytes.decode("utf-8", errors="ignore").splitlines()

    def _read_url(self, limit: int) -> list[str]:
        separator = "&" if "?" in self.source else "?"
        fresh_url = f"{self.source}{separator}_cb={int(time.time() * 1000)}"
        with urllib.request.urlopen(fresh_url, timeout=5) as response:
            lines = response.read().decode("utf-8", errors="ignore").splitlines()[-limit:]
        # Une URL se relit en entier : seules les lignes au-dela de celles deja vues sont nouvelles (avant
        # 2026-11-21, toute la fin du fichier etait rajoutee au tampon toutes les 2 s).
        new = _lines_after_overlap(self._previous_url_lines, lines)
        self._previous_url_lines = lines
        return new


def _lines_after_overlap(previous: list[str], current: list[str]) -> list[str]:
    """Lignes de `current` qui suivent la plus longue fin de `previous` retrouvee en tete de `current`."""
    for size in range(min(len(previous), len(current)), 0, -1):
        if current[:size] == previous[-size:]:
            return current[size:]
    return current


_TOP_WIDTH = 32
"""Largeur du cadre avant le premier rendu (34 colonnes moins la bordure)."""
_MESSAGE_MAX = 4000
"""Ligne entiere dans « Message », comme omega-serv (retour utilisateur 2026-11-20 : coupee, l'ascenseur
horizontal s'arretait avant le User-Agent) ; borne seulement contre une ligne demesuree."""


def _format_bytes(size: float) -> str:
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    if size >= 1024:
        return f"{size / 1024:.1f} KB"
    return f"{int(size)} B"


class LiveTailScreen(OmegaScreen):
    """5.1/8.5 — selection de source puis suivi live (tableau + stats)."""

    def __init__(
        self, *, container: DependencyContainer, source: str | None = None
    ) -> None:
        """source : ouverture directe sur ce log (lecteur Simple de 5.2 Favoris / 5.3 Voir
        les logs) — sans passer par la selection, sans toucher a l'historique de 8.5 ;
        « Arreter / Retour » revient alors a l'ecran appelant."""
        super().__init__()
        self._container = container
        self._direct_source = source
        self._command = ManageLiveTailPinsCommand(JsonStore(RUNTIME_DIR))
        self._display_items: dict[str, dict] = {}
        self._reader: _LogReader | None = None
        self._buffer: list[LogEntry] = []
        self._line_number = 0
        self._read_error: str | None = None
        self._first_render = True
        self._timer: Timer | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="setup-panel", classes="omega-panel"):
            yield Static(
                _("VISUALISER LES LOGS EN DIRECT (LIVE TAIL)"), classes="omega-title"
            )
            yield Static("", id="setup-hint", classes="omega-hint")
            yield DataTable(id="sources-table")
            yield Input(
                placeholder=_("Nom de l'épingle (uniquement pour 'Épingler')"),
                id="pin-name-input",
            )
            yield Input(
                placeholder=_("Chemin du fichier ou URL http(s)://..."),
                id="source-input",
            )
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
                # Cadre qui defile (repris d'omega-log / omega-serv) : avec les tops, un Static seul a
                # hauteur fixe coupait la fin de son contenu.
                with VerticalScroll(id="stats-frame", classes="omega-dash-box"):
                    yield Static(id="stats-box")
                yield DataTable(id="logs-table")
            with (
                Horizontal(classes="omega-actions"),
                Container(classes="omega-btn-frame"),
            ):
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
        self.query_one("#sources-table", DataTable).add_columns(
            _("Type"), _("Nom"), _("Chemin")
        )
        self.query_one("#logs-table", DataTable).add_columns(
            _("Heure"), _("Niveau"), _("Source"), _("IP"), _("Type"), _("Service"), _("Code"), _("Durée"),
            _("Message"),
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

        # Logs de la Bibliotheque (5.1) en tete (2026-11-09 : « 8.5 et 8.6 doivent aussi etre alimentes par la
        # Bibliotheque ») ; les epingles et l'historique (raccourcis manuels d'origine) suivent.
        pinned_paths = set(self._command.list_active_pinned().values())
        for lib_path in library_paths():
            if lib_path in pinned_paths:
                continue
            key = str(idx)
            self._display_items[key] = {
                "type": "library",
                "name": _("Bibliothèque"),
                "path": lib_path,
            }
            table.add_row(_("Bibliothèque"), Text(Path(lib_path).name), Text(lib_path), key=key)
            idx += 1

        for name, path in self._command.list_active_pinned().items():
            key = str(idx)
            self._display_items[key] = {"type": "pinned", "name": name, "path": path}
            table.add_row(_("Épingle"), Text(name), Text(path), key=key)
            idx += 1

        for h_path in self._command.list_history()[:5]:
            key = str(idx)
            self._display_items[key] = {
                "type": "history",
                "name": _("Historique récent"),
                "path": h_path,
            }
            table.add_row(_("Historique"), _("Historique récent"), Text(h_path), key=key)
            idx += 1

        hint = self.query_one("#setup-hint", Static)
        if self._display_items:
            hint.update(
                _("Sélectionnez une ligne, ou saisissez un chemin/URL manuellement.")
            )
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
            hint.update(
                _("Aucune source épinglée. Saisissez un chemin/URL manuellement.")
            )

    def _apply_selected_item(self, item: dict) -> None:
        self.query_one("#source-input", Input).value = item["path"]
        self.query_one("#pin-name-input", Input).value = (
            item["name"] if item["type"] == "pinned" else ""
        )

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
            self.app.notify(
                _("Nom et chemin requis pour épingler."), severity="warning"
            )
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
        if item["type"] == "library":
            self.app.notify(
                _(
                    "Ce log vient de la Bibliothèque : retirez-le depuis 5.1 Bibliothèque."
                ),
                severity="warning",
            )
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
        source = (
            self._direct_source or self.query_one("#source-input", Input).value.strip()
        )
        if not source:
            self.app.notify(
                _("Source invalide. Saisissez un chemin ou une URL."),
                severity="warning",
            )
            return

        if (
            not self._direct_source
            and source not in self._command.list_all_known_paths()
        ):
            self._command.record_history(source)

        if self._timer is not None:
            self._timer.stop()

        self._reader = _LogReader(source)
        self._buffer = []
        self._line_number = 0
        self._read_error = None
        self.query_one("#live-title", Static).update(
            _("LIVE TAIL — {source}").format(source=source)
        )

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
        if self._reader is None:
            return
        try:
            lines = self._reader.read_new_lines(_BUFFER_SIZE)
        except (OSError, urllib.error.URLError, ValueError) as exc:
            message = _("Erreur de lecture ({source}) : {e}").format(source=self._reader.source, e=exc)
            if message != self._read_error:  # une fois par erreur, pas toutes les 2 s
                self._read_error = message
                self.app.notify(message, severity="error")
            lines = []
        else:
            self._read_error = None
        added = False
        for line in lines:
            self._line_number += 1
            entry = parse_log_line(line, line_number=self._line_number, log_path=self._reader.source)
            if entry is not None:
                self._buffer.append(entry)
                added = True
        if len(self._buffer) > _BUFFER_SIZE:
            self._buffer = self._buffer[-_BUFFER_SIZE:]

        self.query_one("#stats-box", Static).update(self._render_stats(compute_traffic_stats(self._buffer)))
        # Tout le tampon, du plus ancien au plus recent, comme le viewer Simple d'omega-serv (reference,
        # retour utilisateur 2026-11-02) : avant, seules les 30 plus recentes en tete, sans ascenseur.
        if added or self._first_render:
            self._first_render = False
            self._render_logs_table()

    def _render_stats(self, stats: TrafficStats) -> Text:
        """Cadre de stats IDENTIQUE au viewer Simple d'omega-serv (reference) : debits rapportes a la periode
        couverte par les horodatages du tampon, « - » pour une valeur absente du log (2026-11-21 : plus de
        350 octets / 25 ms supposes, ni de debit rapporte au temps passe devant l'ecran)."""
        variables = self.app.get_css_variables()
        heading = f"bold {variables.get('secondary', '')}".strip()
        good = variables.get("status-available", "") or variables.get("success", "green") or "green"
        warn = variables.get("warning", "yellow") or "yellow"
        bad = variables.get("error", "red") or "red"
        info = variables.get("secondary", "cyan") or "cyan"
        none = "-"

        content = Text()
        content.append(_("── RENDEMENT ──────────────\n"), style=heading)
        rps = (
            none
            if stats.requests_per_second is None
            else _("{requests_per_second:.1f} req/s").format(
                requests_per_second=stats.requests_per_second
            )
        )
        content.append(_(" ⚡ Débit        : {rps}\n").format(rps=rps), style=info)
        if stats.avg_latency_ms is None:
            content.append(_(" ⏱ Latence moy. : {none}\n\n").format(none=none))
        else:
            latency = stats.avg_latency_ms
            style = good if latency < 200 else (warn if latency < 500 else bad)
            content.append(
                _(" ⏱ Latence moy. : {latency:.0f} ms\n\n").format(latency=latency),
                style=style,
            )

        content.append(_("── BANDE PASSANTE ─────────\n"), style=heading)
        bps = none if stats.bytes_per_second is None else f"{_format_bytes(stats.bytes_per_second)}/s"
        volume = none if stats.bytes_total is None else _format_bytes(stats.bytes_total)
        average = none if stats.avg_size is None else _format_bytes(stats.avg_size)
        content.append(_(" 🌐 Débit réseau : {bps}\n").format(bps=bps))
        content.append(_(" 📦 Volume total : {total}\n").format(total=volume))
        content.append(_(" 🗜 Taille moy.  : {average}\n\n").format(average=average))

        content.append(_("── STATUTS HTTP ───────────\n"), style=heading)
        content.append(_(" 📊 Requêtes     : {http_total}\n").format(http_total=stats.http_total))
        content.append(_(" √  Succès 2xx   : {status_2xx}\n").format(status_2xx=stats.status_2xx), style=good)
        content.append(_(" ↔  Redir. 3xx   : {status_3xx}\n").format(status_3xx=stats.status_3xx), style=info)
        content.append(_(" ⚠  Erreurs 4xx  : {status_4xx}\n").format(status_4xx=stats.status_4xx), style=warn)
        content.append(_(" ❌ Erreurs 5xx  : {status_5xx}\n").format(status_5xx=stats.status_5xx), style=bad)
        content.append(_(" ⛔ Refus 403    : {status_403}\n").format(status_403=stats.status_403), style=warn)
        content.append(_(" ⏳ Refus 429    : {status_429}\n\n").format(status_429=stats.status_429), style=warn)

        content.append(_("── CLIENTS & RÉSEAU ───────\n"), style=heading)
        content.append(_(" 💻 IPs uniques  : {unique_ips}\n").format(unique_ips=stats.unique_ips))
        # Adresse sur sa propre ligne : une IPv4 longue ou une IPv6 deborderait du cadre (34 colonnes).
        content.append(_(" 🖧 Top 5 IP     :\n"), style=info)
        self._append_top(content, stats.top_ips, info)
        if stats.top_paths:
            content.append(_("── CHEMINS DEMANDÉS ───────\n"), style=heading)
            self._append_top(content, stats.top_paths, "")
            content.append(_("── CHEMINS EN 404 ─────────\n"), style=heading)
            self._append_top(content, stats.top_not_found, warn)

        content.append(_("── SANTÉ & TAMPON ─────────\n"), style=heading)
        rate = stats.error_rate
        health_style = good if rate < 5 else (warn if rate < 15 else bad)
        health = "EXCELLENT" if rate < 2 else ("CORRECT" if rate < 10 else _("DÉGRADÉ"))
        content.append(_(" 🌡 Santé        : {health}\n").format(health=health), style=health_style)
        content.append(_(" ⚠  Taux d'erreur: {rate:.1f}%\n").format(rate=rate), style=health_style)
        content.append(
            _(" 📥 Tampon       : {count}/{BUFFER_SIZE}").format(
                count=len(self._buffer), BUFFER_SIZE=_BUFFER_SIZE
            )
        )
        return content

    def _append_top(
        self, content: Text, items: list[tuple[str, int]], style: str
    ) -> None:
        """Repris d'omega-log : valeur depuis le bord gauche, compte aligne a droite une colonne avant le bord."""
        if not items:
            content.append("    " + _("(aucun)") + "\n\n", style="dim")
            return
        width = self.query_one("#stats-box", Static).size.width or _TOP_WIDTH
        count_width = max(len(str(count)) for _value, count in items)
        room = max(8, width - 3 - count_width)
        for value, count in items:
            shown = (
                value
                if cell_len(value) <= room
                else set_cell_size(value, room - 1) + "…"
            )
            content.append(
                " " + shown + " " * (room - cell_len(shown)) + " ", style=style
            )
            content.append(f"{count:>{count_width}}\n", style="bold")
        content.append("\n")

    def _client_type(self, entry: LogEntry, palette: LinePalette) -> Text | str:
        """Propre a omega-fire : robot, outil en ligne de commande ou navigateur, d'apres le VRAI User-Agent
        (« - » quand le log n'en donne pas)."""
        agent = extract_user_agent(entry.raw_line)
        if agent is None:
            return "-"
        lowered = agent.lower()
        if "bot" in lowered or "crawler" in lowered or "spider" in lowered:
            return Text(_("🤖 Bot"), style=palette.warn)
        if any(tool in lowered for tool in ("curl", "wget", "python", "scanner", "go-http")):
            return Text(_("⚠ CLI"), style=palette.bad)
        return Text(_("🖧 Web"), style="dim")

    def _render_logs_table(self) -> None:
        """Memes colonnes que le viewer Simple d'omega-serv (reference, 2026-11-20 : ligne entiere, couleurs
        du theme par information, colonne Service, Duree), plus Type, propre a omega-fire."""
        table = self.query_one("#logs-table", DataTable)
        # Suivi automatique seulement si on etait deja en bas : jamais arrache d'une lecture plus haut.
        follow = table.scroll_y >= table.max_scroll_y - 1
        table.clear()
        palette = palette_from_theme(self.app.get_css_variables())
        for entry in self._buffer:
            level_style = {"error": palette.bad, "critical": f"bold {palette.bad}",
                           "warning": palette.warn}.get(entry.level.value, "")
            if entry.http_status is None:
                code_cell: Text | str = "-"
            else:
                code_cell = Text(str(entry.http_status), style=palette.status(entry.http_status))
            if entry.latency_ms is None:
                duration_cell: Text | str = "-"
            else:
                latency = entry.latency_ms
                latency_style = palette.good if latency < 200 else (palette.warn if latency < 500 else palette.bad)
                duration_cell = Text(f"{latency}ms", style=latency_style)
            level = entry.level.value.upper()
            table.add_row(
                entry.timestamp.strftime("%H:%M:%S"),
                Text(level, style=level_style) if level_style else level,
                entry.source.value,
                # Texte venu du client (ligne de requete) : jamais lu comme balisage Rich.
                Text(entry.ip or "-"),
                self._client_type(entry, palette),
                Text(entry.service or "-"),
                code_cell,
                duration_cell,
                highlight_log_line(entry.raw_line.strip()[:_MESSAGE_MAX], palette),
            )
        if follow:
            table.call_after_refresh(table.scroll_end, animate=False)
