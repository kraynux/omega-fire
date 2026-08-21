# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Persistence adapter — file-based implementation of PersistencePort.

Implements the BackupInfo-related operations of PersistencePort using
ArchiveStore for the actual tar.gz I/O. This adapter is the bridge
between application/ (via the port) and the concrete archive mechanics.

The Snapshot-related operations (create_snapshot, list_snapshots,
restore_snapshot, delete_snapshot) are out of scope for this adapter
for now — they belong to the separate full-state snapshot feature
(menus 7.1/7.2/3.4) and are not yet implemented here.
"""
from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime
from omega_fire.ports.persistence import BackupInfo, PersistencePort, Snapshot
from omega_fire.infrastructure.storage.files.archive_store import (
    ArchiveStore,
    ArchiveStoreError,
)
from omega_fire.infrastructure.exceptions import StorageError


class FileBackupAdapter:
    """Implements the backup-related subset of PersistencePort.

    Uses ArchiveStore for tar.gz creation, extraction, listing and
    deletion. Does not implement snapshot operations (see class
    docstring above).
    """

    def __init__(self, archive_store: ArchiveStore):
        self._archive_store = archive_store

    def create_backup(
        self,
        backup_dir: Path,
        *,
        source_paths: list[Path],
        components: list[str] | None = None,
        metadata: dict[str, str] | None = None,
        archive_name: str | None = None,
    ) -> BackupInfo:
        """Create a backup archive from one or more source paths.

        Args:
            backup_dir: destination directory (must match the
                ArchiveStore's configured base_dir in practice).
            source_paths: files/directories to include in the archive.
            components: labels describing what was backed up
                (e.g. ["logs"], stored in BackupInfo for display).
            metadata: optional extra metadata.
            archive_name: optional explicit archive name (without
                extension). If omitted, a timestamped name is generated
                from the first source path's stem.

        Raises:
            StorageError: if archive creation fails.
        """
        if not source_paths:
            raise StorageError("create_backup: source_paths must not be empty")

        if archive_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            stem = source_paths[0].stem
            archive_name = f"backup_{stem}_{timestamp}"

        try:
            archive_path = self._archive_store.create_archive(
                archive_name=archive_name,
                source_paths=source_paths,
            )
            info = self._archive_store.get_archive_info(archive_path)
        except ArchiveStoreError as e:
            raise StorageError(f"Failed to create backup: {e}") from e

        return BackupInfo(
            path=archive_path,
            created_at=datetime.fromisoformat(info["created_at"]),
            size_bytes=info["size_bytes"],
            components=components or [],
            metadata=metadata,
        )

    def restore_backup(self, backup: BackupInfo, *, dest_dir: Path) -> None:
        """Extract a backup archive to a destination directory.

        Args:
            backup: the backup to restore.
            dest_dir: destination directory for extraction.

        Raises:
            StorageError: if extraction fails.
        """
        try:
            self._archive_store.extract_archive(backup.path, dest_dir)
        except ArchiveStoreError as e:
            raise StorageError(f"Failed to restore backup {backup.path}: {e}") from e

    def list_backups(self, backup_dir: Path) -> list[BackupInfo]:
        """List available backup archives, most recent first.

        Args:
            backup_dir: directory to list (informational; ArchiveStore
                is already scoped to its own base_dir).

        Raises:
            StorageError: if listing fails.
        """
        try:
            archive_paths = self._archive_store.list_archives()
            infos = []
            for path in archive_paths:
                raw = self._archive_store.get_archive_info(path)
                infos.append(
                    BackupInfo(
                        path=path,
                        created_at=datetime.fromisoformat(raw["created_at"]),
                        size_bytes=raw["size_bytes"],
                        components=[],
                        metadata=None,
                    )
                )
        except ArchiveStoreError as e:
            raise StorageError(f"Failed to list backups in {backup_dir}: {e}") from e

        return sorted(infos, key=lambda b: b.created_at, reverse=True)

    def delete_backup(self, backup: BackupInfo) -> None:
        """Delete a backup archive.

        Args:
            backup: the backup to delete.
        """
        self._archive_store.delete_archive(backup.path)

    # ------------------------------------------------------------------
    # Snapshot operations — 
    # ------------------------------------------------------------------

    def _get_snapshots_dir(self) -> Path:
        """Dedicated subdirectory for full-state snapshots, separate
        from individual file backups (menus 5.4/5.5/5.6)."""
        snapshots_dir = self._archive_store._base_dir / "snapshots"
        snapshots_dir.mkdir(parents=True, exist_ok=True)
        return snapshots_dir

    def create_snapshot(
        self,
        *,
        banned_ips: list,
        rules: list,
        jails: list,
        description: str = "",
        origin: str = "manual",
    ) -> Snapshot:
        """Create a full-state snapshot (menu 7.1).

        Builds the domain Snapshot in memory (via
        domain/persistence/service.py), serializes it to JSON, and
        compresses it into a dedicated snapshots/ subdirectory.

        Raises:
            StorageError: if snapshot creation fails.
        """
        from omega_fire.domain.persistence.service import PersistenceService
        from omega_fire.domain.persistence.exceptions import PersistenceError

        try:
            service = PersistenceService()
            backup_result = service.create_full_backup(
                banned_ips=banned_ips,
                rules=rules,
                jails=jails,
                description=description,
                origin=origin,
            )
        except PersistenceError as e:
            raise StorageError(f"Failed to build snapshot content: {e}") from e

        domain_snapshot = backup_result.snapshot
        snapshot_id = domain_snapshot.metadata.snapshot_id

        json_data = self._serialize_domain_snapshot(domain_snapshot)

        snapshots_dir = self._get_snapshots_dir()
        temp_json_path = snapshots_dir / f"_tmp_{snapshot_id}.json"
        temp_json_path.write_text(
            json.dumps(json_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        try:
            snapshot_archive_store = ArchiveStore(base_dir=snapshots_dir)
            archive_path = snapshot_archive_store.create_archive(
                archive_name=snapshot_id,
                source_paths=[temp_json_path],
            )
        except ArchiveStoreError as e:
            raise StorageError(f"Failed to compress snapshot: {e}") from e
        finally:
            temp_json_path.unlink(missing_ok=True)

        return Snapshot(
            id=snapshot_id,
            created_at=domain_snapshot.metadata.created_at,
            blacklist_count=backup_result.blacklist_count,
            rules_count=backup_result.rules_count,
            jails_count=backup_result.fail2ban_count,
            description=description,
            origin=domain_snapshot.metadata.origin.value,
        )

    def list_snapshots(self) -> list[Snapshot]:
        """List all available snapshots, most recent first."""
        snapshots_dir = self._get_snapshots_dir()
        results: list[Snapshot] = []

        for archive_path in snapshots_dir.glob("*.tar.gz"):
            try:
                domain_snapshot = self._read_snapshot_archive(archive_path)
            except Exception:
                continue

            results.append(Snapshot(
                id=domain_snapshot.metadata.snapshot_id,
                created_at=domain_snapshot.metadata.created_at,
                blacklist_count=domain_snapshot.content.total_bans,
                rules_count=domain_snapshot.content.total_rules,
                jails_count=domain_snapshot.content.total_jails,
                description=domain_snapshot.metadata.description,
                origin=domain_snapshot.metadata.origin.value,
            ))

        return sorted(results, key=lambda s: s.created_at, reverse=True)

    def restore_snapshot(self, snapshot_id: str) -> None:
        """Not directly implemented here — restoration requires
        applying data to live backends, which this file-only adapter
        does not have access to. Use get_snapshot_content() (below)
        from application/ to retrieve the data, then apply it via the
        appropriate backend adapters."""
        raise NotImplementedError(
            "restore_snapshot() requires backend adapters to apply the "
            "restored state — use get_snapshot_content() and apply the "
            "result via application/commands/restore_state.py instead."
        )

    def delete_snapshot(self, snapshot_id: str) -> None:
        """Delete a snapshot archive by ID."""
        snapshots_dir = self._get_snapshots_dir()
        archive_path = snapshots_dir / f"{snapshot_id}.tar.gz"
        if archive_path.exists():
            archive_path.unlink()

    def update_snapshot_description(self, snapshot_id: str, new_description: str) -> bool:
        """Update only the description of an existing snapshot.

        Decompresses the existing archive, rewrites description in the
        deserialized domain Snapshot, re-serializes and recompresses
        under the EXACT SAME snapshot_id / filename — never touches the
        identifier used by delete_snapshot()/get_snapshot_content()/
        list_snapshots() for lookups. See PersistencePort docstring for
        why this is deliberately not a rename.

        Returns:
            True if the snapshot was found and updated, False if no
            snapshot with this ID exists.
        """
        snapshots_dir = self._get_snapshots_dir()
        archive_path = snapshots_dir / f"{snapshot_id}.tar.gz"
        if not archive_path.exists():
            return False

        try:
            domain_snapshot = self._read_snapshot_archive(archive_path)
        except Exception as e:
            raise StorageError(f"Failed to read snapshot {snapshot_id} for update: {e}") from e

        domain_snapshot.metadata.description = new_description
        json_data = self._serialize_domain_snapshot(domain_snapshot)

        temp_json_path = snapshots_dir / f"_tmp_{snapshot_id}.json"
        temp_json_path.write_text(
            json.dumps(json_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        try:
            # Écrase l'archive existante : create_archive() ouvre en mode
            # "w:gz" (voir ArchiveStore), donc un nom déjà présent est
            # remplacé plutôt que dupliqué — pas de nettoyage manuel requis.
            snapshot_archive_store = ArchiveStore(base_dir=snapshots_dir)
            snapshot_archive_store.create_archive(
                archive_name=snapshot_id,
                source_paths=[temp_json_path],
            )
        except ArchiveStoreError as e:
            raise StorageError(f"Failed to recompress snapshot {snapshot_id}: {e}") from e
        finally:
            temp_json_path.unlink(missing_ok=True)

        return True

    def get_snapshot_content(self, snapshot_id: str):
        """Read and return the full domain Snapshot (metadata + content)
        for a given ID — used by restore flows that need the actual
        banned IPs / rules / jails, not just the summary counts.

        Returns:
            The domain Snapshot object (domain/persistence/snapshots.py),
            or None if not found.
        """
        snapshots_dir = self._get_snapshots_dir()
        archive_path = snapshots_dir / f"{snapshot_id}.tar.gz"
        if not archive_path.exists():
            return None
        try:
            return self._read_snapshot_archive(archive_path)
        except Exception:
            return None

    def _read_snapshot_archive(self, archive_path: Path):
        """Extract and deserialize a snapshot archive into a domain Snapshot."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            self._archive_store.extract_archive(archive_path, Path(tmp_dir))
            json_files = list(Path(tmp_dir).glob("*.json"))
            if not json_files:
                raise StorageError(f"No JSON content found in {archive_path}")
            data = json.loads(json_files[0].read_text(encoding="utf-8"))
            return self._deserialize_domain_snapshot(data)

    def _serialize_domain_snapshot(self, domain_snapshot) -> dict:
        """Convert a domain Snapshot (dataclasses + enums) into a plain
        JSON-serializable dict."""
        meta = domain_snapshot.metadata
        content = domain_snapshot.content

        return {
            "metadata": {
                "snapshot_id": meta.snapshot_id,
                "created_at": meta.created_at.isoformat(),
                "scope": meta.scope.value,
                "description": meta.description,
                "version": meta.version,
                "source_system": meta.source_system,
                "status": meta.status.value,
                "origin": meta.origin.value,
            },
            "content": {
                "blacklist": {
                    "banned_ips": content.blacklist.banned_ips if content.blacklist else [],
                } if content.blacklist else None,
                "rules": {
                    "rules": content.rules.rules if content.rules else [],
                } if content.rules else None,
                "fail2ban": {
                    "jails": content.fail2ban.jails if content.fail2ban else [],
                } if content.fail2ban else None,
                "total_bans": content.total_bans,
                "total_rules": content.total_rules,
                "total_jails": content.total_jails,
            },
        }

    def _deserialize_domain_snapshot(self, data: dict):
        """Reconstruct a domain Snapshot from its serialized dict form."""
        from datetime import datetime
        from omega_fire.domain.persistence.snapshots import (
            Snapshot as DomainSnapshot,
            SnapshotMetadata,
            SnapshotContent,
            SnapshotScope,
            SnapshotStatus,
            SnapshotOrigin,
            BlacklistSnapshot,
            RulesSnapshot,
            Fail2banSnapshot,
        )

        meta_raw = data["metadata"]
        metadata = SnapshotMetadata(
            snapshot_id=meta_raw["snapshot_id"],
            created_at=datetime.fromisoformat(meta_raw["created_at"]),
            scope=SnapshotScope(meta_raw["scope"]),
            description=meta_raw.get("description", ""),
            version=meta_raw.get("version", "1.0"),
            source_system=meta_raw.get("source_system", "omega-fire"),
            status=SnapshotStatus(meta_raw["status"]),
            origin=SnapshotOrigin(meta_raw.get("origin", "manual")),
        )

        content_raw = data["content"]
        content = SnapshotContent(
            blacklist=BlacklistSnapshot(
                banned_ips=content_raw["blacklist"]["banned_ips"],
                count=len(content_raw["blacklist"]["banned_ips"]),
            ) if content_raw.get("blacklist") else None,
            rules=RulesSnapshot(
                rules=content_raw["rules"]["rules"],
                count=len(content_raw["rules"]["rules"]),
            ) if content_raw.get("rules") else None,
            fail2ban=Fail2banSnapshot(
                jails=content_raw["fail2ban"]["jails"],
                count=len(content_raw["fail2ban"]["jails"]),
            ) if content_raw.get("fail2ban") else None,
            total_bans=content_raw.get("total_bans", 0),
            total_rules=content_raw.get("total_rules", 0),
            total_jails=content_raw.get("total_jails", 0),
        )

        return DomainSnapshot(metadata=metadata, content=content)


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Implémente la partie BackupInfo de PersistencePort (create/restore/
#   list/delete_backup) en s'appuyant sur ArchiveStore existant.
# - Les opérations Snapshot (état complet firewall, menus 7.x/3.4) ne
#   sont volontairement PAS implémentées ici (NotImplementedError
#   explicite) — sujet séparé, à traiter plus tard.
#
# Pourquoi dans infrastructure/ (charte) :
# - Implémentation concrète d'un port (PersistencePort).
# - Dépend de ArchiveStore (infrastructure/) et convertit ses résultats
#   bruts (dict) en objets du contrat (BackupInfo).
#
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier (pas de décision sur QUAND sauvegarder)
# ❌ Pas d'accès direct à tarfile (délégué à ArchiveStore)
# ❌ Pas d'appel depuis interfaces/ (c'est application/ qui l'utilisera
#   via le port, câblé par app/dependency_container.py)
#
# Points clés :
# - create_backup() : accepte source_paths (liste), génère un nom
#   d'archive horodaté si non fourni.
# - Toutes les erreurs ArchiveStoreError sont traduites en StorageError
#   (hiérarchie d'exceptions infrastructure/, charte section 5).
# - update_snapshot_description() : modifie UNIQUEMENT la description
#   d'un snapshot existant (décompresse, réécrit, recompresse sous le
#   MÊME snapshot_id) — jamais de renommage, pour ne jamais désynchroniser
#   l'ID utilisé par delete_snapshot()/get_snapshot_content()/list_snapshots()
#
# Comment il sera utilisé (aperçu) :
# - app/dependency_container.py l'instanciera comme persistence_adapter,
#   avec un ArchiveStore pointant vers var/backups/.
# - application/commands/rotate_logs.py, restore_backup.py,
#   purge_backups.py l'appelleront via un accesseur du container.
# - interfaces/cli/actions.py (menu 7.2) appellera
#   update_snapshot_description() pour l'option "Modifier la description"
#----------------------------------------------------------------------
#----------------------------------------------------------------------
