# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Restore backup command.

Orchestrates the restoration of a compressed log backup (menu 5.5):
extracts the archive to a temporary location via the persistence port,
then merges or overwrites the target file according to the requested
mode. If overwriting, a safety backup of the current target is created
first via the same port.
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from omega_fire.infrastructure.exceptions import StorageError
from omega_fire.ports.persistence import BackupInfo


@dataclass
class RestoreBackupRequest:
    """Input for the restore backup use case."""
    backup_path: str
    target_dir: str
    mode: str = "append"  # "append" | "overwrite"

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.backup_path:
            errors.append("backup_path must not be empty")
        elif not Path(self.backup_path).exists():
            errors.append(f"Backup file not found: {self.backup_path}")
        if self.mode not in ("append", "overwrite"):
            errors.append(f"Invalid mode: {self.mode}")
        return errors

    def is_valid(self) -> bool:
        return len(self.validate()) == 0


@dataclass
class RestoreBackupResult:
    """Output of the restore backup use case."""
    success: bool
    message: str
    target_file: Optional[Path] = None
    safety_backup_path: Optional[Path] = None


class RestoreBackupCommand:
    """Use case: restore a compressed backup to its target file."""

    def __init__(self, persistence_port: Any, temp_dir: Path = Path("var/backups/_temp_restore")):
        self._port = persistence_port
        self._temp_dir = temp_dir

    def execute(self, request: RestoreBackupRequest) -> RestoreBackupResult:
        errors = request.validate()
        if errors:
            return RestoreBackupResult(success=False, message="; ".join(errors))

        backup_path = Path(request.backup_path)
        target_dir = Path(request.target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        target_dir_name = target_dir.name  # "logs", "blocklist", "exports"

        backup = BackupInfo(
            path=backup_path,
            created_at=datetime.fromtimestamp(backup_path.stat().st_mtime),
            size_bytes=backup_path.stat().st_size,
            components=[],
        )

        try:
            self._port.restore_backup(backup, dest_dir=self._temp_dir)
        except StorageError as e:
            return RestoreBackupResult(success=False, message=f"Échec de l'extraction : {e}")

        extracted_files = list(self._temp_dir.glob("*"))
        if not extracted_files:
            shutil.rmtree(self._temp_dir, ignore_errors=True)
            return RestoreBackupResult(success=False, message="L'archive extraite est vide.")

        extracted_file = extracted_files[0]
        target_file = target_dir / extracted_file.name

        safety_backup_path = None
        diag = ""

        try:
            if request.mode == "overwrite":
                if target_file.exists():
                    safety_info = self._port.create_backup(
                        backup_dir=Path("var/backups"),
                        source_paths=[target_file],
                        components=["safety_auto"],
                        metadata={"reason": "Sauvegarde automatique avant écrasement (5.5)"},
                    )
                    safety_backup_path = safety_info.path
                shutil.copy2(extracted_file, target_file)
                summary = "Remplacement complet (écrasement)"
            else:
                if target_file.exists():
                    if target_dir_name == "logs":
                        with open(extracted_file, "r", encoding="utf-8", errors="ignore") as src:
                            content = src.read()
                        separator = (
                            f"\n\n# ─── Restauration ajoutée le "
                            f"{datetime.now().strftime('%d/%m/%Y %H:%M:%S')} "
                            f"(depuis {backup_path.name}) ───\n"
                        )
                        with open(target_file, "a", encoding="utf-8") as dst:
                            dst.write(separator + content)
                        summary = "Fusion incrémentale (ajout, logs)"
                    else:
                        # Blocklist/exports : fusion sans doublon.
                        with open(target_file, "r", encoding="utf-8", errors="ignore") as f:
                            existing_ips = {
                                line.split()[0] for line in f
                                if line.strip() and not line.strip().startswith("#")
                            }

                        with open(extracted_file, "r", encoding="utf-8", errors="ignore") as f:
                            new_lines = [
                                line.rstrip("\n") for line in f
                                if line.strip() and not line.strip().startswith("#")
                            ]

                        lines_to_add = []
                        for line in new_lines:
                            tokens = line.split()
                            if not tokens:
                                continue
                            ip = tokens[0]
                            if ip not in existing_ips:
                                lines_to_add.append(line)
                                existing_ips.add(ip)

                        if lines_to_add:
                            with open(target_file, "a", encoding="utf-8") as dst:
                                dst.write("\n" + "\n".join(lines_to_add) + "\n")

                        diag = (
                            f" ({len(lines_to_add)} nouvelle(s) entrée(s) ajoutée(s), "
                            f"{len(new_lines) - len(lines_to_add)} déjà présente(s) ignorée(s))"
                        )
                        summary = "Fusion incrémentale (ajout, sans doublon)"
                else:
                    shutil.copy2(extracted_file, target_file)
                    summary = "Fusion incrémentale (fichier cible créé, aucun doublon possible)"
        finally:
            shutil.rmtree(self._temp_dir, ignore_errors=True)

        return RestoreBackupResult(
            success=True,
            message=f"Restauration effectuée avec succès : {summary}.{diag}",
            target_file=target_file,
            safety_backup_path=safety_backup_path,
        )


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Restaure un backup compressé (menu 5.5) : extraction via le port
#   persistence, puis fusion ou écrasement du fichier cible.
#
# Diagnostic temporaire :
# - Le message de résultat inclut désormais [DIAGNOSTIC : ...] pour le
#   mode append hors logs, afin de vérifier concrètement combien de
#   lignes sont lues/ajoutées/rejetées à chaque restauration. À retirer
#   une fois le comportement confirmé correct.
#----------------------------------------------------------------------
