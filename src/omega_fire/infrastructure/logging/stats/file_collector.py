# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
from datetime import datetime
import gzip
import os
from pathlib import Path
import re
from typing import List, Optional

from omega_fire.core.stats.models import LogEntry


class FileLogCollector:
    """Collecteur de données par analyse des fichiers de logs (fail2ban.log et archives .gz)."""

    DEFAULT_LOG_DIR = Path("/var/log")
    
    # Pattern Regex pour Fail2ban : YYYY-MM-DD HH:MM:SS ... [jail] Action IP
    FAIL2BAN_PATTERN = re.compile(
        r"^(?P<date>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}).*?\[(?P<jail>[^\]]+)\]\s+(?P<action>Ban|Unban|Restore)\s+(?P<ip>\S+)"
    )

    def __init__(self, log_dir: Optional[Path] = None):
        self.log_dir = log_dir or self.DEFAULT_LOG_DIR

    def _get_log_files(self) -> List[Path]:
        """Retourne la liste des fichiers fail2ban.log* triés par date de modification."""
        if not self.log_dir.exists():
            return []
        
        # Récupère fail2ban.log, fail2ban.log.1, fail2ban.log.2.gz, etc.
        files = list(self.log_dir.glob("fail2ban.log*"))
        return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)

    def fetch_entries(self, since: datetime) -> List[LogEntry]:
        """Parcourt les logs et extrait les événements postérieurs à la date demandée."""
        entries: List[LogEntry] = []
        log_files = self._get_log_files()

        for file_path in log_files:
            if not os.access(file_path, os.R_OK):
                continue

            # Choix du lecteur selon le format (texte brut ou archive .gz)
            opener = gzip.open if file_path.suffix == ".gz" else open
            
            try:
                with opener(file_path, "rt", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        match = self.FAIL2BAN_PATTERN.search(line)
                        if not match:
                            continue

                        data = match.groupdict()
                        try:
                            log_time = datetime.strptime(data["date"], "%Y-%m-%d %H:%M:%S")
                        except ValueError:
                            continue

                        # Si la ligne est plus ancienne que notre période cible, on passe
                        if log_time < since:
                            continue

                        entries.append(
                            LogEntry(
                                timestamp=log_time,
                                jail=data["jail"],
                                action=data["action"],
                                ip=data["ip"],
                            )
                        )
            except Exception:
                # Si un fichier est corrompu ou illisible, on continue sur les autres
                continue

        # Tri chronologique des événements extraits
        entries.sort(key=lambda x: x.timestamp)
        return entries
