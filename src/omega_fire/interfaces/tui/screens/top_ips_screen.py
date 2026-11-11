# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 5.2 — Analyser les IPs (Top N). Patron #3 riche : source
(epingle ou chemin manuel), Top N, periode, chacun avec ses champs
conditionnels. Logique identique a
interfaces/cli/actions.py::action_5_2_top_ips. La gestion des epingles
reutilise PinnedPathsScreen (Phase 2/2.2) plutot que de dupliquer le
CRUD ici."""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.widgets import Button, DataTable, Footer, Header, Input, Select, Static

from omega_fire.application.commands.manage_pinned_log_paths import ManagePinnedLogPathsCommand
from omega_fire.domain.reports.top_ips import TOP_IPS_EXPORT_PREFIX, TopIpRow, TopIpsReport
from omega_fire.infrastructure.exporters.top_ips_exporter import write_top_ips
from omega_fire.infrastructure.config.paths import DEFAULT_PINNED_FILES, RUNTIME_DIR, VAR_DIR
from omega_fire.infrastructure.storage.files.json_store import JsonStore
from omega_fire.interfaces.tui.export_language import export_translation
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.screens.ban_ip_list_screen import _extract_valid_ips
from omega_fire.interfaces.tui.screens.export_blacklist_screen import _HTML_THEMES
from omega_fire.interfaces.tui.screens._log_sources import log_source_options
from omega_fire.interfaces.tui.screens.confirm import ConfirmScreen
from omega_fire.infrastructure.storage.files.log_ip_removal import remove_ips_in_place
from omega_fire.interfaces.tui.screens.remove_ip_from_log_screen import parse_ip_list, split_lines_by_ips
from omega_fire.interfaces.tui.screens.pinned_paths_screen import PinnedPathsScreen
from omega_fire.interfaces.tui.support.action_audit import log_action_result
from omega_fire.shared.i18n import _, translating_as

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ACTION_TITLE = "5.4 Analyser les IPs (Top N)"
_REMOVE_ACTION_TITLE = "5.5 Supprimer une IP des logs"
"""Retrait depuis 5.4 : meme titre d'historique que 5.5 (meme geste, meme ecriture)."""
_SRC_MANUAL = "__manual__"

_LOG_PATTERN = re.compile(
    r'^(?P<ip>\S+)\s+\S+\s+\S+\s+\[(?P<time>[^\]]+)\]\s+"(?P<method>\S+)\s+(?P<path>\S+)[^"]*"\s+(?P<status>\d+)\s+(?P<size>\d+|-)'
)


def _format_size(size: int) -> str:
    if size > 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    if size > 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size} B"


def _count_ips(log_path: Path, time_limit: datetime | None) -> tuple[dict[str, int], dict[str, int], int, bool]:
    """Comptage des IPs (logique d'origine de 5.4, deplacee hors de l'ecran pour tourner dans un fil).
    Leve OSError si le fichier est illisible."""
    ip_counts: dict[str, int] = {}
    ip_bytes: dict[str, int] = {}
    total_occurrences = 0
    is_raw_ip_file = False

    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = _LOG_PATTERN.search(line)
        if match:
            ip = match.group("ip")
            raw_time = match.group("time")
            raw_size = match.group("size")
            if time_limit:
                try:
                    date_str = raw_time.split()[0]
                    log_dt = datetime.strptime(date_str, "%d/%b/%Y:%H:%M:%S")
                    if log_dt < time_limit:
                        continue
                except ValueError:
                    pass
            bytes_sent = int(raw_size) if raw_size.isdigit() else 0
            ip_counts[ip] = ip_counts.get(ip, 0) + 1
            ip_bytes[ip] = ip_bytes.get(ip, 0) + bytes_sent
            total_occurrences += 1
        else:
            raw_ips = _extract_valid_ips(line)
            if raw_ips:
                is_raw_ip_file = True
                for ip in raw_ips:
                    ip_counts[ip] = ip_counts.get(ip, 0) + 1
                    total_occurrences += 1
    return ip_counts, ip_bytes, total_occurrences, is_raw_ip_file

