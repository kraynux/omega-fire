# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Catalogue des fichiers exportes (version 3.5) : 6.6 « Voir tous les exports » et le
chargement d'une liste d'IPs en 5.5. Parcourt le dossier d'exports (Reglages -> Exports,
var/exports/ par defaut) et, dans var/blocklist/, les seuls exports de 6.1
(export-blacklist*) — jamais les blocklists de travail elles-memes."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from omega_fire.domain.reports.top_ips import TOP_IPS_EXPORT_PREFIX

# Prefixe de nom -> type d'export (cle stable, libelle traduit cote interface).
_KINDS: tuple[tuple[str, str], ...] = (
    (TOP_IPS_EXPORT_PREFIX, "top_ips"),
    ("export-blacklist", "blacklist"),
    ("rules-nft-ipt_", "rules"),
    ("audit-rapport_", "audit"),
    ("f2b-rapport_", "f2b"),
    ("list-", "jail"),
    ("rapport_systeme_", "state"),
    ("stats_report_", "stats"),
    ("conntrack-rapport_", "conntrack"),
    ("guide-aide_", "guide"),
    ("logs-stats_", "log_stats"),
)
VIEWABLE_SUFFIXES = (".json", ".txt", ".html", ".htm", ".csv", ".log")


@dataclass(frozen=True)
class ExportFile:
    path: Path
    kind: str          # cle de _KINDS, "other" sinon
    size: int
    mtime: float

    @property
    def is_html(self) -> bool:
        return self.path.suffix.lower() in (".html", ".htm")


def export_kind(name: str) -> str:
    for prefix, kind in _KINDS:
        if name.startswith(prefix):
            return kind
    return "other"


def _scan(directory: Path, only_prefix: str | None = None) -> list[ExportFile]:
    found: list[ExportFile] = []
    try:
        entries = list(directory.iterdir())
    except OSError:
        return found
    for entry in entries:
        if only_prefix and not entry.name.startswith(only_prefix):
            continue
        try:
            if not entry.is_file():
                continue
            stat = entry.stat()
        except OSError:
            continue
        found.append(ExportFile(entry, export_kind(entry.name), stat.st_size, stat.st_mtime))
    return found


def list_exports(exports_dir: Path, blocklist_dir: Path | None = None) -> list[ExportFile]:
    """Plus recents d'abord."""
    files = _scan(exports_dir)
    if blocklist_dir is not None and blocklist_dir.resolve() != exports_dir.resolve():
        files += _scan(blocklist_dir, only_prefix="export-blacklist")
    return sorted(files, key=lambda f: f.mtime, reverse=True)


def ip_list_exports(exports_dir: Path, blocklist_dir: Path | None = None) -> list[ExportFile]:
    """Exports qui contiennent une liste d'IPs (5.5) : Top N d'abord, puis blacklist et
    jails ; les plus recents d'abord dans chaque groupe."""
    order = {"top_ips": 0, "blacklist": 1, "jail": 2}
    files = [f for f in list_exports(exports_dir, blocklist_dir)
             if f.kind in order and f.path.suffix.lower() in (".json", ".txt", ".html")]
    return sorted(files, key=lambda f: (order[f.kind], -f.mtime))
