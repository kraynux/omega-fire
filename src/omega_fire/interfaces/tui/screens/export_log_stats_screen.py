# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 6.5 — Exporter les statistiques des logs (2026-11-09, OMEGA-FIRE_PLAN_LOGS_NIVEAU_SERV_LOG.md).

Porte d'omega-log (interfaces/tui/screens/access_log_stats_screen.py), meme schema qu'omega-serv /
omega-log : periodes 24h / 7j / 30j / Tout, calcul en processus separes avec indicateur d'attente,
synthese, statuts HTTP en jauges, top IP, chemins demandes, chemins en 404, repartition horaire,
tendance par jour, export JSON et HTML (themes d'omega-lib). LOGS SEULEMENT : les bans, jails et
l'etat du pare-feu restent dans 8.3 / 8.4 (rapports globaux) ; 5.10 garde sa vue rapide.

Differences avec omega-log (omega-fire) : logs choisis par cases a cocher (Bibliotheque 5.1 en tete,
puis epingles), pas d'elevation sudo (omega-fire tourne deja en root), dossier d'exports et langue des
exports d'omega-fire, action notee dans l'historique d'audit."""
from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from omega_lib.theme.policies import DEFAULT_EXPORT_THEME, EXPORT_PALETTES
from rich.cells import cell_len
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.css.query import NoMatches
from textual.widgets import Button, Footer, Header, Select, Static

from omega_fire.application.commands.manage_pinned_log_paths import ManagePinnedLogPathsCommand
from omega_fire.application.log_stats.access_log_stats import AccessLogStatsResult
from omega_fire.domain.log_stats.stats_report import RankedItem, StatsReport
from omega_fire.infrastructure.config.paths import BLOCKLIST_DIR, DEFAULT_PINNED_FILES, RUNTIME_DIR
from omega_fire.infrastructure.exporters.log_stats_html import LOG_STATS_EXPORT_PREFIX, export_log_stats_html
from omega_fire.infrastructure.storage.files.json_store import JsonStore
from omega_fire.interfaces.tui.export_language import export_translation
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.screens._log_sources import log_source_options
from omega_fire.interfaces.tui.screens._parallel_compute import accumulate_in_pool
from omega_fire.interfaces.tui.screens.checklist import CheckListScreen
from omega_fire.interfaces.tui.support.action_audit import log_action_result
from omega_fire.interfaces.tui.widgets.busy_indicator import (
    PERIOD_BUTTON_LABELS,
    PERIOD_HINT,
    BusyIndicator,
    describe_selection,
)
from omega_fire.interfaces.tui.widgets.gauges import append_gauge_line
from omega_fire.shared.i18n import N_, _, translating_as

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ACTION_TITLE = "6.5 Exporter les statistiques des logs"

_PERIODS: tuple[tuple[str, str | None], ...] = (
    ("24h", "24h"), ("7j", "7d"), ("30j", "30d"), ("Tout", None),
)
_BAR_WIDTH = 40
_LABEL_WIDTH = 39
"""Largeur maximale des libelles des classements (ajustee au plus long) : une IPv6 complete (39
caracteres) tient sans coupure."""
_PERIOD_LABELS: dict[str | None, str] = {
    "24h": N_("24 dernières heures"), "7d": N_("7 derniers jours"), "30d": N_("30 derniers jours"),
}
"""Traduits a l'affichage (l'export peut etre dans une autre langue que l'interface)."""


def _format_bytes(size: float) -> str:
    for unit, factor in ((_("Go"), 1024 ** 3), (_("Mo"), 1024 ** 2), (_("Ko"), 1024)):
        if size >= factor:
            return f"{size / factor:.1f} {unit}"
    return f"{int(size)} o"


def _export_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _is_blocklist(path: str) -> bool:
    """Les fichiers de blocklist epingles (listes d'IP) ne sont pas des logs : jamais proposes ici."""
    try:
        return Path(path).resolve().is_relative_to(BLOCKLIST_DIR.resolve())
    except (OSError, ValueError):
        return False


class ExportLogStatsScreen(OmegaScreen):
    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container
        self._pinned_command = ManagePinnedLogPathsCommand(
            JsonStore(RUNTIME_DIR),
            relative_path="blocklist_analysis_pinned_paths.json",
            defaults=[str(p) for p in DEFAULT_PINNED_FILES],
        )
        self._selected: list[str] = []
        self._result: AccessLogStatsResult | None = None
        self._computing = False

    def _available_logs(self) -> list[tuple[str, str]]:
        return [(label, value) for label, value in log_source_options(self._pinned_command.list_paths(), None)
                if not _is_blocklist(value)]

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(classes="omega-panel"):
            yield Static(_("EXPORTER LES STATISTIQUES DES LOGS"), classes="omega-title")
            yield Static(_("Logs seulement, même rapport qu'omega-serv et omega-log. Les bans, jails et l'état du "
                           "pare-feu sont dans les rapports 8.3 et 8.4."), classes="omega-hint")
            yield Static(_("Logs analysés"), classes="omega-subtitle")
            yield Static("", id="selected-logs")
            with Horizontal(classes="omega-actions"), Container(classes="omega-btn-frame"):
                yield Button(_("Choisir les logs"), id="choose-logs")
            yield Static("", id="selection-size", classes="omega-hint")
            with Horizontal(classes="omega-actions"):
                for label, _period in _PERIODS:
                    with Container(classes="omega-btn-frame"):
                        yield Button(_(PERIOD_BUTTON_LABELS[label]), id=f"period-{label}")
            yield Static(PERIOD_HINT, classes="omega-hint")
            yield BusyIndicator(id="busy")

            yield Static("", id="stats-summary")
            yield Static("", id="stats-hourly")

            yield Static(_("Thème d'export HTML"), classes="omega-subtitle")
            yield Select([(name, name) for name in EXPORT_PALETTES], value=DEFAULT_EXPORT_THEME, allow_blank=False,
                         id="theme-select")
            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Exporter JSON"), id="export-json")
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Exporter HTML"), id="export-html")
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Retour"), id="back")
        yield Footer()

    def on_mount(self) -> None:
        logs = self._available_logs()
        self._selected = [logs[0][1]] if logs else []
        self._show_selection()

    def _show_selection(self) -> None:
        widget = self.query_one("#selected-logs", Static)
        if not self._selected:
            widget.update(_("Aucun log : importez-en dans 5.1 Bibliothèque, ou épinglez-en un."))
        else:
            widget.update("\n".join(f"  {path}" for path in self._selected))
        description = describe_selection(self._selected)
        self.query_one("#selection-size", Static).update(
            _("Sélection : {description}").format(description=description) if description else "")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id or ""
        if button_id == "back":
            self.dismiss()
        elif button_id == "choose-logs":
            self.app.push_screen(
                CheckListScreen(title=_("LOGS À ANALYSER"),
                                message=_("Bibliothèque (5.1) en tête, puis vos épingles."),
                                items=self._available_logs(), checked=set(self._selected)),
                self._apply_choice,
            )
        elif button_id.startswith("period-"):
            self._compute(dict(_PERIODS)[button_id.removeprefix("period-")])
        elif button_id == "export-json":
            self._export_json()
        elif button_id == "export-html":
            self._export_html()

    def _apply_choice(self, chosen: list[str] | None) -> None:
        if chosen is None:
            return
        self._selected = list(chosen)
        self._show_selection()

    def _compute(self, period: str | None) -> None:
        if self._computing:
            self.app.notify(_("Un calcul est déjà en cours, patientez."), severity="warning")
            return
        if not self._selected:
            self.app.notify(_("Choisissez au moins un log."), severity="warning")
            return
        paths = list(self._selected)
        self._computing = True
        self._set_period_buttons_disabled(True)
        self.query_one("#busy", BusyIndicator).start(paths, period)
        self.run_worker(self._compute_async(paths, period))

    def _set_period_buttons_disabled(self, disabled: bool) -> None:
        try:
            for label, _period in _PERIODS:
                self.query_one(f"#period-{label}", Button).disabled = disabled
        except NoMatches:
            pass  # ecran deja ferme

    def _finish_computing(self) -> None:
        self._computing = False
        self._set_period_buttons_disabled(False)
        try:
            self.query_one("#busy", BusyIndicator).stop()
        except NoMatches:
            pass  # ecran deja ferme

    async def _compute_async(self, paths: list[str], period: str | None) -> None:
        try:
            self.query_one("#stats-summary", Static).update("")
            self.query_one("#stats-hourly", Static).update("")
        except NoMatches:
            self._finish_computing()
            return
        try:
            accumulator = await accumulate_in_pool(paths, period, None, self._show_progress)
        except Exception as exc:  # noqa: BLE001 - jamais planter l'appli pour un calcul de stats
            self._show_compute_error(str(exc))
            return
        result = AccessLogStatsResult(sources=paths, period=period, report=accumulator.to_report())
        self._apply_result(paths, period, result)

    def _show_progress(self, done_bytes: int, total_bytes: int, done_parts: int, total_parts: int) -> None:
        try:
            self.query_one("#busy", BusyIndicator).set_progress(done_bytes, total_bytes, done_parts, total_parts)
        except NoMatches:
            pass  # ecran deja ferme

    def _clear_summary(self) -> None:
        try:
            self.query_one("#stats-summary", Static).update("")
        except NoMatches:
            pass  # ecran deja ferme (utilisateur reparti avant la fin du calcul) — rien a mettre a jour

    def _show_compute_error(self, message: str) -> None:
        self.app.notify(_("Erreur de calcul : {message}").format(message=message), severity="error")
        self._finish_computing()
        try:
            self.query_one("#stats-summary", Static).update(_("Erreur de calcul : {message}").format(message=message))
        except NoMatches:
            pass  # ecran deja ferme (utilisateur reparti avant la fin du calcul) — rien a mettre a jour

    def _apply_result(self, paths: list[str], period: str | None, result: AccessLogStatsResult) -> None:
        self._finish_computing()
        self._result = result

        try:
            summary_widget = self.query_one("#stats-summary", Static)
            hourly_widget = self.query_one("#stats-hourly", Static)
        except NoMatches:
            return  # ecran deja ferme (utilisateur reparti avant la fin du calcul) — rien a mettre a jour

        colors = self._colors()
        summary_widget.update(self._summary_text(result, len(paths), colors))
        hourly_widget.update(self._time_text(result.report, colors))

    def _colors(self) -> dict[str, str]:
        variables = self.app.get_css_variables()
        return {
            "heading": f"bold {variables.get('secondary', '')}".strip(),
            "bar": variables.get("accent", "cyan") or "cyan",
            "peak": variables.get("error", "red") or "red",
            "good": variables.get("success", "green") or "green",
            "warn": variables.get("warning", "yellow") or "yellow",
            "bad": variables.get("error", "red") or "red",
            "info": variables.get("secondary", "cyan") or "cyan",
        }

    def _summary_text(self, result: AccessLogStatsResult, log_count: int, colors: dict[str, str]) -> Text:
        """Synthese, statuts HTTP et classements (2026-11-06, presentation du rapport d'omega-fire)."""
        report = result.report
        content = Text()
        period_label = _(_PERIOD_LABELS.get(result.period, N_("tout le fichier")))
        content.append(_("── SYNTHÈSE — {period_label}, {log_count} log(s) ──\n").format(period_label=period_label, log_count=log_count), style=colors["heading"])
        if report.total == 0:
            content.append(_(" Aucune ligne sur cette période.\n"))
            return content
        rate_style = colors["good"] if report.error_rate < 5 else (colors["warn"] if report.error_rate < 15 else colors["bad"])
        volume = "-" if report.bytes_total is None else _format_bytes(report.bytes_total)
        covered = "-" if report.first_day is None else f"{report.first_day} → {report.last_day}"
        content.append(_(" Lignes analysées   : {total}\n").format(total=report.total))
        content.append(_(" Requêtes HTTP      : {http_total}\n").format(http_total=report.http_total))
        content.append(_(" IPs uniques        : {unique_ips}\n").format(unique_ips=report.unique_ips))
        content.append(_(" Taux d'erreur      : {error_rate:.1f} %\n").format(error_rate=report.error_rate), style=rate_style)
        content.append(_(" Volume transféré   : {volume}\n").format(volume=volume))
        content.append(_(" Heure de pointe    : {peak_hour:02d}h ({peak_count} lignes)\n").format(peak_hour=report.peak_hour, peak_count=report.peak_count), style=colors["info"])
        content.append(_(" Période couverte   : {covered}\n\n").format(covered=covered))

        if report.statuses:
            content.append(_("── STATUTS HTTP ──\n"), style=colors["heading"])
            status_styles = {"2xx": colors["good"], "3xx": colors["info"], "4xx": colors["warn"], "5xx": colors["bad"],
                             "403": colors["warn"], "429": colors["warn"]}
            labels = {name: _("Refus {name}").format(name=name) if name in ("403", "429") else name
                      for name in report.statuses}
            # Largeur du plus long libelle (« Abgewiesen 403 » en allemand), jamais coupe a 10 colonnes.
            label_width = min(_LABEL_WIDTH, max(10, *(cell_len(label) for label in labels.values())))
            for name, count in report.statuses.items():
                share = count / report.http_total * 100 if report.http_total else 0
                append_gauge_line(content, labels[name], count, report.http_total, label_width=label_width,
                                  bar_width=_BAR_WIDTH, style=status_styles[name], suffix=f"  {share:5.1f} %")
            content.append("\n")

        self._append_ranking(content, _("TOP IP"), report.top_ips, colors["bar"], colors)
        if report.top_paths:
            self._append_ranking(content, _("CHEMINS DEMANDÉS"), report.top_paths, colors["bar"], colors)
            self._append_ranking(content, _("CHEMINS EN 404"), report.top_not_found, colors["warn"], colors)
        return content

    def _append_ranking(self, content: Text, title: str, items: list[RankedItem], style: str,
                        colors: dict[str, str]) -> None:
        content.append(f"── {title} ──\n", style=colors["heading"])
        if not items:
            content.append("  " + _("(aucun)") + "\n\n", style="dim")
            return
        maximum = items[0].count
        label_width = min(_LABEL_WIDTH, max(cell_len(item.value) for item in items))
        for item in items:
            suffix = "  " + _("dont {errors} en erreur").format(errors=item.errors) if item.errors else ""
            append_gauge_line(content, item.value, item.count, maximum, label_width=label_width,
                              bar_width=_BAR_WIDTH // 2, style=style, suffix=suffix)
        content.append("\n")

    def _time_text(self, report: StatsReport, colors: dict[str, str]) -> Text:
        """Repartition horaire (24 jauges, heure de pointe en couleur d'alerte) puis tendance par jour."""
        content = Text()
        if report.total == 0:
            return content
        content.append(_("── RÉPARTITION HORAIRE (24 h) ──\n"), style=colors["heading"])
        maximum = max(report.hourly)
        for hour, count in enumerate(report.hourly):
            style = colors["peak"] if count == maximum and count > 0 else colors["bar"]
            append_gauge_line(content, f"{hour:02d}h", count, maximum, label_width=4, bar_width=_BAR_WIDTH, style=style)
        content.append("\n")
        content.append(_("── TENDANCE PAR JOUR ({count} j) ──\n").format(count=len(report.daily)), style=colors["heading"])
        maximum_day = max((count for _day, count in report.daily), default=0)
        for day, count in report.daily:
            append_gauge_line(content, day, count, maximum_day, label_width=10, bar_width=_BAR_WIDTH, style=colors["bar"])
        return content

    def _export_json(self) -> None:
        if self._result is None:
            self.app.notify(_("Calculez d'abord les statistiques (choisissez une période)."), severity="warning")
            return
        payload = {"sources": self._result.sources, "period": self._result.period, **asdict(self._result.report)}
        self._write(".json", json.dumps(payload, indent=2, ensure_ascii=False, default=str), _("Export JSON : {out_path}"))

    def _export_html(self) -> None:
        if self._result is None:
            self.app.notify(_("Calculez d'abord les statistiques (choisissez une période)."), severity="warning")
            return
        report = self._result.report
        theme_name = str(self.query_one("#theme-select", Select).value)
        with translating_as(export_translation(self, self._container)):
            html = export_log_stats_html(
                sources=self._result.sources,
                period_label=_(_PERIOD_LABELS.get(self._result.period, N_("tout le fichier"))),
                report=asdict(report),
                volume="-" if report.bytes_total is None else _format_bytes(report.bytes_total),
                theme_name=theme_name,
            )
        self._write(".html", html, _("Export HTML : {out_path}"))

    def _write(self, suffix: str, content: str, message: str) -> None:
        export_dir = self._container.exports_dir
        out_path = export_dir / f"{LOG_STATS_EXPORT_PREFIX}{_export_timestamp()}{suffix}"
        try:
            export_dir.mkdir(parents=True, exist_ok=True)
            out_path.write_text(content, encoding="utf-8")
        except OSError as exc:
            self.app.notify(_("Erreur lors de l'écriture du fichier d'export : {e}").format(e=exc), severity="error")
            log_action_result(self._container, _ACTION_TITLE, status="failure", error=str(exc))
            return
        self.app.notify(message.format(out_path=out_path), timeout=8)
        log_action_result(self._container, _ACTION_TITLE, status="success")
