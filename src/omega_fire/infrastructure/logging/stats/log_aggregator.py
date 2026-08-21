# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
import re
import subprocess
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from omega_fire.core.stats.models import IpStat, JailStat, LogEntry, LogStatsSummary
from omega_fire.infrastructure.logging.stats.file_collector import FileLogCollector
from omega_fire.infrastructure.logging.stats.sqlite_collector import SqliteLogCollector


class LogAggregator:
    """Orchestrateur qui combine les collecteurs et génère la synthèse des statistiques."""

    PERIOD_MAP = {
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
    }

    def __init__(
        self,
        sqlite_collector: Optional[SqliteLogCollector] = None,
        file_collector: Optional[FileLogCollector] = None,
    ):
        self.sqlite_collector = sqlite_collector or SqliteLogCollector()
        self.file_collector = file_collector or FileLogCollector()

    def _parse_kernel_firewall_logs(self, since: datetime) -> List[LogEntry]:
        """Lit et parse les événements iptables et nftables depuis journalctl ou les fichiers du noyau."""
        entries: List[LogEntry] = []

        fw_regex = re.compile(
            r'(?P<fw_type>IPT|NFT|BLOCK|DROP|REJECT|FW-BAN)'
            r'.*?SRC=(?P<src>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
            r'(?:.*?DPT=(?P<dpt>\d+))?'
        )

        lines: List[str] = []

        # 1. Extraction via journalctl
        try:
            res = subprocess.run(
                ["journalctl", "-k", "--no-pager"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if res.returncode == 0 and res.stdout:
                lines = res.stdout.splitlines()
        except Exception:
            pass

        # 2. Fallback sur fichiers logs kernel
        if not lines:
            for log_path in [
                Path("/var/log/kern.log"),
                Path("/var/log/syslog"),
                Path("/var/log/messages"),
            ]:
                if log_path.exists():
                    try:
                        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                            lines.extend(f.readlines()[-2000:])
                    except Exception:
                        pass

        # 3. Conversion en LogEntry
        for line in lines:
            match = fw_regex.search(line)
            if match:
                data = match.groupdict()
                src_ip = data.get("src")
                fw_type = data.get("fw_type", "FW")
                dpt = data.get("dpt")

                if not src_ip:
                    continue

                if "NFT" in fw_type or "nft" in line.lower():
                    jail_name = f"nftables (port {dpt})" if dpt else "nftables-drop"
                else:
                    jail_name = f"iptables (port {dpt})" if dpt else "iptables-drop"

                entries.append(
                    LogEntry(
                        timestamp=datetime.now(),
                        ip=src_ip,
                        jail=jail_name,
                        action="Ban",
                    )
                )

        return entries

    def _collect_entries(self, start_date: datetime) -> Tuple[List[LogEntry], str]:
        """Collecte les entrées de log depuis toutes les sources
        disponibles (SQLite en priorité, fallback fichiers, complément
        logs noyau), avec identification de la source effectivement
        utilisée.

        Extrait de get_summary() pour être réutilisé par
        get_daily_trend() sans dupliquer la logique de collecte.
        """
        entries: List[LogEntry] = []
        data_source = "Inconnue"

        # 1. Tentative d'extraction via SQLite
        if self.sqlite_collector.is_available():
            entries = self.sqlite_collector.fetch_bans(since=start_date)
            data_source = "SQLite"

        # 2. Fallback / Complément via les fichiers logs
        if not entries:
            entries = self.file_collector.fetch_entries(since=start_date)
            data_source = "Fichiers Logs"

        # 2b. Ajout des événements pare-feu (iptables / nftables)
        fw_entries = self._parse_kernel_firewall_logs(since=start_date)
        if fw_entries:
            entries.extend(fw_entries)
            if data_source == "Inconnue":
                data_source = "Pare-feu Système"

        return entries, data_source

    def get_summary(self, period_code: str = "24h") -> LogStatsSummary:
        """Génère un résumé complet des statistiques pour la période demandée."""
        end_date = datetime.now()
        delta = self.PERIOD_MAP.get(period_code, timedelta(hours=24))
        start_date = end_date - delta

        entries, data_source = self._collect_entries(start_date)

        if not entries:
            return LogStatsSummary(
                period_label=period_code,
                start_date=start_date,
                end_date=end_date,
                data_source=data_source,
            )

        # 3. Calculs et agrégations
        total_events = len(entries)
        bans_only = [e for e in entries if e.action in ("Ban", "Restore")]
        total_bans = len(bans_only)

        # Agrégation par Jail
        jail_counts = Counter(e.jail for e in bans_only)
        active_jails_set = set(self.sqlite_collector.get_active_jails())
        top_jails: List[JailStat] = []

        for jail_name, count in jail_counts.most_common(10):
            pct = (count / total_bans * 100.0) if total_bans > 0 else 0.0
            top_jails.append(
                JailStat(
                    name=jail_name,
                    total_bans=count,
                    is_active=(
                        jail_name in active_jails_set if active_jails_set else True
                    ),
                    percentage=round(pct, 1),
                )
            )

        top_jail_name = top_jails[0].name if top_jails else "Aucun"

        # Agrégation par IP
        ip_data: Dict[str, Dict] = {}
        for entry in bans_only:
            if entry.ip not in ip_data:
                ip_data[entry.ip] = {"count": 0, "last_ban": entry.timestamp}
            ip_data[entry.ip]["count"] += 1
            if entry.timestamp > ip_data[entry.ip]["last_ban"]:
                ip_data[entry.ip]["last_ban"] = entry.timestamp

        sorted_ips = sorted(
            ip_data.items(), key=lambda x: x[1]["count"], reverse=True
        )[:10]
        top_ips: List[IpStat] = [
            IpStat(
                ip=ip,
                total_bans=info["count"],
                last_ban=info["last_ban"],
            )
            for ip, info in sorted_ips
        ]

        # Agrégation par série temporelle (24 créneaux)
        hourly_series = [0] * 24
        for entry in bans_only:
            hour_idx = entry.timestamp.hour
            hourly_series[hour_idx] += 1

        peak_count = max(hourly_series) if hourly_series else 0
        peak_hour_idx = hourly_series.index(peak_count) if peak_count > 0 else 0
        peak_hour_str = f"{peak_hour_idx:02d}h00"

        return LogStatsSummary(
            period_label=period_code,
            start_date=start_date,
            end_date=end_date,
            total_events=total_events,
            total_bans=total_bans,
            peak_hour=peak_hour_str,
            peak_count=peak_count,
            top_jail_name=top_jail_name,
            top_jails=top_jails,
            top_ips=top_ips,
            hourly_series=hourly_series,
            data_source=data_source,
        )

    _DAY_LABELS_FR = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]

    def get_daily_trend(self, period_code: str = "7d") -> List[Tuple[str, int]]:
        """Agrège les bans par jour (période '7d') ou par bloc de 7 jours
        glissants (période '30d'), pour le graphique de tendance des
        rapports 8.3/8.4 (interfaces/cli/renderers/stats/daily_trend_chart.py).

        Distinct de hourly_series (LogStatsSummary), qui cumule
        l'activité par heure-de-journée sur toute la période sans
        jamais montrer si l'activité progresse ou régresse jour après
        jour — c'est précisément ce que cette méthode apporte.

        Args:
            period_code: '7d' pour un bucket quotidien (7 points),
                '30d' pour un bucket hebdomadaire glissant (4-5 points).
                Toute autre valeur retombe sur un bucket quotidien.

        Returns:
            Liste de tuples (label, count), triée chronologiquement,
            prête pour render_daily_trend_chart().
        """
        end_date = datetime.now()
        delta = self.PERIOD_MAP.get(period_code, timedelta(days=7))
        start_date = end_date - delta

        entries, _ = self._collect_entries(start_date)
        bans_only = [e for e in entries if e.action in ("Ban", "Restore")]

        bucket_days = 7 if period_code == "30d" else 1

        buckets: List[Tuple[datetime, datetime]] = []
        cursor = start_date
        while cursor < end_date:
            bucket_end = min(cursor + timedelta(days=bucket_days), end_date)
            buckets.append((cursor, bucket_end))
            cursor = bucket_end

        result: List[Tuple[str, int]] = []
        for bucket_start, bucket_end in buckets:
            count = sum(
                1 for e in bans_only
                if bucket_start <= e.timestamp < bucket_end
            )
            if bucket_days == 1:
                label = f"{self._DAY_LABELS_FR[bucket_start.weekday()]} {bucket_start.day:02d}"
            else:
                last_day = bucket_end - timedelta(seconds=1)
                label = f"{bucket_start.strftime('%d/%m')}-{last_day.strftime('%d/%m')}"
            result.append((label, count))

        return result

       
# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Orchestrateur qui combine plusieurs collecteurs de logs (SQLite
#   fail2ban natif en priorité, fichiers fail2ban.log en fallback,
#   logs noyau iptables/nftables en complément) et génère une synthèse
#   agrégée des statistiques de bannissement sur une période donnée.
# - Alimente les menus 5.8 (dashboard interactif live) et 8.3/8.4
#   (rapports statistiques statiques 7j/30j).
#
# Pourquoi dans infrastructure/logging/stats/ (charte) :
# - Fait de l'I/O réel (SQLite en lecture, fichiers, subprocess
#   journalctl) — ne peut pas vivre dans domain/.
# - Coordonne des collecteurs eux-mêmes en infrastructure/ (
#   sqlite_collector.py, file_collector.py) — cohérent d'être au même
#   niveau qu'eux plutôt que dans application/.
# - Retourne des dataclasses pures (LogStatsSummary, JailStat, IpStat,
#   core/stats/models.py) que interfaces/ et application/ consomment
#   sans jamais connaître le mécanisme de collecte sous-jacent.
#
# Ce qu'il ne contient PAS :
# ❌ Pas de rendu Rich/HTML (délégué à interfaces/cli/renderers/stats/
#    et domain/reports/ + infrastructure/exporters/html_exporter.py)
# ❌ Pas de décision d'affichage (quelle période, quel format) — reçoit
#    period_code en paramètre, ne décide jamais lui-même
# ❌ Pas de persistance (lecture seule sur toutes ses sources)
#
# Points clés :
# - PERIOD_MAP : "24h" / "7d" / "30d" — les trois fenêtres temporelles
#   supportées par tout le mécanisme de stats du projet
# - _parse_kernel_firewall_logs() : lit journalctl -k (fallback fichiers
#   kern.log/syslog/messages) pour détecter des règles iptables/nftables
#   avec action LOG — LIMITE CONNUE : horodate systématiquement à
#   datetime.now() (pas l'heure réelle de l'événement), donc fausse la
#   répartition temporelle si cette source produit des entrées. Très
#   probablement vide en pratique : aucune règle créée par Omega-Fire
#   (3.1/3.4) n'utilise l'action LOG à ce jour. Non corrigé
#   volontairement (hors périmètre du chantier 8.3/8.4).
# - _collect_entries(start_date) : collecte brute mutualisée (SQLite →
#   fallback fichiers → complément logs noyau), extraite pour être
#   réutilisée par get_summary() ET get_daily_trend() sans dupliquer la
#   logique de priorité des sources.
# - get_summary(period_code) : synthèse complète — totaux, heure de pic,
#   top jails, top IPs, hourly_series (répartition par HEURE-DE-JOURNÉE,
#   cumulée sur toute la période, jamais jour-par-jour).
# - get_daily_trend(period_code) : agrégation JOUR-PAR-JOUR (période
#   "7d", 7 points) ou par BLOC DE 7 JOURS GLISSANTS (période "30d",
#   4-5 points) — répond à "l'activité augmente-t-elle dans le temps",
#   question à laquelle hourly_series ne répond jamais. Ajoutée pour
#   les rapports 8.3/8.4 (interfaces/cli/renderers/stats/
#   daily_trend_chart.py), réutilise _collect_entries() sans dupliquer
#   la collecte.
# - SqliteLogCollector (infrastructure/logging/stats/sqlite_collector.py) :
#   source PRIORITAIRE et FIABLE — lit directement
#   /var/lib/fail2ban/fail2ban.sqlite3 en lecture seule, jamais la
#   table 'bans' du projet Omega-Fire (celle-ci reste vide, non
#   alimentée par action_2_1_ban_ip/action_2_3_unban_ip — dette
#   technique connue, sans impact ici puisque cette classe ne la lit
#   jamais).
# - FileLogCollector (infrastructure/logging/stats/file_collector.py) :
#   fallback si SQLite indisponible — parse fail2ban.log et ses
#   archives .gz tournées.
#
# Comment il sera utilisé (aperçu) :
# - interfaces/cli/views/log_stats_view.py (menu 5.8) : dashboard Live
#   interactif, bascule entre périodes via touches [1]/[2]/[3]
# - application/queries/build_stats_report.py (menus 8.3/8.4, à venir) :
#   appelle get_summary() ET get_daily_trend() pour construire un
#   rapport statique multi-sections, combiné à AuditLogger (gestion) et
#   PersistencePort.list_snapshots() (évolution des règles) — sources
#   que ce fichier ne connaît pas et ne doit jamais connaître.
#---------------------------------------------------------------------->
