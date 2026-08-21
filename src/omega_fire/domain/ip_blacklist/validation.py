# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Blocklist file line validation.

Pure domain rules defining what counts as a valid line inside a
blocklist text file (var/blocklist/*.txt): a single IP address or
CIDR network per line, a comment line, or a blank line. Nothing else
is considered valid — this is the sole gatekeeper protecting menu 2.7
(file-based blocklist editing) from ever producing content that a
backend adapter's ban_ip()/unban_ip() could choke on later.

No I/O, no file access — receives and returns plain strings/values
only. Reading/writing the actual file is infrastructure's job
(TextStore); deciding whether a line is acceptable is a business
rule, hence domain/.
"""
from dataclasses import dataclass
from enum import Enum
from ipaddress import ip_network
from typing import Optional


COMMENT_PREFIX = "#"


class LineKind(Enum):
    """Classification of a single line in a blocklist file."""
    IP = "ip"
    COMMENT = "comment"
    BLANK = "blank"
    INVALID = "invalid"


@dataclass(frozen=True)
class ParsedLine:
    """Result of classifying one line of a blocklist file."""
    line_number: int
    raw: str
    kind: LineKind
    ip: Optional[str] = None  # normalized IP/CIDR, only set when kind == IP
    reason: Optional[str] = None  # explanation, only set when kind == INVALID


def classify_line(raw: str, line_number: int = 0) -> ParsedLine:
    """Classify a single raw line as IP, COMMENT, BLANK, or INVALID.

    Accepted formats:
    - A single IPv4/IPv6 address (e.g. "192.168.1.50")
    - A CIDR network (e.g. "10.0.0.0/24")
    - A comment line: starts with '#', any content after is free text
    - A blank line (whitespace only)

    Anything else — free text, multiple values on one line, a
    malformed address — is INVALID, with a human-readable reason.
    A trailing inline comment after an IP (e.g. "1.2.3.4 # note") is
    tolerated and stripped before validation: the IP is checked on
    its own, the comment portion never causes rejection.
    """
    stripped = raw.strip()

    if not stripped:
        return ParsedLine(line_number=line_number, raw=raw, kind=LineKind.BLANK)

    if stripped.startswith(COMMENT_PREFIX):
        return ParsedLine(line_number=line_number, raw=raw, kind=LineKind.COMMENT)

    # Tolère un commentaire en fin de ligne après l'IP (ex: "1.2.3.4 # note"),
    # convention déjà utilisée par les exports du projet (voir menu 2.8).
    candidate = stripped.split(COMMENT_PREFIX, 1)[0].strip()

    # Une ligne valide ne contient qu'UN SEUL token réseau — pas de liste,
    # pas de texte additionnel non préfixé par '#'.
    if " " in candidate or "\t" in candidate:
        return ParsedLine(
            line_number=line_number,
            raw=raw,
            kind=LineKind.INVALID,
            reason="Plusieurs valeurs ou texte libre sur une seule ligne (une IP par ligne).",
        )

    try:
        network = ip_network(candidate, strict=False)
        is_single_host = "/" not in candidate
        return ParsedLine(
            line_number=line_number,
            raw=raw,
            kind=LineKind.IP,
            ip=str(network.network_address) if is_single_host else str(network),
        )
    except ValueError:
        return ParsedLine(
            line_number=line_number,
            raw=raw,
            kind=LineKind.INVALID,
            reason=f"'{candidate}' n'est pas une adresse IP ou un réseau CIDR valide.",
        )


def parse_blocklist_content(content: str) -> list[ParsedLine]:
    """Classify every line of a blocklist file's content, in order."""
    return [
        classify_line(raw, line_number=idx + 1)
        for idx, raw in enumerate(content.splitlines())
    ]


def extract_valid_ips(parsed_lines: list[ParsedLine]) -> list[str]:
    """Extract only the valid IP/CIDR values, in file order, deduplicated."""
    seen: set[str] = set()
    result: list[str] = []
    for line in parsed_lines:
        if line.kind == LineKind.IP and line.ip not in seen:
            seen.add(line.ip)
            result.append(line.ip)
    return result


def extract_rejected_lines(parsed_lines: list[ParsedLine]) -> list[ParsedLine]:
    """Extract only the INVALID lines, for reporting to the user before
    any cleanup is applied — see rebuild_clean_content()."""
    return [line for line in parsed_lines if line.kind == LineKind.INVALID]


def rebuild_clean_content(parsed_lines: list[ParsedLine]) -> str:
    """Rebuild file content keeping only IP, COMMENT and BLANK lines.

    INVALID lines are silently dropped here (Option B: automatic
    cleanup, never blocking the save). The caller is responsible for
    showing extract_rejected_lines() to the user BEFORE calling this,
    so the cleanup is always reported, never a silent surprise.
    """
    kept = [
        line.raw
        for line in parsed_lines
        if line.kind in (LineKind.IP, LineKind.COMMENT, LineKind.BLANK)
    ]
    return "\n".join(kept) + ("\n" if kept else "")


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit ce qu'est une ligne valide dans un fichier blocklist texte :
#   une IP/CIDR seule, un commentaire ('#'), ou une ligne vide. Rejette
#   tout le reste avec une raison explicite.
# Pourquoi dans domain/ (charte) :
# - Règle métier pure : la définition d'une "ligne valide" ne dépend
#   d'aucun détail de stockage (fichier, chemin) ni de rendu (Rich).
# - Aucune dépendance externe hormis le module standard 'ipaddress'
#   (déjà utilisé ailleurs dans le projet, ex. application/commands/
#   create_rule.py côté validation CIDR pour le menu 3.1).
# - Testable en mémoire pure, sans aucun fichier réel.
# Ce qu'il ne contient PAS :
# ❌ Pas d'I/O (ne lit ni n'écrit aucun fichier — TextStore s'en charge)
# ❌ Pas de rendu Rich, pas de prompt utilisateur
# ❌ Pas d'appel à un adapter backend
# Points clés :
# - LineKind : IP | COMMENT | BLANK | INVALID
# - ParsedLine : résultat de classification d'une ligne (numéro, brut,
#   nature, IP normalisée si applicable, raison si invalide)
# - classify_line() : classifie UNE ligne
# - parse_blocklist_content() : classifie tout le contenu d'un fichier
# - extract_valid_ips() : liste des IP/CIDR valides, dédupliquée, dans
#   l'ordre du fichier
# - extract_rejected_lines() : liste des lignes invalides, pour rapport
#   utilisateur AVANT tout nettoyage
# - rebuild_clean_content() : reconstruit un contenu propre (IP +
#   commentaires + lignes vides conservés, invalides retirées) — Option
#   B actée : jamais bloquant, toujours accompagné du rapport
#   extract_rejected_lines() en amont
# Comment il sera utilisé (aperçu) :
# - application/commands/manage_blocklist_file.py (Phase 4) l'utilisera
#   pour valider le contenu avant sauvegarde et produire le rapport
#   affiché à l'utilisateur par le menu 2.7 (Phase 6)
#---------------------------------------------------------------------->
