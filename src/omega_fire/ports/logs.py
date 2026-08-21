# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Contrat pour la gestion des logs (analyse, rotation, nettoyage)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol

from omega_fire.shared.networking import IPAddress


@dataclass(frozen=True, slots=True)
class LogEntry:
    """Entrée de log immuable.

    Attributs:
        timestamp: date et heure de l'événement.
        source_ip: adresse IP source.
        destination_ip: adresse IP destination (optionnel).
        method: méthode HTTP (GET, POST, etc.).
        path: chemin de la requête.
        status_code: code de statut HTTP.
        bytes_sent: nombre d'octets envoyés.
        user_agent: user-agent du client (optionnel).
        raw_line: ligne brute du log.
    """
    timestamp: datetime
    source_ip: IPAddress
    destination_ip: IPAddress | None = None
    method: str = ""
    path: str = ""
    status_code: int = 0
    bytes_sent: int = 0
    user_agent: str = ""
    raw_line: str = ""


@dataclass(frozen=True, slots=True)
class LogStats:
    """Statistiques de logs.

    Attributs:
        total_entries: nombre total d'entrées.
        top_ips: liste des IPs les plus fréquentes (IP, count).
        status_distribution: répartition des codes HTTP (code, count).
        hourly_distribution: répartition par heure (heure, count).
        daily_distribution: répartition par jour (date, count).
    """
    total_entries: int
    top_ips: list[tuple[IPAddress, int]]
    status_distribution: dict[int, int]
    hourly_distribution: dict[int, int]
    daily_distribution: dict[str, int]


@dataclass(frozen=True, slots=True)
class LogBackup:
    """Sauvegarde de logs.

    Attributs:
        path: chemin du fichier de backup.
        created_at: date de création.
        size_bytes: taille en octets.
        compressed: True si compressé (gzip).
    """
    path: Path
    created_at: datetime
    size_bytes: int
    compressed: bool


class LogsPort(Protocol):
    """Contrat pour la gestion des logs.

    Définit les opérations attendues pour analyser, rotater,
    nettoyer et restaurer les logs.
    """

    @abstractmethod
    def parse_line(self, line: str) -> LogEntry | None:
        """Parse une ligne de log brute.

        Args:
            line: ligne brute du log.

        Returns:
            LogEntry si la ligne est valide, None sinon.
        """
        ...

    @abstractmethod
    def get_top_ips(self, limit: int = 20) -> list[tuple[IPAddress, int]]:
        """Récupère les IPs les plus fréquentes.

        Args:
            limit: nombre maximum d'IPs à retourner.

        Returns:
            Liste de tuples (IP, count) triés par fréquence décroissante.
        """
        ...

    @abstractmethod
    def get_stats(self) -> LogStats:
        """Récupère les statistiques complètes des logs.

        Returns:
            LogStats avec toutes les distributions.
        """
        ...

    @abstractmethod
    def remove_ip(self, ip: IPAddress) -> int:
        """Supprime toutes les occurrences d'une IP des logs.

        Args:
            ip: adresse IP à supprimer.

        Returns:
            Nombre d'entrées supprimées.
        """
        ...

    @abstractmethod
    def rotate(self, backup_dir: Path) -> LogBackup:
        """Effectue une rotation des logs (backup + compression).

        Args:
            backup_dir: répertoire de destination des backups.

        Returns:
            LogBackup du fichier créé.
        """
        ...

    @abstractmethod
    def list_backups(self, backup_dir: Path) -> list[LogBackup]:
        """Liste les backups disponibles.

        Args:
            backup_dir: répertoire des backups.

        Returns:
            Liste de LogBackup triés par date décroissante.
        """
        ...

    @abstractmethod
    def restore_backup(self, backup: LogBackup) -> None:
        """Restaure un backup de logs.

        Args:
            backup: backup à restaurer.
        """
        ...

    @abstractmethod
    def purge_backups(self, backup_dir: Path, older_than: datetime | None = None) -> int:
        """Supprime les backups anciens.

        Args:
            backup_dir: répertoire des backups.
            older_than: si fourni, supprime uniquement les backups avant cette date.

        Returns:
            Nombre de backups supprimés.
        """
        ...

    @abstractmethod
    def cleanup(self, *, keep_days: int | None = None, keep_lines: int | None = None) -> int:
        """Nettoie les logs anciens.

        Args:
            keep_days: conserve uniquement les logs des N derniers jours.
            keep_lines: conserve uniquement les N dernières lignes.

        Returns:
            Nombre d'entrées supprimées.
        """
        ...

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit le contrat (Protocol) pour la gestion des logs.
# - Fournit LogEntry, LogStats, LogBackup (dataclasses frozen).
# - Spécifie les opérations : parse_line(), get_top_ips(), get_stats(), remove_ip(),
#   rotate(), list_backups(), restore_backup(), purge_backups(), cleanup().
#
# Pourquoi dans ports/ (charte) :
# - C'est un contrat attendu par le cœur applicatif (application/commands/)
# - Pas d'implémentation concrète (c'est le rôle de infrastructure/)
# - Aucune dépendance vers domain/, application/, infrastructure/, interfaces/
#
# Ce qu'il ne contient PAS :
# ❌ Pas d'implémentation concrète (lecture fichiers, compression gzip)
# ❌ Pas d'import depuis domain/
# ❌ Pas d'import depuis application/
# ❌ Pas d'import depuis infrastructure/
# ❌ Pas d'import depuis interfaces/
# ❌ Pas de logique de parsing spécifique (regex Apache/Nginx)
#
# Points clés :
# - LogEntry : dataclass frozen avec timestamp, source_ip, destination_ip, method,
#   path, status_code, bytes_sent, user_agent, raw_line
# - LogStats : dataclass frozen avec total_entries, top_ips, status_distribution,
#   hourly_distribution, daily_distribution
# - LogBackup : dataclass frozen avec path, created_at, size_bytes, compressed
# - LogsPort : Protocol définissant toutes les opérations sur logs
# - IPAddress importé depuis shared/networking.py
# - Toutes les méthodes sont abstraites (via Protocol)
#
# Comment il sera utilisé (aperçu) :
# - application/queries/log_top_ips.py appellera logs_port.get_top_ips()
# - application/commands/rotate_logs.py appellera logs_port.rotate()
# - infrastructure/ implémentera LogsPort (lecture fichiers, parsing)
# - interfaces/cli/actions.py appellera logs_port.get_stats() pour menu 5.8
#---------------------------------------------------------------------->        
