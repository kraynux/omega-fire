# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Journal des bans publie par omega-fire (plan omega-connect, phase 3, 2026-11-21)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
from omega_lib.infrastructure.synchro.ban_journal import (
    read_active_bans,
    read_ban_journal,
)

from omega_fire.infrastructure.synchro import ban_journal
from omega_fire.infrastructure.synchro.ban_journal import (
    BanJournalingFirewall,
    resync_ban_state,
)


@dataclass
class _Entry:
    ip: str


class _FakeFirewall:
    def __init__(self, ok: bool = True) -> None:
        self.banned: set[str] = set()
        self.ok = ok

    def is_available(self) -> bool:
        return True

    def list_bans(self) -> list[_Entry]:
        return [_Entry(ip) for ip in sorted(self.banned)]

    def ban_ip(self, ip, comment: str = "") -> bool:
        if self.ok:
            self.banned.update(ip if isinstance(ip, list) else [ip])
        return self.ok

    def unban_ip(self, ip) -> bool:
        self.banned.difference_update(ip if isinstance(ip, list) else [ip])
        return True

    def ban_single_ip(self, ip, *, reason: str = "", timeout_seconds: int | None = None) -> None:
        self.banned.add(str(ip))

    def flush(self) -> int:
        count = len(self.banned)
        self.banned.clear()
        return count

    def get_stats(self) -> str:
        return "stats"


@pytest.fixture
def zone(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / "bans").mkdir()
    monkeypatch.setenv("OMEGA_SYNCHRO_DIR", str(tmp_path))
    monkeypatch.setattr(ban_journal, "_is_root", lambda: True)
    return tmp_path


def _wrap(fake: _FakeFirewall) -> BanJournalingFirewall:
    wrapper: BanJournalingFirewall
    wrapper = BanJournalingFirewall(fake, lambda: resync_ban_state([wrapper]))
    return wrapper


def _active(zone: Path) -> set[str]:
    result = read_active_bans(zone / "bans" / "actifs.json")
    return {e.network for e in result.value.entries} if result.value else set()


def test_ban_et_levee_publies(zone: Path) -> None:
    firewall = _wrap(_FakeFirewall())
    assert firewall.ban_ip(["203.0.113.7", "198.51.100.4"], comment="manuel") is True
    firewall.ban_single_ip("192.0.2.1", reason="transfert sshd", timeout_seconds=3600)
    assert _active(zone) == {"203.0.113.7/32", "198.51.100.4/32", "192.0.2.1/32"}
    firewall.unban_ip("203.0.113.7")
    assert _active(zone) == {"198.51.100.4/32", "192.0.2.1/32"}
    events = read_ban_journal(zone / "bans" / "journal.jsonl").events
    assert all(e.origin == "omega-fire:manual" for e in events)
    transfer = next(e for e in events if e.network == "192.0.2.1/32")
    assert transfer.expires_at is not None and transfer.reason == "transfert sshd"
    assert firewall.get_stats() == "stats"  # le reste de l'interface passe tel quel


def test_vidage_et_echec_resynchronisent(zone: Path) -> None:
    fake = _FakeFirewall()
    firewall = _wrap(fake)
    firewall.ban_ip(["203.0.113.7"])
    assert firewall.flush() == 1
    assert _active(zone) == set()
    fake.ok = False
    fake.banned.add("198.51.100.4")  # pose hors d'omega-fire, retrouve par la resynchronisation
    assert firewall.ban_ip("192.0.2.9") is False
    assert _active(zone) == {"198.51.100.4/32"}


def test_sans_zone_ni_root_le_pare_feu_n_est_pas_affecte(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OMEGA_SYNCHRO_DIR", str(tmp_path / "absente"))
    fake = _FakeFirewall()
    firewall = _wrap(fake)
    assert firewall.ban_ip("203.0.113.7") is True
    assert fake.banned == {"203.0.113.7"}
    assert not (tmp_path / "absente").exists()
