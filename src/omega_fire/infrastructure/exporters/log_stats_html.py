# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Export HTML des statistiques des logs (6.5, 2026-11-09) : MEME schema qu'omega-log / omega-serv
(gabarit porte d'omega-log : access_log_stats_report.html.j2 -> log_stats_report.html.j2, seul le nom
du logiciel change). Logs seulement : les bans et l'etat du pare-feu restent dans 8.3 / 8.4.

Palettes : omega_lib.theme.policies (les memes themes d'export que les autres outils omega)."""
from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from omega_lib.theme.policies import DEFAULT_EXPORT_THEME, EXPORT_PALETTES, Palette

from omega_fire.shared.i18n import _, html_dir, html_lang

LOG_STATS_EXPORT_PREFIX = "logs-stats_"
"""Prefixe des fichiers (catalogue des exports, 6.6)."""

_TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "domain" / "reports" / "templates"
_env = Environment(loader=FileSystemLoader(_TEMPLATES_DIR), autoescape=select_autoescape(["html", "j2"]))
# Texte des gabarits traduit par `_` dans la langue active (celle des exports sous translating_as).
_env.globals.update(_=_, html_lang=html_lang, html_dir=html_dir)


def resolve_export_palette(theme_name: str) -> Palette:
    """Un nom inconnu se replie sur le theme par defaut (repris d'omega-log / omega-serv)."""
    return EXPORT_PALETTES.get(theme_name, EXPORT_PALETTES[DEFAULT_EXPORT_THEME])


def export_log_stats_html(*, sources: Sequence[str], period_label: str, report: dict, volume: str,
                          theme_name: str = DEFAULT_EXPORT_THEME) -> str:
    """`report` = dataclasses.asdict(StatsReport)."""
    template = _env.get_template("log_stats_report.html.j2")
    return template.render(
        sources=sources,
        period_label=period_label,
        report=report,
        volume=volume,
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        palette=resolve_export_palette(theme_name),
    )
