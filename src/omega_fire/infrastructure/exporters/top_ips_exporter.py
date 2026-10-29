# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecriture d'un export Top N des IPs (5.4) en JSON / TXT / HTML, et relecture de la
liste d'IPs d'un export (5.5). La relecture accepte tout export d'IPs d'omega-fire :
JSON (cle "rows" ou "ips"), sinon extraction des IPs ligne par ligne (TXT, HTML), dans
l'ordre du fichier et sans doublon."""
from __future__ import annotations

import ipaddress
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from omega_fire.domain.reports.top_ips import TopIpsReport
from omega_fire.shared.parsing import extract_ips

FORMATS = ("json", "txt", "html")
_MAX_READ_BYTES = 20 * 1024 * 1024


def write_top_ips(report: TopIpsReport, fmt: str, path: Path, generated_at: str,
                  html_exporter: Any = None, html_context: dict[str, Any] | None = None) -> Path:
    """html_context : libelles deja traduits (langue des exports), theme_name, columns et
    table_rows (cellules deja mises en forme, comme le tableau de 5.4)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "json":
        data = {
            "source": "Omega-Fire", "type": "Top IPs", "source_file": report.source,
            "period": report.period, "exported_at": generated_at,
            "total_occurrences": report.total_occurrences, "unique_ips": report.unique_ips,
            "raw_ip_file": report.raw_ip_file,
            "rows": [asdict(row) for row in report.rows],
        }
        path.write_text(json.dumps(data, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")
    elif fmt == "txt":
        lines = [
            "# Omega-Fire Top IPs Export", f"# Source : {report.source}", f"# Period : {report.period}",
            f"# Generated : {generated_at}", f"# Total : {report.total_occurrences}", "",
        ]
        # Une IP par ligne, dans l'ordre du classement (reinjectable, comme 6.1).
        lines += [row.ip for row in report.rows]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    elif fmt == "html":
        if html_exporter is None:
            raise ValueError(fmt)  # erreur de programmation : exporteur HTML manquant
        context = dict(html_context or {})
        context.update(generated_at=generated_at, total_ips=len(report.rows))
        html_exporter.export_data(context, path, template_name="top_ips.html.j2")
    else:
        raise ValueError(fmt)  # erreur de programmation : format inconnu
    return path


def _valid(candidate: str) -> str | None:
    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        return None


def read_exported_ips(path: Path) -> list[str]:
    """IPs d'un export, dans l'ordre (rang Top N), sans doublon. Leve OSError si illisible."""
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        text = handle.read(_MAX_READ_BYTES)
    if path.suffix.lower() == ".json":
        try:
            data = json.loads(text)
        except ValueError:
            data = None
        if isinstance(data, dict):
            if isinstance(data.get("rows"), list):
                values = [row.get("ip", "") for row in data["rows"] if isinstance(row, dict)]
            elif isinstance(data.get("ips"), list):
                values = [str(value) for value in data["ips"]]
            else:
                values = []
            return list(dict.fromkeys(ip for ip in map(_valid, values) if ip))
    found: list[str] = []
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            continue
        for candidate in extract_ips(line):
            ip = _valid(candidate)
            if ip:
                found.append(ip)
    return list(dict.fromkeys(found))
