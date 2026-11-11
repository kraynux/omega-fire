# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
# Porte d'omega-log (domain/logs/stats_accumulator.py) le 2026-11-09 (OMEGA-FIRE_PLAN_LOGS_NIVEAU_SERV_LOG.md) : garder identique a la source.
"""Accumulateur de statistiques en flux (2026-11-06, retour utilisateur : « il y a des logs plus gros de
serveurs ») : chaque ligne analysee est comptee puis oubliee - plus jamais la liste complete des lignes en
memoire (415 609 lignes = plus de 300 Mo d'objets avant). Deux accumulateurs se FUSIONNENT : un fichier
decoupe en morceaux est analyse sur plusieurs coeurs, chaque morceau rend son accumulateur, la somme donne
exactement le meme resultat qu'une lecture d'un bloc.

Sert le rapport de Statistiques (`to_report`) et le top IP de « Voir et traiter IP » (`top_ips`).
Pur domaine, aucune I/O."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from omega_fire.domain.log_stats.models import LogEntry, TopIP
from omega_fire.domain.log_stats.stats_report import (
    MAX_TREND_DAYS,
    STATUS_GROUPS,
    TOP_SIZE,
    RankedItem,
    StatsReport,
)


def _is_http_error(status: int | None) -> bool:
    return status is not None and status >= 400


@dataclass
class StatsAccumulator:
    total: int = 0
    error_level: int = 0
    hourly: list[int] = field(default_factory=lambda: [0] * 24)
    per_day: Counter[date] = field(default_factory=Counter)
    statuses: Counter[int] = field(default_factory=Counter)
    bytes_total: int = 0
    has_size: bool = False
    ips: Counter[str] = field(default_factory=Counter)
    ip_errors: Counter[str] = field(default_factory=Counter)
    ip_first: dict[str, datetime] = field(default_factory=dict)
    ip_last: dict[str, datetime] = field(default_factory=dict)
    ip_services: dict[str, set[str]] = field(default_factory=dict)
    paths: Counter[str] = field(default_factory=Counter)
    path_errors: Counter[str] = field(default_factory=Counter)
    not_found: Counter[str] = field(default_factory=Counter)

    def add(self, entry: LogEntry) -> None:
        self.total += 1
        if entry.is_error():
            self.error_level += 1
        moment = entry.timestamp
        self.hourly[moment.hour] += 1
        self.per_day[moment.date()] += 1
        status = entry.http_status
        if status is not None:
            self.statuses[status] += 1
        if entry.bytes_sent is not None:
            self.bytes_total += entry.bytes_sent
            self.has_size = True
        ip = entry.ip
        if ip:
            self.ips[ip] += 1
            if _is_http_error(status):
                self.ip_errors[ip] += 1
            if ip not in self.ip_first or moment < self.ip_first[ip]:
                self.ip_first[ip] = moment
            if ip not in self.ip_last or moment > self.ip_last[ip]:
                self.ip_last[ip] = moment
            if entry.service:
                self.ip_services.setdefault(ip, set()).add(entry.service)
        if entry.http_path:
            path = entry.http_path.split("?", 1)[0]
            self.paths[path] += 1
            if _is_http_error(status):
                self.path_errors[path] += 1
            if status == 404:
                self.not_found[path] += 1

    def merge(self, other: StatsAccumulator) -> None:
        self.total += other.total
        self.error_level += other.error_level
        self.hourly = [mine + theirs for mine, theirs in zip(self.hourly, other.hourly)]
        for name in ("per_day", "statuses", "ips", "ip_errors", "paths", "path_errors", "not_found"):
            getattr(self, name).update(getattr(other, name))
        self.bytes_total += other.bytes_total
        self.has_size = self.has_size or other.has_size
        for ip, moment in other.ip_first.items():
            if ip not in self.ip_first or moment < self.ip_first[ip]:
                self.ip_first[ip] = moment
        for ip, moment in other.ip_last.items():
            if ip not in self.ip_last or moment > self.ip_last[ip]:
                self.ip_last[ip] = moment
        for ip, services in other.ip_services.items():
            self.ip_services.setdefault(ip, set()).update(services)

    def to_report(self, *, top_size: int = TOP_SIZE) -> StatsReport:
        report = StatsReport(total=self.total, hourly=list(self.hourly))
        if not self.total:
            return report
        peak = max(range(24), key=lambda hour: self.hourly[hour])
        report.peak_hour, report.peak_count = peak, self.hourly[peak]

        report.first_day, report.last_day = min(self.per_day), max(self.per_day)
        start = max(report.first_day, report.last_day - timedelta(days=MAX_TREND_DAYS - 1))
        report.daily = [
            ((start + timedelta(days=offset)).isoformat(), self.per_day.get(start + timedelta(days=offset), 0))
            for offset in range((report.last_day - start).days + 1)
        ]

        report.http_total = sum(self.statuses.values())
        if report.http_total:
            for group in STATUS_GROUPS:
                first = int(group[0]) * 100
                report.statuses[group] = sum(n for status, n in self.statuses.items() if first <= status < first + 100)
            report.statuses["403"] = self.statuses.get(403, 0)
            report.statuses["429"] = self.statuses.get(429, 0)
            report.error_rate = (report.statuses["4xx"] + report.statuses["5xx"]) / report.http_total * 100
        else:
            report.error_rate = self.error_level / self.total * 100

        report.bytes_total = self.bytes_total if self.has_size else None
        report.unique_ips = len(self.ips)
        report.top_ips = _ranked(self.ips, self.ip_errors, top_size)
        report.top_paths = _ranked(self.paths, self.path_errors, top_size)
        report.top_not_found = _ranked(self.not_found, Counter(), top_size)
        return report

    def top_ips(self, n: int = 10) -> list[TopIP]:
        """Meme forme et meme ordre que `analytics.compute_top_ips` (ecran « Voir et traiter IP »)."""
        return [
            TopIP(ip=ip, count=count, first_seen=self.ip_first.get(ip), last_seen=self.ip_last.get(ip),
                  services=sorted(self.ip_services.get(ip, set())), http_errors=self.ip_errors.get(ip, 0))
            for ip, count in sorted(self.ips.items(), key=lambda item: (-item[1], item[0]))[:n]
        ]


def _ranked(counts: Counter[str], errors: Counter[str], size: int) -> list[RankedItem]:
    return [RankedItem(value, count, errors.get(value, 0)) for value, count in counts.most_common(size)]


def accumulate(entries: list[LogEntry]) -> StatsAccumulator:
    accumulator = StatsAccumulator()
    for entry in entries:
        accumulator.add(entry)
    return accumulator
