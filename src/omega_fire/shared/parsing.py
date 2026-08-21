# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Helpers de parsing générique (texte, IP, champs)."""

from __future__ import annotations

import re
from typing import Iterable, Iterator

from omega_fire.shared.exceptions import ParsingError

# Regex "large" pour détecter une IPv4 ou IPv6 dans une ligne de log.
# Elle est volontairement permissive : la validation stricte se fait ensuite
# via ipaddress (dans shared/networking.py). Publiques (sans "_" préfixe) :
# réutilisées telles quelles par infrastructure/backends/nftables/adapter.py
# pour parser la sortie de "nft list set" (référentiel §50), qui a besoin
# d'y adjoindre son propre groupe optionnel "comment" — composer sur ces
# fragments plutôt que dupliquer la regex IPv6 (non triviale) une 2e fois.
IPV4_PATTERN = r"\b(?:\d{1,3}\.){3}\d{1,3}\b"
# Le motif précédent (\b...{1,4}:){2,7}[0-9a-fA-F]{1,4}\b) ne matchait jamais
# la notation compressée "::" (référentiel §49, 2026-08-17) — un groupe vide
# entre deux ":" consécutifs viole {1,4}, donc "::1"/"::"/"2001:db8::" (la
# forme la plus courante en pratique) n'étaient jamais extraits. Corrigé :
# {0,4} accepte un groupe vide (donc "::"), et \b remplacé par des
# lookaround négatifs ((?<![\w:])/(?![\w:])) car \b échoue sur une limite
# qui commence/finit par ":" (caractère non-mot des deux côtés).
#
# Forme IPv4-mapped (référentiel §60, 2026-08-17) : une adresse comme
# "::ffff:192.168.1.10" n'était matchée que jusqu'à "::ffff:192" — la
# branche purement hexadécimale ci-dessous ne reconnaît pas de point, donc
# elle s'arrête dès qu'elle croise le premier "." du quadruplet IPv4 final,
# tronquant l'adresse (rejetée ensuite par la validation stricte en aval,
# silencieusement absente de toute extraction en masse — jamais un problème
# pour la saisie unitaire ban/unban, qui valide directement via ipaddress
# sans passer par cette regex). Alternative dédiée ajoutée, essayée en
# premier : groupes hexadécimaux terminés par ':', suivis d'un quadruplet
# IPv4 (RFC 4291 §2.5.5 — forme x:x:x:x:x:x:d.d.d.d, y compris compressée).
IPV6_MAPPED_PATTERN = r"(?:[0-9a-fA-F]{0,4}:){2,6}(?:\d{1,3}\.){3}\d{1,3}"
IPV6_PATTERN = (
    r"(?<![\w:])(?:"
    rf"{IPV6_MAPPED_PATTERN}"
    r"|(?:[0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}"
    r")(?![\w:])"
)
_IP_PATTERN = re.compile(rf"(?:{IPV4_PATTERN}|{IPV6_PATTERN})")


def extract_ips(line: str) -> list[str]:
    """Extrait toutes les adresses IP (v4 ou v6) d'une ligne de texte.

    Args:
        line: ligne de log ou texte brut.

    Returns:
        Liste des IP trouvées (peut être vide).

    Note:
        La validation stricte (format correct, plage valide) n'est pas faite ici.
        Utiliser shared/networking.py pour valider chaque IP extraite.
    """
    return _IP_PATTERN.findall(line)


def extract_first_ip(line: str) -> str | None:
    """Extrait la première adresse IP trouvée dans une ligne, ou None."""
    match = _IP_PATTERN.search(line)
    return match.group(0) if match else None


def split_fields(line: str, separator: str | None = None) -> list[str]:
    """Découpe une ligne en champs, en ignorant les espaces multiples.

    Args:
        line: ligne à découper.
        separator: séparateur explicite (None = whitespace).

    Returns:
        Liste de champs nettoyés (vides retirés).
    """
    if separator is None:
        return line.split()
    return [field.strip() for field in line.split(separator) if field.strip()]


def extract_key_value(line: str, separator: str = "=") -> dict[str, str]:
    """Extrait les paires clé=valeur d'une ligne.

    Args:
        line: ligne contenant des paires clé=valeur.
        separator: séparateur entre clé et valeur (défaut '=').

    Returns:
        Dictionnaire {clé: valeur} (valeurs entre guillemets dépouillées).
    """
    result: dict[str, str] = {}
    # Pattern : mot-clé suivi du séparateur puis valeur (entre guillemets ou non)
    pattern = re.compile(
        rf'(\w+)\s*{re.escape(separator)}\s*(?:"([^"]*")|\'([^\']*)\'|(\S+))'
    )
    for match in pattern.finditer(line):
        key = match.group(1)
        value = match.group(2) or match.group(3) or match.group(4) or ""
        # Retirer les guillemets finaux si présents
        value = value.strip("\"'")
        result[key] = value
    return result


def iter_lines(text: str) -> Iterator[str]:
    """Itère sur les lignes d'un texte, en ignorant les lignes vides."""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            yield stripped


def require_match(pattern: re.Pattern[str], text: str, context: str = "") -> re.Match[str]:
    """Applique un regex et lève ParsingError si pas de match.

    Args:
        pattern: regex compilé.
        text: texte à matcher.
        context: contexte optionnel pour le message d'erreur.

    Returns:
        L'objet Match.

    Raises:
        ParsingError: si le regex ne matche pas.
    """
    match = pattern.search(text)
    if not match:
        msg = f"Regex ne matche pas"
        if context:
            msg += f" (contexte: {context})"
        raise ParsingError(msg)
    return match

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Fournit des helpers de parsing générique : extraction d'IP depuis une ligne,
#   découpe de champs, extraction de paires clé=valeur, itération sur lignes.
# - Fournit un helper require_match() pour lever ParsingError si regex échoue.
#
# Pourquoi dans shared/ (charte) :
# - Ce sont des outils de parsing texte, non métier
# - Utilisés par domain/logs/parser.py (extraction IP), infrastructure/backends/
#   */parser.py (parsing nft/iptables/fail2ban)
# - Aucun lien avec une règle firewall, fail2ban, logs, blacklist
# - Aucune dépendance vers domain/, application/, infrastructure/, interfaces/
#
# Ce qu'il ne contient PAS :
# ❌ Pas d'import depuis domain/
# ❌ Pas d'import depuis application/
# ❌ Pas d'import depuis infrastructure/
# ❌ Pas d'import depuis interfaces/
# ❌ Pas de logique métier (ex: parsing spécifique nftables)
# ❌ Pas de validation stricte d'IP (c'est shared/networking.py)
# ❌ Pas de subprocess, sqlite3, rich, open() — aucun I/O
#
# Points clés :
# - extract_ips() : extrait toutes les IP (v4/v6) d'une ligne (regex permissive)
# - extract_first_ip() : extrait la première IP trouvée
# - split_fields() : découpe une ligne en champs (whitespace ou séparateur)
# - extract_key_value() : extrait paires clé=valeur (gère guillemets)
# - iter_lines() : itère sur lignes non vides d'un texte
# - require_match() : lève ParsingError si regex ne matche pas
# - Les regex IP sont permissives (validation stricte via shared/networking.py)
#
# Comment il sera utilisé (aperçu) :
# - domain/logs/parser.py utilisera extract_ips() pour extraire IP des logs
# - infrastructure/backends/nftables/parser.py utilisera split_fields()
# - infrastructure/backends/fail2ban/parser.py utilisera extract_key_value()
# - infrastructure/probe/scanner.py utilisera require_match() pour valider sorties
#---------------------------------------------------------------------->    
