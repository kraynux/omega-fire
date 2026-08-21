# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Cross-jail IP duplicate detection (menu 6.4).

An IP present in multiple jails at once isn't necessarily an anomaly
(e.g. the same attacker triggering both sshd and sshd-custom), but
it's useful information — surfacing the top 20 most-shared IPs.
"""
from __future__ import annotations

from typing import Any

from omega_fire.application.queries.f2b_report.models import DuplicateIp

MAX_DUPLICATE_IPS_DISPLAYED = 20


def collect_duplicate_ips(jails_info: list[Any]) -> list[DuplicateIp]:
    """Find IPs currently banned in more than one jail simultaneously.

    Perf note (2026-08-16) : appelait auparavant sa propre boucle
    list_jails() + get_jail_status() par jail — un fail2ban-client
    supplémentaire par jail, EN PLUS de celui déjà fait par
    jails_section.py::collect_jails_detail() pour le même rapport.
    Prend maintenant directement la liste JailInfo déjà récupérée une
    seule fois par report_builder.py (list_jails_info(), banned_ips
    déjà peuplé) — zéro appel fail2ban-client ici désormais, calcul
    purement en mémoire.

    Args:
        jails_info: Liste de JailInfo déjà résolue (ports/fail2ban.py),
            typiquement le résultat de Fail2banAdapter.list_jails_info().

    Returns:
        List of DuplicateIp, sorted by jail_count descending, capped
        at MAX_DUPLICATE_IPS_DISPLAYED. Empty list if no IP is shared
        across jails.
    """
    jails_by_ip: dict[str, list[str]] = {}

    for info in jails_info:
        for ip in info.banned_ips:
            jails_by_ip.setdefault(str(ip), []).append(info.name)

    duplicates = [
        DuplicateIp(ip=ip, jails=jails)
        for ip, jails in jails_by_ip.items()
        if len(jails) > 1
    ]

    duplicates.sort(key=lambda d: d.jail_count, reverse=True)

    return duplicates[:MAX_DUPLICATE_IPS_DISPLAYED]


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Détecte les IPs présentes simultanément dans plusieurs jails
#   (section "Top IPs multi-jails" du rapport 6.4).
#
# Pourquoi dans application/queries/f2b_report/ (charte) :
# - Lecture seule, calcul en mémoire pur — ne touche plus
#   Fail2banAdapter directement depuis le 2026-08-16 (voir note perf
#   ci-dessus), reçoit les JailInfo déjà résolus par l'appelant.
#
# Points clés :
# - Ce n'est pas une anomalie en soi (la même IP peut légitimement
#   déclencher plusieurs jails) — présenté comme information, pas
#   comme un avertissement (contrairement aux anomalies de 6.3).
# - Plafonné à 20 (MAX_DUPLICATE_IPS_DISPLAYED), trié par nombre de
#   jails décroissant — les recoupements les plus larges en premier.
#
# Comment il sera utilisé :
# - report_builder.py appelle collect_duplicate_ips() pour peupler
#   F2bReportData.duplicate_ips.
#----------------------------------------------------------------------