class TopIpsScreen(OmegaScreen):
    """Analyse Top N des IPs les plus actives dans un log ou fichier brut."""

    CSS = """
    /* Retour utilisateur 2026-10-28 : en pleine largeur, le tableau de resultats
       annulait le centrage du formulaire (tout colle a gauche) ; meme largeur que le
       formulaire (70). Hauteur naturelle : le 1fr commun aux DataTable l'ecrasait a
       une ligne dans la zone qui defile. */
    TopIpsScreen #result-table {
        width: 70;
        height: auto;
    }

    TopIpsScreen #export-section {
        width: 70;
        height: auto;
    }

    TopIpsScreen #export-section .omega-subtitle {
        margin-top: 1;
    }

    TopIpsScreen #export-section .omega-actions {
        width: 100%;
        align: center middle;
    }
    """

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container
        self._pinned_command = ManagePinnedLogPathsCommand(
            JsonStore(RUNTIME_DIR),
            relative_path="blocklist_analysis_pinned_paths.json",
            defaults=[str(p) for p in DEFAULT_PINNED_FILES],
        )
        self._report: TopIpsReport | None = None
        self._custom_days = ""
        self._analyzed_path: Path | None = None
        """Fichier de la derniere analyse (ou recherche) : cible du retrait d'IP."""
        self._selected_ip: str | None = None
        self._busy = False

    def _source_options(self) -> list[tuple[str, str]]:
        # Bibliotheque (5.1) en tete, puis epingles, puis chemin manuel (2026-11-09).
        return log_source_options(self._pinned_command.list_paths(), _SRC_MANUAL)

    @staticmethod
    def _period_options() -> list[tuple[str, str]]:
        return [(_("Tout le fichier"), "all"), (_("Dernière heure"), "1h"), (_("Dernières 24 heures"), "24h"),
                (_("Derniers 7 jours"), "7d"), (_("Saisie manuelle (jours)"), "custom")]

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(classes="omega-form-panel"):
            yield Static(_("ANALYSER LES IPs (TOP N)"), classes="omega-title")

            yield Static(_("Source (fichier log ou blocklist)"), classes="omega-subtitle")
            yield Select(self._source_options(), id="source-select", prompt=_("Sélectionner"))
            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Gérer les épingles"), id="manage-pins")

            yield Static(_("Chemin manuel"), id="manual-label", classes="omega-subtitle omega-hidden")
            yield Input(
                value=str(VAR_DIR / "log" / "access.log"),
                id="manual-input",
                classes="omega-hidden",
            )

            yield Static(_("Nombre d'IPs (Top N)"), classes="omega-subtitle")
            yield Select(
                [(_("Top 10"), "10"), (_("Top 50"), "50"), (_("Top 100"), "100"), (_("Personnalisé"), "custom")],
                value="10",
                id="topn-select",
            )
            yield Static(_("Nombre personnalisé"), id="topn-custom-label", classes="omega-subtitle omega-hidden")
            yield Input(value="20", id="topn-custom-input", classes="omega-hidden")

            yield Static(_("Période à analyser"), classes="omega-subtitle")
            yield Select(self._period_options(), value="all", id="period-select")
            yield Static(_("Nombre de jours"), id="period-custom-label", classes="omega-subtitle omega-hidden")
            yield Input(value="30", id="period-custom-input", classes="omega-hidden")

            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Analyser"), id="launch", variant="primary")
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Retour"), id="back")

            yield Static("", id="result-hint", classes="omega-hint")
            yield DataTable(id="result-table")

            # Au niveau de « Voir et traiter IP » d'omega-serv / omega-log (2026-11-09) : chercher une IP
            # precise dans le log (fichier entier) et retirer l'IP choisie (ligne du tableau ou recherche).
            yield Static(_("Ou cherchez une IP précise dans ce log (fichier entier) :"), classes="omega-subtitle")
            yield Input(placeholder=_("Adresse IP"), id="search-ip-input")
            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Rechercher cette IP"), id="search-ip")
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Retirer cette IP du log analysé"), id="remove-ip", variant="error",
                                 disabled=True)
            yield Static("", id="ip-search-result", classes="omega-hint")

            # Version 3.5 : exporter le resultat (meme mecanisme que 6.1) pour le
            # recharger en 5.5 sans recopier les IPs a la main. Visible apres une analyse.
            with Vertical(id="export-section", classes="omega-hidden"):
                yield Static(_("Exporter le résultat (rechargeable en 5.5)"), classes="omega-subtitle")
                yield Select(
                    [(_("JSON (brut structure)"), "json"), (_("TXT (1 IP par ligne, réinjectable)"), "txt"),
                     (_("HTML (rapport visuel)"), "html")],
                    value="json",
                    id="format-select",
                )
                yield Static(_("Thème HTML"), id="theme-label", classes="omega-subtitle omega-hidden")
                yield Select(
                    [(label, name) for name, label in _HTML_THEMES.items()],
                    value="omega-base",
                    id="theme-select",
                    classes="omega-hidden",
                )
                with Horizontal(classes="omega-actions"):
                    with Container(classes="omega-btn-frame"):
                        yield Button(_("Exporter"), id="export", variant="primary")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#result-table", DataTable).cursor_type = "row"
        options = self._source_options()
        if options:
            self.query_one("#source-select", Select).value = options[0][1]

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "source-select":
            is_manual = str(event.value) == _SRC_MANUAL
            self.query_one("#manual-label", Static).set_class(not is_manual, "omega-hidden")
            self.query_one("#manual-input", Input).set_class(not is_manual, "omega-hidden")
        elif event.select.id == "topn-select":
            is_custom = str(event.value) == "custom"
            self.query_one("#topn-custom-label", Static).set_class(not is_custom, "omega-hidden")
            self.query_one("#topn-custom-input", Input).set_class(not is_custom, "omega-hidden")
        elif event.select.id == "format-select":
            is_html = str(event.value) == "html"
            self.query_one("#theme-label", Static).set_class(not is_html, "omega-hidden")
            self.query_one("#theme-select", Select).set_class(not is_html, "omega-hidden")
        elif event.select.id == "period-select":
            is_custom = str(event.value) == "custom"
            self.query_one("#period-custom-label", Static).set_class(not is_custom, "omega-hidden")
            self.query_one("#period-custom-input", Input).set_class(not is_custom, "omega-hidden")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss()
            return
        if event.button.id == "manage-pins":
            self.app.push_screen(PinnedPathsScreen(container=self._container), self._refresh_source_select)
            return
        if event.button.id == "export":
            self._export()
            return
        if event.button.id == "search-ip":
            self._search_ip()
            return
        if event.button.id == "remove-ip":
            self._confirm_remove_ip()
            return
        if event.button.id != "launch":
            return
        self._analyze()

    def _refresh_source_select(self, _result: None) -> None:
        select = self.query_one("#source-select", Select)
        select.set_options(self._source_options())

    def _analyze(self) -> None:
        source = self.query_one("#source-select", Select).value
        if source == _SRC_MANUAL or source is None or source == Select.BLANK:
            selected_file = self.query_one("#manual-input", Input).value.strip()
        else:
            selected_file = str(source)
        if not selected_file:
            self.app.notify(_("Saisissez un chemin de fichier."), severity="warning")
            return
        log_path = Path(selected_file)

        topn_choice = str(self.query_one("#topn-select", Select).value)
        if topn_choice == "custom":
            raw = self.query_one("#topn-custom-input", Input).value.strip()
            limit_n = int(raw) if raw.isdigit() and int(raw) > 0 else 20
        else:
            limit_n = int(topn_choice)

        period_choice = str(self.query_one("#period-select", Select).value)
        now = datetime.now()
        time_limit = None
        if period_choice == "1h":
            time_limit = now - timedelta(hours=1)
        elif period_choice == "24h":
            time_limit = now - timedelta(days=1)
        elif period_choice == "7d":
            time_limit = now - timedelta(days=7)
        elif period_choice == "custom":
            raw = self.query_one("#period-custom-input", Input).value.strip()
            if raw.isdigit() and int(raw) > 0:
                time_limit = now - timedelta(days=int(raw))

        if self._busy:
            return
        self._busy = True
        self.query_one("#launch", Button).disabled = True
        self.query_one("#result-hint", Static).update(_("Analyse en cours... (l'interface reste utilisable)"))
        self._analyzed_path = log_path
        self.run_worker(lambda: self._compute_in_thread(log_path, time_limit, limit_n), thread=True,
                        exclusive=True, group="top-ips")

    def _compute_in_thread(self, log_path: Path, time_limit: datetime | None, limit_n: int) -> None:
        """Lecture et comptage hors de l'interface (2026-11-09, comme omega-serv / omega-log : un gros
        log figeait l'ecran pendant l'analyse)."""
        try:
            result = _count_ips(log_path, time_limit)
        except Exception as e:  # noqa: BLE001 - tout echec de lecture est montre a l'utilisateur
            self.app.call_from_thread(self._analysis_failed, str(e))
            return
        self.app.call_from_thread(self._show_analysis, log_path, limit_n, *result)

    def _analysis_failed(self, error: str) -> None:
        self._busy = False
        self.query_one("#launch", Button).disabled = False
        self.query_one("#result-hint", Static).update("")
        self.app.notify(_("Erreur lors de la lecture du fichier : {e}").format(e=error), severity="error")

    def _show_analysis(self, log_path: Path, limit_n: int, ip_counts: dict[str, int], ip_bytes: dict[str, int],
                       total_occurrences: int, is_raw_ip_file: bool) -> None:
        self._busy = False
        try:
            self.query_one("#launch", Button).disabled = False
        except NoMatches:
            return  # ecran deja ferme
        table = self.query_one("#result-table", DataTable)
        table.clear(columns=True)
        hint = self.query_one("#result-hint", Static)
        self._report = None
        self.query_one("#export-section").set_class(True, "omega-hidden")

        if not ip_counts:
            hint.update(_("Aucune IP valide n'a pu être extraite de ce fichier."))
            return

        sorted_ips = sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)[:limit_n]
        duplicates_count = sum(count - 1 for count in ip_counts.values() if count > 1)
        period_value = str(self.query_one("#period-select", Select).value)
        self._custom_days = self.query_one("#period-custom-input", Input).value.strip()
        self._report = TopIpsReport(
            source=str(log_path), period=period_value, total_occurrences=total_occurrences,
            unique_ips=len(ip_counts), raw_ip_file=is_raw_ip_file,
            rows=[
                TopIpRow(
                    rank=rank, ip=ip, count=count,
                    percent=None if is_raw_ip_file else (
                        round(count / total_occurrences * 100, 1) if total_occurrences else 0.0),
                    volume_bytes=None if is_raw_ip_file else ip_bytes.get(ip, 0),
                )
                for rank, (ip, count) in enumerate(sorted_ips, start=1)
            ],
        )
        self.query_one("#export-section").set_class(False, "omega-hidden")

        if is_raw_ip_file:
            table.add_columns(_("Rang"), _("Adresse IP"), _("Occurrences"), _("Statut"))
            for rank, (ip, count) in enumerate(sorted_ips, start=1):
                status = _("Doublon") if count > 1 else _("Unique")
                table.add_row(f"#{rank}", ip, str(count), status, key=ip)
            if duplicates_count > 0:
                hint.update(_("Total entrées : {total_occurrences} | IPs uniques : {count} | Doublons : {duplicates_count}").format(total_occurrences=total_occurrences, count=len(ip_counts), duplicates_count=duplicates_count))
            else:
                hint.update(_("Fichier propre : {count} IPs uniques sans doublon.").format(count=len(ip_counts)))
        else:
            table.add_columns(_("Rang"), _("Adresse IP"), _("Requêtes"), _("% Trafic"), _("Volume"))
            for rank, (ip, count) in enumerate(sorted_ips, start=1):
                pct = (count / total_occurrences * 100) if total_occurrences > 0 else 0
                table.add_row(f"#{rank}", ip, f"{count:,}", f"{pct:.1f}%", _format_size(ip_bytes.get(ip, 0)), key=ip)
            hint.update(_("Analyse terminée ({count} IPs affichées sur {total_occurrences} requêtes).").format(count=len(sorted_ips), total_occurrences=total_occurrences))

    # ------------------------------------------------------------------
    # Recherche et retrait d'une IP (au niveau de « Voir et traiter IP », 2026-11-09)
    # ------------------------------------------------------------------
    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.data_table.id != "result-table" or event.row_key is None or event.row_key.value is None:
            return
        self._select_ip(str(event.row_key.value))

    def _select_ip(self, ip: str) -> None:
        self._selected_ip = ip
        button = self.query_one("#remove-ip", Button)
        button.disabled = self._analyzed_path is None

    def _current_path(self) -> Path | None:
        source = self.query_one("#source-select", Select).value
        if source == _SRC_MANUAL or source is None or source == Select.BLANK:
            raw = self.query_one("#manual-input", Input).value.strip()
        else:
            raw = str(source)
        return Path(raw) if raw else None

    def _search_ip(self) -> None:
        candidates, invalid = parse_ip_list(self.query_one("#search-ip-input", Input).value)
        if invalid or len(candidates) != 1:
            self.app.notify(_("Saisissez une seule adresse IP valide."), severity="warning")
            return
        path = self._current_path()
        if path is None:
            self.app.notify(_("Saisissez un chemin de fichier."), severity="warning")
            return
        ip = candidates[0]
        self.query_one("#ip-search-result", Static).update(_("Recherche en cours..."))
        self.run_worker(lambda: self._search_in_thread(path, ip), thread=True, exclusive=True, group="top-ips-search")

    def _search_in_thread(self, path: Path, ip: str) -> None:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                counts, _cleaned = split_lines_by_ips(f.readlines(), [ip])
        except OSError as e:
            self.app.call_from_thread(self.app.notify, _("Impossible de lire le fichier : {e}").format(e=e),
                                      severity="error")
            return
        self.app.call_from_thread(self._show_search, path, ip, counts.get(ip, 0))

    def _show_search(self, path: Path, ip: str, count: int) -> None:
        try:
            result = self.query_one("#ip-search-result", Static)
        except NoMatches:
            return
        self._analyzed_path = path
        if count == 0:
            result.update(_("{ip} : absente de {name}.").format(ip=ip, name=path.name))
            self._selected_ip = None
            self.query_one("#remove-ip", Button).disabled = True
            return
        result.update(_("{ip} : {count} ligne(s) dans {name}.").format(ip=ip, count=count, name=path.name))
        self._select_ip(ip)

    def _confirm_remove_ip(self) -> None:
        ip, path = self._selected_ip, self._analyzed_path
        if ip is None or path is None:
            return
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                counts, cleaned_lines = split_lines_by_ips(f.readlines(), [ip])
        except OSError as e:
            self.app.notify(_("Impossible de lire le fichier : {e}").format(e=e), severity="error")
            return
        occurrences = counts.get(ip, 0)
        if occurrences == 0:
            self.app.notify(_("Aucune de ces IPs n'a été trouvée dans '{name}'.").format(name=path.name),
                            severity="warning")
            return
        details = _("  {ip} : {count} ligne(s)").format(ip=ip, count=occurrences)
        # Meme confirmation et meme ecriture que 5.5 (Supprimer une IP des logs).
        self.app.push_screen(
            ConfirmScreen(
                title=_("CONFIRMER LA SUPPRESSION"),
                message=_("Fichier : {name}\n{details}\n{occurrences} ligne(s) retirée(s), {count} ligne(s) "
                          "restante(s) après purge.").format(
                    name=path.name, details=details, occurrences=occurrences, count=len(cleaned_lines)),
            ),
            lambda confirmed: self._remove_if_confirmed(confirmed, path, ip, occurrences, cleaned_lines),
        )

    def _remove_if_confirmed(self, confirmed: bool | None, path: Path, ip: str, occurrences: int,
                             cleaned_lines: list[str]) -> None:
        if not confirmed:
            return
        try:
            # Sur place, binaire, relu juste avant l'ecriture (correctif 2026-11-10, voir 5.5).
            occurrences = sum(remove_ips_in_place(path, [ip]).values())
        except OSError as e:
            self.app.notify(_("Erreur lors de l'écriture dans le fichier : {e}").format(e=e), severity="error")
            log_action_result(self._container, _REMOVE_ACTION_TITLE, status="failure", error=str(e))
            return
        self.app.notify(_("{occurrences} ligne(s) retirée(s) de {name} ({count} IP(s)).").format(
            occurrences=occurrences, name=path.name, count=1))
        log_action_result(self._container, _REMOVE_ACTION_TITLE, status="success")
        self._selected_ip = None
        self.query_one("#remove-ip", Button).disabled = True
        self.query_one("#ip-search-result", Static).update("")
        if self._report is not None:
            self._analyze()  # resultat a jour, sans l'IP retiree

    def _export(self) -> None:
        report = self._report
        if report is None:
            self.app.notify(_("Lancez d'abord une analyse."), severity="warning")
            return
        fmt = str(self.query_one("#format-select", Select).value)
        theme_name = str(self.query_one("#theme-select", Select).value)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self._container.exports_dir / f"{TOP_IPS_EXPORT_PREFIX}{timestamp}.{fmt}"
        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with translating_as(export_translation(self, self._container)):
                html_context = None
                if fmt == "html":
                    html_context = self._html_context(report, theme_name)
                write_top_ips(report, fmt, path, generated_at,
                              html_exporter=self._container.get_exporter_port("html") if fmt == "html" else None,
                              html_context=html_context)
        except Exception as e:
            self.app.notify(_("Erreur lors de l'écriture du fichier d'export : {e}").format(e=e), severity="error")
            log_action_result(self._container, _ACTION_TITLE, status="failure", error=str(e))
            return
        self.app.notify(
            _("Export réussi : {count} IP(s) dans '{path}'. Rechargeable en 5.5, visible en 6.6.").format(
                count=len(report.rows), path=path),
            timeout=8,
        )
        log_action_result(self._container, _ACTION_TITLE, status="success")

    def _html_context(self, report: TopIpsReport, theme_name: str) -> dict:
        """Libelles traduits dans la langue des exports (appele sous translating_as)."""
        if report.raw_ip_file:
            columns = [_("Rang"), _("Adresse IP"), _("Occurrences"), _("Statut")]
            rows = [[f"#{row.rank}", row.ip, str(row.count), _("Doublon") if row.count > 1 else _("Unique")]
                    for row in report.rows]
        else:
            columns = [_("Rang"), _("Adresse IP"), _("Requêtes"), _("% Trafic"), _("Volume")]
            rows = [[f"#{row.rank}", row.ip, f"{row.count:,}", f"{row.percent:.1f}%",
                     _format_size(row.volume_bytes or 0)] for row in report.rows]
        period_value = report.period
        period_label = next((label for label, value in self._period_options() if value == period_value), "")
        if period_value == "custom":
            period_label = _("{days} derniers jours").format(days=self._custom_days)
        return {
            "page_title": _("Top IPs - Omega-Fire"),
            "heading": _("Classement des IPs les plus actives"),
            "source_label": _("Source"), "source_value": report.source,
            "period_label": _("Période"), "period_value": period_label,
            "columns": columns, "table_rows": rows, "theme_name": theme_name,
        }
