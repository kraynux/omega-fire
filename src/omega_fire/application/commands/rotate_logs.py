# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Rotate logs command.

Orchestrates the creation of a compressed backup for a single log file
chosen by the user (menu 5.4), then applies the retention limit by
deleting the oldest excess backups.

Conforms to Omega-Fire architecture charter:
- No direct tarfile/file I/O (delegated to the persistence port)
- Translates infrastructure exceptions into a structured result
- Auditing is handled by the caller (interfaces/cli/_execute_action_flow),
  not duplicated here
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from omega_fire.domain.logs.rotation import compute_rotations_to_delete
from omega_fire.infrastructure.exceptions import StorageError


@dataclass
class RotateLogsRequest:
    """Input for the rotate logs use case."""
    source_path: str
    target: str = "all"
    reason: Optional[str] = None
    compress: bool = True
    keep: int = 7

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.source_path:
            errors.append("source_path must not be empty")
        if not Path(self.source_path).exists():
            errors.append(f"Source file not found: {self.source_path}")
        if self.keep < 1:
            errors.append("Keep must be at least 1")
        if self.keep > 365:
            errors.append("Keep must not exceed 365 days")
        return errors

    def is_valid(self) -> bool:
        return len(self.validate()) == 0


@dataclass
class RotateLogsResult:
    """Output of the rotate logs use case."""
    success: bool
    message: str
    backup_path: Optional[Path] = None
    backup_size_bytes: Optional[int] = None
    deleted_count: int = 0


class RotateLogsCommand:
    """Use case: create a compressed backup of a log file, then apply
    the retention limit by deleting the oldest excess backups."""

    def __init__(self, persistence_port: Any, backup_dir: Path = Path("var/backups")):
        """Initialize the command.

        Args:
            persistence_port: implementation of PersistencePort (via
                app/dependency_container.py::get_persistence_port()).
            backup_dir: destination directory for backups.
        """
        self._port = persistence_port
        self._backup_dir = backup_dir

    def execute(self, request: RotateLogsRequest) -> RotateLogsResult:
        errors = request.validate()
        if errors:
            return RotateLogsResult(success=False, message="; ".join(errors))

        source = Path(request.source_path)

        # --- 1. Création du backup ---
        try:
            backup_info = self._port.create_backup(
                backup_dir=self._backup_dir,
                source_paths=[source],
                components=["logs"],
                metadata={"target": request.target, "reason": request.reason or ""},
            )
        except StorageError as e:
            return RotateLogsResult(
                success=False,
                message=f"Erreur technique lors de la sauvegarde : {e}",
            )

        # --- 2. Application de la limite de rétention ---
        try:
            existing_backups = self._port.list_backups(self._backup_dir)
        except StorageError as e:
            # Le backup a réussi, seule la purge des anciens a échoué
            return RotateLogsResult(
                success=True,
                message=(
                    f"Sauvegarde créée avec succès, mais la purge des anciennes "
                    f"archives a échoué : {e}"
                ),
                backup_path=backup_info.path,
                backup_size_bytes=backup_info.size_bytes,
            )

        existing_names = [b.path.name for b in existing_backups]
        names_to_delete = compute_rotations_to_delete(
            existing_rotations=existing_names,
            max_rotations=request.keep,
        )

        backups_by_name = {b.path.name: b for b in existing_backups}
        deleted_count = 0
        for name in names_to_delete:
            backup = backups_by_name.get(name)
            if backup:
                self._port.delete_backup(backup)
                deleted_count += 1

        return RotateLogsResult(
            success=True,
            message=f"Sauvegarde créée avec succès : {backup_info.path.name}",
            backup_path=backup_info.path,
            backup_size_bytes=backup_info.size_bytes,
            deleted_count=deleted_count,
        )


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Crée un backup compressé d'un fichier log choisi par l'utilisateur
#   (menu 5.4), puis applique la limite de rétention (request.keep) en
#   supprimant les archives excédentaires les plus anciennes.
#
# Pourquoi dans application/commands/ (charte) :
# - Cas d'usage qui orchestre validation + création + purge.
# - Ne fait aucun tarfile/I/O direct (délégué à persistence_port).
# - Dépend de domain/logs/rotation.py (pur) pour le calcul de purge.
#
# Ce qu'il ne contient PAS :
# ❌ Pas d'import de infrastructure/storage/files/ (port reçu en paramètre)
# ❌ Pas de rendu UI
# ❌ Pas d'utilisation du pipeline (application/pipeline/) — suit le même
#   pattern simple, direct, que create_rule.py/delete_rule.py (validés
#   et testés cette session), pas le pattern ExecutionPlan/PipelineStep.
#
# Points clés :
# - RotateLogsRequest/RotateLogsResult : mêmes conventions que
#   CreateRuleRequest/CreateRuleResult (dataclasses simples).
# - Le port est injecté au constructeur, pas de closures nécessaires.
# - backup_info accessible directement dans le Result retourné par
#   execute() — pas de relecture indirecte via list_backups().
#
# Flux d'exécution :
# interfaces/cli/actions.py : action_5_4_rotate_logs(ctx)
#   ↓ résout le port via ctx.container.get_persistence_port()
#   ↓ construit RotateLogsRequest depuis la saisie utilisateur
# application/commands/rotate_logs.py : RotateLogsCommand.execute()
#   ↓ persistence_port.create_backup() / list_backups() / delete_backup()
#---------------------------------------------------------------------->
