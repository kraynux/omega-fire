# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Purge backups command.

Deletes a list of backup archives via the persistence port, translating
each deletion into a structured count of successes/failures. The
selection of *which* archives to delete (by age, quota, prefix, or
manual choice) remains the responsibility of the caller (menu 5.6 in
interfaces/cli/actions.py) — this command only executes the deletion.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from omega_fire.ports.persistence import BackupInfo


@dataclass
class PurgeBackupsResult:
    """Output of the purge backups use case."""
    deleted_count: int = 0
    error_count: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return self.error_count == 0


class PurgeBackupsCommand:
    """Use case: delete a set of backup archives via the persistence port."""

    def __init__(self, persistence_port: Any):
        self._port = persistence_port

    def execute(self, backups_to_delete: list[BackupInfo]) -> PurgeBackupsResult:
        deleted_count = 0
        errors: list[str] = []

        for backup in backups_to_delete:
            try:
                self._port.delete_backup(backup)
                deleted_count += 1
            except Exception as e:
                errors.append(f"{backup.path.name} : {e}")

        return PurgeBackupsResult(
            deleted_count=deleted_count,
            error_count=len(errors),
            errors=errors,
        )


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Supprime une liste de backups (menu 5.6) via le port persistence.
# - La SÉLECTION des archives à supprimer (par ancienneté, quota,
#   préfixe safety_auto_, ou choix manuel) reste dans actions.py — ce
#   n'est pas une règle métier au sens strict, plutôt un filtre UI sur
#   des métadonnées de fichiers déjà affichées à l'utilisateur.
#
# Pourquoi dans application/commands/ (charte) :
# - Exécute la suppression sans jamais appeler Path.unlink() directement
#   (délégué au port, qui délègue à ArchiveStore).
#
# Flux d'exécution :
# interfaces/cli/actions.py : action_5_6_purge_backups(ctx)
#   ↓ calcule files_to_delete (ancienneté/quota/etc., inchangé)
#   ↓ résout le port via ctx.container.get_persistence_port()
#   ↓ construit une liste de BackupInfo depuis persistence_port.list_backups()
# application/commands/purge_backups.py : PurgeBackupsCommand.execute()
#   ↓ persistence_port.delete_backup() pour chaque backup ciblé
#----------------------------------------------------------------------
