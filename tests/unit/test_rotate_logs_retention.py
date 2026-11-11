# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Rétention des sauvegardes de logs (correctif 2026-11-09) : on garde les `keep` archives les plus
RÉCENTES du même journal ; les archives des autres journaux ne comptent pas et ne sont jamais touchées."""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from omega_fire.application.commands.rotate_logs import RotateLogsCommand, RotateLogsRequest
from omega_fire.ports.persistence import BackupInfo


class FakePort:
    def __init__(self, existing: list[tuple[str, datetime]], new_name: str, new_at: datetime):
        self.backups = [BackupInfo(path=Path("/b") / n, created_at=t, size_bytes=1, components=[], metadata=None)
                        for n, t in existing]
        self.new = BackupInfo(path=Path("/b") / new_name, created_at=new_at, size_bytes=1, components=[], metadata=None)
        self.deleted: list[str] = []

    def create_backup(self, **_kwargs):
        self.backups.append(self.new)
        return self.new

    def list_backups(self, _backup_dir):
        # comme l'adaptateur réel : le plus récent d'abord
        return sorted(self.backups, key=lambda b: b.created_at, reverse=True)

    def delete_backup(self, backup):
        self.deleted.append(backup.path.name)
        self.backups.remove(backup)


def _name(stem: str, t: datetime) -> str:
    return f"backup_{stem}_{t:%Y%m%d_%H%M%S}.tar.gz"


def test_keeps_most_recent_of_same_log_only(tmp_path):
    log = tmp_path / "access.log"
    log.write_text("x\n")
    t0 = datetime(2026, 11, 1, 3, 45, 0)
    access = [(_name("access", t0 + timedelta(days=i)), t0 + timedelta(days=i)) for i in range(4)]
    others = [(_name("error", t0 + timedelta(days=i)), t0 + timedelta(days=i)) for i in range(5)]
    others.append((_name("access.old", t0), t0))  # autre journal au nom proche : jamais compté
    new_at = t0 + timedelta(days=10)
    port = FakePort(access + others, _name("access", new_at), new_at)

    result = RotateLogsCommand(port, Path("/b")).execute(RotateLogsRequest(source_path=str(log), keep=3))

    assert result.success
    assert result.deleted_count == 2
    assert port.deleted == [access[0][0], access[1][0]]  # les deux plus anciennes
    remaining = {b.path.name for b in port.backups}
    assert port.new.path.name in remaining
    assert {n for n, _ in others} <= remaining


def test_new_backup_never_deleted_with_keep_one(tmp_path):
    log = tmp_path / "audit.log"
    log.write_text("x\n")
    t0 = datetime(2026, 11, 1, 3, 45, 0)
    old = [(_name("audit", t0 + timedelta(hours=i)), t0 + timedelta(hours=i)) for i in range(3)]
    new_at = t0 + timedelta(days=1)
    port = FakePort(old, _name("audit", new_at), new_at)

    result = RotateLogsCommand(port, Path("/b")).execute(RotateLogsRequest(source_path=str(log), keep=1))

    assert result.deleted_count == 3
    assert [b.path.name for b in port.backups] == [port.new.path.name]
