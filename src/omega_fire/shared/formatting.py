# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Formateurs génériques (taille, durée, nombres)."""

from __future__ import annotations

from datetime import timedelta


def human_bytes(value: int, *, binary: bool = True) -> str:
    """Formate un nombre d'octets en taille lisible (Ko, Mo, Go...).

    Args:
        value: nombre d'octets (>= 0).
        binary: si True, utilise des puissances de 1024 (KiB, MiB...),
                sinon des puissances de 1000 (KB, MB...).
    """
    if value < 0:
        raise ValueError("human_bytes attend une valeur positive")
    base = 1024 if binary else 1000
    units = (
        ["B", "KiB", "MiB", "GiB", "TiB"]
        if binary
        else ["B", "KB", "MB", "GB", "TB"]
    )
    size = float(value)
    for unit in units[:-1]:
        if size < base:
            return f"{size:.1f} {unit}"
        size /= base
    return f"{size:.1f} {units[-1]}"


def human_duration(seconds: float) -> str:
    """Formate une durée en secondes sous forme lisible (ex: '2h 15m 03s')."""
    if seconds < 0:
        raise ValueError("human_duration attend une valeur positive")
    td = timedelta(seconds=int(seconds))
    total = int(td.total_seconds())
    days, rem = divmod(total, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    parts: list[str] = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    parts.append(f"{secs:02d}s")
    return " ".join(parts)


def human_count(value: int) -> str:
    """Formate un grand nombre avec séparateurs (ex: 12345 -> '12 345')."""
    return f"{value:,}".replace(",", " ")


def pad_right(value: str, width: int, fillchar: str = " ") -> str:
    """Aligne à gauche sur `width` caractères."""
    return value.ljust(width, fillchar)


def truncate(value: str, max_length: int, suffix: str = "…") -> str:
    """Tronque une chaîne à `max_length` en ajoutant un suffixe si nécessaire."""
    if len(value) <= max_length:
        return value
    if max_length <= len(suffix):
        return suffix[:max_length]
    return value[: max_length - len(suffix)] + suffix

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Fournit des formateurs génériques pour afficher des valeurs brutes de
#   manière lisible : tailles (Ko/Mo/Go), durées (2h 15m 03s), nombres (12 345).
# - Fournit des helpers d'alignement et de troncature pour le rendu texte.
#
# Pourquoi dans shared/ (charte) :
# - Ce sont des formatages purement techniques, non métier
# - Utilisés par domain/reports/ (contenu logique), infrastructure/exporters/
#   (JSON/TXT/HTML), interfaces/cli/ (rendu Rich)
# - Aucun lien avec une règle firewall, fail2ban, logs, blacklist
# - Aucune dépendance vers domain/, application/, infrastructure/, interfaces/
#
# Ce qu'il ne contient PAS :
# ❌ Pas d'import depuis domain/
# ❌ Pas d'import depuis application/
# ❌ Pas d'import depuis infrastructure/
# ❌ Pas d'import depuis interfaces/
# ❌ Pas de rendu Rich (c'est le rôle de interfaces/cli/renderers/)
# ❌ Pas de décision de couleur ou de style
# ❌ Pas de subprocess, sqlite3, open() — aucun I/O
#
# Points clés :
# - human_bytes() : formate octets → Ko/Mo/Go (binaire ou décimal)
# - human_duration() : formate secondes → '2h 15m 03s'
# - human_count() : formate grands nombres avec séparateurs (12 345)
# - pad_right() : aligne à gauche sur width caractères
# - truncate() : tronque une chaîne avec suffixe '…' si trop longue
# - Toutes les fonctions sont pures (pas d'effet de bord)
#
# Comment il sera utilisé (aperçu) :
# - domain/reports/builders.py utilisera human_bytes() pour tailles de logs
# - infrastructure/exporters/txt_exporter.py utilisera human_count()
# - interfaces/cli/renderers/tables.py utilisera pad_right() et truncate()
# - interfaces/cli/renderers/monitoring_live.py utilisera human_duration()
#---------------------------------------------------------------------->    
