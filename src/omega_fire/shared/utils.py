# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Helpers génériques non métier (validation, conversions)."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

from omega_fire.shared.exceptions import ValidationError


# --- Validation de ports -------------------------------------------------

def validate_port(value: int | str) -> int:
    """Valide et normalise un numéro de port (1-65535).

    Args:
        value: port sous forme d'entier ou de chaîne.

    Returns:
        Le port sous forme d'entier.

    Raises:
        ValidationError: si la valeur n'est pas un port valide.
    """
    try:
        port = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"Port invalide (non entier): {value!r}") from exc
    if not 1 <= port <= 65535:
        raise ValidationError(f"Port hors plage (1-65535): {port}")
    return port


def validate_port_range(value: str) -> tuple[int, int]:
    """Valide une plage de ports au format 'start-end' ou 'port'.

    Returns:
        Un tuple (start, end) avec start <= end.
    """
    if "-" not in value:
        port = validate_port(value)
        return port, port
    parts = value.split("-", 1)
    if len(parts) != 2:
        raise ValidationError(f"Plage de ports mal formée: {value!r}")
    start = validate_port(parts[0].strip())
    end = validate_port(parts[1].strip())
    if start > end:
        raise ValidationError(f"Plage inversée: {start} > {end}")
    return start, end


# --- Validation de dates -------------------------------------------------

_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}(?::\d{2})?)?$")


def parse_iso_datetime(value: str) -> datetime:
    """Parse une date ISO 8601 simplifiée (YYYY-MM-DD ou YYYY-MM-DDTHH:MM[:SS]).

    Retourne un datetime UTC si aucun fuseau n'est précisé.
    """
    if not _ISO_DATE_RE.match(value):
        raise ValidationError(f"Format de date invalide: {value!r}")
    normalized = value.replace(" ", "T")
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(normalized, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    raise ValidationError(f"Date ininterprétable: {value!r}")


# --- Chemins & fichiers --------------------------------------------------

def ensure_directory(path: str | Path) -> Path:
    """Crée le répertoire (et ses parents) s'il n'existe pas, puis le retourne."""
    p = Path(path).expanduser().resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


def safe_filename(value: str, default: str = "export") -> str:
    """Nettoie une chaîne pour en faire un nom de fichier sûr.

    Remplace les caractères non alphanumériques par '_' et retombe
    sur `default` si le résultat est vide.
    """
    cleaned = re.sub(r"[^\w.\-]+", "_", value).strip("._")
    return cleaned or default


# --- Divers --------------------------------------------------------------

def clamp(value: int, minimum: int, maximum: int) -> int:
    """Force `value` à rester dans l'intervalle [minimum, maximum]."""
    if value < minimum:
        return minimum
    if value > maximum:
        return maximum
    return value
# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Fournit des helpers de validation génériques : ports (1-65535), plages de
#   ports, dates ISO 8601 simplifiées, chemins, noms de fichiers sûrs.
# - Fournit des conversions utilitaires : clamp, ensure_directory.
#
# Pourquoi dans shared/ (charte) :
# - Ce sont des validations techniques réutilisables, non métier
# - Utilisés par domain/ (validation de règles), infrastructure/ (fichiers),
#   interfaces/ (saisies utilisateur)
# - Aucun lien avec une règle firewall, fail2ban, logs, blacklist
# - Aucune dépendance vers domain/, application/, infrastructure/, interfaces/
#
# Ce qu'il ne contient PAS :
# ❌ Pas d'import depuis domain/
# ❌ Pas d'import depuis application/
# ❌ Pas d'import depuis infrastructure/
# ❌ Pas d'import depuis interfaces/
# ❌ Pas de logique métier (ex: politique de ban, règle firewall)
# ❌ Pas de subprocess, sqlite3, rich — aucun I/O complexe
# ❌ Pas de validation d'IP (c'est le rôle de shared/networking.py)
#
# Points clés :
# - validate_port() : valide un port unique (1-65535)
# - validate_port_range() : valide une plage 'start-end' ou 'port'
# - parse_iso_datetime() : parse YYYY-MM-DD ou YYYY-MM-DDTHH:MM[:SS] → UTC
# - ensure_directory() : crée récursivement un répertoire
# - safe_filename() : nettoie une chaîne pour nom de fichier sûr
# - clamp() : force une valeur dans un intervalle
# - Toutes les fonctions lèvent ValidationError (de shared/exceptions.py)
#
# Comment il sera utilisé (aperçu) :
# - domain/rules/models.py utilisera validate_port() pour valider les règles
# - infrastructure/exporters/json_exporter.py utilisera safe_filename()
# - interfaces/cli/prompts.py utilisera validate_port_range() pour les saisies
# - application/commands/ban_ip.py utilisera parse_iso_datetime() pour dates
#---------------------------------------------------------------------->
