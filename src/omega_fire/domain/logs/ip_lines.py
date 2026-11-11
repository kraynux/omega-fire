# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Reperage des lignes de log qui contiennent une IP donnee (5.5 Supprimer une IP des logs, 5.4 Top IP).

Deplace depuis interfaces/tui/screens/remove_ip_from_log_screen.py le 2026-11-10 : la reecriture du
fichier (infrastructure/storage/files/log_ip_removal.py) en a besoin, et l'infrastructure n'importe
jamais l'interface."""
from __future__ import annotations

import re


def split_lines_by_ips(lines: list[str], ips: list[str]) -> tuple[dict[str, int], list[str]]:
    """(lignes retirees par IP, lignes conservees). Une ligne qui contient plusieurs des
    IPs n'est comptee qu'une fois, pour la premiere IP de la liste."""
    patterns = [(ip, re.compile(rf"(?<![\w.:]){re.escape(ip)}(?![\w:]|\.\d)")) for ip in ips]
    counts = {ip: 0 for ip in ips}
    kept: list[str] = []
    for line in lines:
        for ip, pattern in patterns:
            if pattern.search(line):
                counts[ip] += 1
                break
        else:
            kept.append(line)
    return counts, kept
