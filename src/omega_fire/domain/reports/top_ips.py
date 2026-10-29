# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Resultat d'une analyse Top N des IPs (5.4, version 3.5), exportable en JSON / TXT /
HTML puis rechargeable en 5.5 (retirer ces IPs des logs) : plus besoin de noter les IPs
d'un ecran a l'autre."""
from __future__ import annotations

from dataclasses import dataclass, field

# Prefixe des fichiers d'export : 5.5 propose d'abord ces fichiers-la.
TOP_IPS_EXPORT_PREFIX = "top-ips_"


@dataclass(frozen=True)
class TopIpRow:
    rank: int
    ip: str
    count: int
    percent: float | None = None      # None pour un fichier brut d'IPs (blocklist)
    volume_bytes: int | None = None


@dataclass(frozen=True)
class TopIpsReport:
    source: str
    period: str
    total_occurrences: int
    unique_ips: int
    raw_ip_file: bool
    rows: list[TopIpRow] = field(default_factory=list)

    @property
    def ips(self) -> list[str]:
        return [row.ip for row in self.rows]
