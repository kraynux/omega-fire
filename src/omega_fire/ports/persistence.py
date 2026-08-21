# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Contrat pour la persistance (sauvegarde, restauration, snapshots)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class BackupInfo:
    path: Path
    created_at: datetime
    size_bytes: int
    components: list[str]
    metadata: dict[str, str] | None = None


@dataclass(frozen=True, slots=True)
class Snapshot:
    id: str
    created_at: datetime
    blacklist_count: int
    rules_count: int
    jails_count: int
    description: str = ""
    origin: str = "manual"


class PersistencePort(Protocol):

    @abstractmethod
    def create_backup(
        self,
        backup_dir: Path,
        *,
        source_paths: list[Path],
        components: list[str] | None = None,
        metadata: dict[str, str] | None = None,
    ) -> BackupInfo:
        ...

    @abstractmethod
    def restore_backup(self, backup: BackupInfo, *, dest_dir: Path) -> None:
        ...

    @abstractmethod
    def list_backups(self, backup_dir: Path) -> list[BackupInfo]:
        ...

    @abstractmethod
    def delete_backup(self, backup: BackupInfo) -> None:
        ...

    @abstractmethod
    def create_snapshot(
        self,
        *,
        banned_ips: list,
        rules: list,
        jails: list,
        description: str = "",
        origin: str = "manual",
    ) -> Snapshot:
        ...
        
    @abstractmethod
    def list_snapshots(self) -> list[Snapshot]:
        ...

    @abstractmethod
    def restore_snapshot(self, snapshot_id: str) -> None:
        ...

    @abstractmethod
    def delete_snapshot(self, snapshot_id: str) -> None:
        ...
# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit le contrat (Protocol) pour la persistance (sauvegarde, restauration).
# - Fournit BackupInfo, Snapshot (dataclasses frozen) et SnapshotOrigin (Enum).
# - Spécifie les opérations : create_backup(), restore_backup(), list_backups(),
#   delete_backup(), create_snapshot(), list_snapshots(), restore_snapshot(),
#   delete_snapshot().
#
# Pourquoi dans ports/ (charte) :
# - C'est un contrat attendu par le cœur applicatif (application/commands/)
# - Pas d'implémentation concrète (c'est le rôle de infrastructure/storage/)
# - Aucune dépendance vers domain/, application/, infrastructure/, interfaces/
#
# Ce qu'il ne contient PAS :
# ❌ Pas d'implémentation concrète (écriture fichiers, compression tar.gz)
# ❌ Pas d'import depuis domain/
# ❌ Pas d'import depuis application/
# ❌ Pas d'import depuis infrastructure/
# ❌ Pas d'import depuis interfaces/
# ❌ Pas de logique SQLite directe
#
# Points clés :
# - Snapshot et SnapshotOrigin sont désormais définis dans core/models.py
#   (langage transverse partagé avec domain/persistence/rotation.py) et
#   simplement importés ici.
# - BackupInfo : dataclass frozen avec path, created_at, size_bytes, components, metadata
# - PersistencePort : Protocol définissant toutes les opérations de backup/snapshot
# - Toutes les méthodes sont abstraites (via Protocol)
#
# Comment il sera utilisé (aperçu) :
# - application/commands/backup_state.py appellera persistence_port.create_backup()
# - application/commands/restore_state.py appellera persistence_port.restore_backup()
# - application/commands/apply_preset.py appellera persistence_port.create_snapshot(
#   origin=SnapshotOrigin.AUTO_PRESET) avant tout changement de profil (menu 3.4)
# - infrastructure/storage/ implémentera PersistencePort (SQLite, fichiers) et
#   sera responsable de la conversion SnapshotOrigin <-> str (colonne TEXT)
# - interfaces/cli/actions.py appellera persistence_port.list_backups() pour menu 7.1
# - create_backup() exige explicitement source_paths : le port ne
#   présume jamais de ce qui doit être sauvegardé, c'est toujours
#   l'appelant (application/) qui le précise.
#---------------------------------------------------------------------->
