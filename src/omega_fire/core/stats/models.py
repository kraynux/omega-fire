# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class LogEntry:
    """Représente un événement individuel extrait d'un log ou de la base SQL."""
    timestamp: datetime
    jail: str
    action: str
    ip: str
    message: Optional[str] = None


@dataclass
class JailStat:
    """Statistiques agrégées pour une Jail spécifique."""
    name: str
    total_bans: int
    is_active: bool = True
    percentage: float = 0.0


@dataclass
class IpStat:
    """Statistiques agrégées pour une adresse IP."""
    ip: str
    total_bans: int
    last_ban: datetime
    country: str = "Inconnu"


@dataclass
class LogStatsSummary:
    """Synthèse complète des métriques pour une période donnée."""
    period_label: str
    start_date: datetime
    end_date: datetime
    total_events: int = 0
    total_bans: int = 0
    peak_hour: str = "--:--"
    peak_count: int = 0
    top_jail_name: str = "Aucun"
    top_jails: List[JailStat] = field(default_factory=list)
    top_ips: List[IpStat] = field(default_factory=list)
    hourly_series: List[int] = field(default_factory=lambda: [0] * 24)
    data_source: str = "Inconnue"
