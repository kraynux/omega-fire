# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
# Porte d'omega-log (domain/logs/stats_report.py) le 2026-11-09 (OMEGA-FIRE_PLAN_LOGS_NIVEAU_SERV_LOG.md) : garder identique a la source.
"""Rapport de statistiques (2026-11-06, retour utilisateur : « le rendu est pauvre, l'export est light ;
omega-fire propose des statistiques exportables 7 et 30 jours avec des jauges sur les horaires, des
graphismes ») - meme presentation que le rapport periodique d'omega-fire (domain/reports/templates/
stats_report.html.j2) : synthese en cartes, repartition horaire, tendance par jour, puis le contenu propre
a des logs : statuts HTTP, top IP, chemins demandes, chemins en 404.

Pur domaine : calcule depuis des LogEntry deja lus. Aucune valeur inventee : le volume transfere
vaut None si le log ne donne pas de taille, les statuts et les chemins restent vides hors log HTTP. Taux
d'erreur = meme definition que le viewer Simple (4xx+5xx parmi les lignes HTTP, sinon lignes de niveau
erreur)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from omega_fire.domain.log_stats.models import LogEntry

TOP_SIZE = 10
MAX_TREND_DAYS = 92
"""Tendance par jour : au plus les 92 derniers jours couverts (un « Tout » sur des annees resterait
lisible) ; 7 j et 30 j tiennent entiers."""
STATUS_GROUPS: tuple[str, ...] = ("2xx", "3xx", "4xx", "5xx")


@dataclass(frozen=True)
class RankedItem:
    value: str
    count: int
    errors: int = 0
    """Lignes 4xx/5xx de cette IP ou de ce chemin (0 hors log HTTP)."""


@dataclass
class StatsReport:
    total: int = 0
    http_total: int = 0
    unique_ips: int = 0
    error_rate: float = 0.0
    bytes_total: int | None = None
    first_day: date | None = None
    last_day: date | None = None
    peak_hour: int | None = None
    peak_count: int = 0
    hourly: list[int] = field(default_factory=lambda: [0] * 24)
    daily: list[tuple[str, int]] = field(default_factory=list)
    """(AAAA-MM-JJ, lignes) pour chaque jour de la periode couverte, jours vides compris."""
    statuses: dict[str, int] = field(default_factory=dict)
    """2xx, 3xx, 4xx, 5xx, puis 403 et 429 (refus) - vide hors log HTTP."""
    top_ips: list[RankedItem] = field(default_factory=list)
    top_paths: list[RankedItem] = field(default_factory=list)
    top_not_found: list[RankedItem] = field(default_factory=list)


def build_stats_report(entries: list[LogEntry], *, top_size: int = TOP_SIZE) -> StatsReport:
    """Rapport d'une liste de lignes deja lues - calcule par l'accumulateur en flux (stats_accumulator.py),
    seul endroit ou ce calcul est ecrit."""
    from omega_fire.domain.log_stats.stats_accumulator import accumulate

    return accumulate(entries).to_report(top_size=top_size)
