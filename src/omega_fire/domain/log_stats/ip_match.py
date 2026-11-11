# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
# Porte d'omega-log (domain/logs/ip_match.py) le 2026-11-09 (OMEGA-FIRE_PLAN_LOGS_NIVEAU_SERV_LOG.md) : garder identique a la source.
"""Correspondance d'une adresse IP dans une ligne de log, quel que soit son format (2026-11-07).

Une seule regle pour COMPTER (recherche manuelle de « Voir et Traiter IP ») et pour RETIRER
(`application/use_cases/process_ip.py`) : le nombre affiche est exactement celui des lignes retirees.
Repris tel quel d'omega-serv (domain/logs/ip_match.py, portage 2026-11-07).

CORRIGE : la limite de mot `\\b` utilisee jusqu'ici ne trouvait jamais une IPv6 terminee par `::`
(`2a03:2880:f800:15::`) - ni le `:` final ni l'espace suivant ne sont des caracteres de mot, il n'y a donc
pas de limite. Les limites sont maintenant explicites : une IP n'est jamais le morceau d'une IP plus longue
(1.1.1.1 ne trouve pas 1.1.1.11 ni 21.1.1.1), un port apres une IPv4 (1.1.1.1:443) est accepte."""
from __future__ import annotations

import ipaddress
import re


def normalize_ip(text: str) -> str | None:
    """Forme ecrite dans les logs (IPv6 compressee, en minuscules), ou None si ce n'est pas une adresse IP."""
    try:
        return str(ipaddress.ip_address(text.strip()))
    except ValueError:
        return None


def ip_line_pattern(ip: str) -> re.Pattern[str]:
    escaped = re.escape(ip)
    if ":" in ip:  # IPv6 : ni chiffre hexadecimal ni `:` de part et d'autre
        return re.compile(rf"(?<![\w:]){escaped}(?![\w:])")
    # IPv4 : ni chiffre ni point avant ; apres, ni chiffre ni « .chiffre » (une IP plus longue)
    return re.compile(rf"(?<![\w.]){escaped}(?![\w]|\.\d)")


def line_contains_ip(line: str, ip: str, pattern: re.Pattern[str]) -> bool:
    """`ip in line` d'abord : presque toutes les lignes sont ecartees sans expression reguliere."""
    return ip in line and pattern.search(line) is not None
