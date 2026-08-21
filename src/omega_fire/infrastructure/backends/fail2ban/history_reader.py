# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Fail2ban database history reader.

Reads fail2ban's own SQLite database (typically
/var/lib/fail2ban/fail2ban.sqlite3) in strict read-only mode to
retrieve chronological ban history — information not exposed by
fail2ban-client itself (list_jails()/get_jail_status() only give the
CURRENT state, no ordering by time).

This is a separate concern from Fail2banAdapter (which talks to
fail2ban-client via subprocess): here we read fail2ban's own storage
directly, never write to it, and never assume it exists (fail2ban may
be configured without persistent storage).
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

DEFAULT_F2B_DB_PATH = Path("/var/lib/fail2ban/fail2ban.sqlite3")


class Fail2banHistoryReader:
    """Read-only reader for fail2ban's internal SQLite database."""

    def __init__(self, db_path: Path = DEFAULT_F2B_DB_PATH):
        self._db_path = db_path

    def is_available(self) -> bool:
        """Check if fail2ban's database file exists and is readable."""
        return self._db_path.exists()

    def get_recent_bans(self, jail_name: str, limit: int = 10) -> list[dict]:
        """Get the most recent bans for a jail, most recent first.

        Args:
            jail_name: Name of the jail.
            limit: Maximum number of entries to return.

        Returns:
            List of dicts with keys: ip, timeofban (Unix timestamp),
            bantime, bancount. Empty list if the database is
            unavailable or the query fails — never raises.
        """
        if not self.is_available():
            return []

        try:
            # URI mode=ro : ouverture strictement en lecture seule,
            # jamais de risque d'écrire ou de verrouiller la base
            # réelle de fail2ban.
            uri = f"file:{self._db_path}?mode=ro"
            conn = sqlite3.connect(uri, uri=True, timeout=2.0)
            conn.row_factory = sqlite3.Row
            try:
                cursor = conn.execute(
                    "SELECT ip, timeofban, bantime, bancount "
                    "FROM bips WHERE jail = ? "
                    "ORDER BY timeofban DESC LIMIT ?",
                    (jail_name, limit),
                )
                return [dict(row) for row in cursor.fetchall()]
            finally:
                conn.close()
        except Exception:
            return []


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Lit en lecture seule la base SQLite propre à fail2ban (table bips)
#   pour obtenir un historique chronologique des bans par jail —
#   donnée absente de fail2ban-client (status ne donne que l'état
#   courant, sans ordre temporel).
#
# Pourquoi dans infrastructure/backends/fail2ban/ (charte) :
# - Accès technique à une base de données externe (celle de fail2ban,
#   pas la nôtre), colocalisé avec le reste du backend fail2ban.
#
# Ce qu'il ne contient PAS :
# ❌ Jamais d'écriture (mode=ro strict, pas de fallback en lecture-écriture)
# ❌ Pas de dépendance à notre propre infrastructure/storage/sqlite/
#   (base entièrement séparée, gérée par fail2ban lui-même)
#
# Points clés :
# - is_available() : vérifie la présence du fichier avant toute requête
# - get_recent_bans() : jamais d'exception propagée — retourne une
#   liste vide si la base est absente/inaccessible/verrouillée
# - Chemin par défaut : /var/lib/fail2ban/fail2ban.sqlite3 (standard),
#   configurable via le constructeur si besoin
#
# Comment il sera utilisé :
# - application/queries/f2b_report/jails_section.py appellera
#   get_recent_bans() pour enrichir le détail de chaque jail.
#----------------------------------------------------------------------
