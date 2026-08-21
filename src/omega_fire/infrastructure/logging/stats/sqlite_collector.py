# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
from datetime import datetime, timedelta
import os
from pathlib import Path
import sqlite3
from typing import Dict, List, Optional, Tuple

from omega_fire.core.stats.models import IpStat, JailStat, LogEntry


class SqliteLogCollector:
    """Collecteur de données de logs à partir de la base de données SQLite de Fail2ban."""

    DEFAULT_DB_PATH = Path("/var/lib/fail2ban/fail2ban.sqlite3")

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or self.DEFAULT_DB_PATH

    def is_available(self) -> bool:
        """Vérifie si la base SQLite existe et est lisible."""
        return self.db_path.exists() and os.access(self.db_path, os.R_OK)

    def fetch_bans(self, since: datetime) -> List[LogEntry]:
        """Récupère tous les événements de type 'Ban' depuis une date donnée."""
        if not self.is_available():
            return []

        entries: List[LogEntry] = []
        since_timestamp = int(since.timestamp())

        query = """
            SELECT jail, ip, timeofban, data
            FROM bans
            WHERE timeofban >= ?
            ORDER BY timeofban ASC
        """

        try:
            # Ouverture en mode lecture seule via URI SQLite
            conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
            cursor = conn.cursor()
            cursor.execute(query, (since_timestamp,))

            for jail, ip, timeofban, data in cursor.fetchall():
                timestamp = datetime.fromtimestamp(timeofban)
                entries.append(
                    LogEntry(
                        timestamp=timestamp,
                        jail=jail,
                        action="Ban",
                        ip=ip,
                        message=data,
                    )
                )
            conn.close()
        except sqlite3.Error:
            # En cas d'erreur de lecture SQLite, on retourne la liste partielle/vide
            pass

        return entries

    def get_active_jails(self) -> List[str]:
        """Récupère la liste des Jails actuellement enregistrées dans la DB."""
        if not self.is_available():
            return []

        active_jails = []
        query = "SELECT DISTINCT jail FROM bans"

        try:
            conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
            cursor = conn.cursor()
            cursor.execute(query)
            active_jails = [row[0] for row in cursor.fetchall()]
            conn.close()
        except sqlite3.Error:
            pass

        return active_jails
