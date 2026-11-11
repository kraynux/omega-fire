# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Correctifs du 2026-11-10 (etude de l'interconnecteur, etape 1) : adresses protegees, duree des bans
transferes vers nftables, retrait d'IP sur place dans un log vivant, journal cree au nom du proprietaire
de son dossier, jail deja defini sur disque refuse."""
from __future__ import annotations

import stat
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from omega_fire.domain.fail2ban.exceptions import JailAlreadyExistsError as DomainJailAlreadyExistsError
from omega_fire.domain.ip_blacklist.protected import is_protected, split_protected
from omega_fire.infrastructure.backends.fail2ban.adapter import (
    Fail2banAdapter,
    _create_like_parent,
    parse_ban_remaining_seconds,
)
from omega_fire.infrastructure.backends.nftables.serializer import NftSerializer
from omega_fire.infrastructure.storage.files.log_ip_removal import remove_ips_in_place


@pytest.mark.parametrize("address", [
    "127.0.0.1", "::1", "100.106.10.47", "fd7a:115c:a1e0::5", "192.168.1.20", "10.0.0.3",
    "172.16.4.1", "169.254.1.1", "fe80::1", "fd00::1", "::ffff:192.168.1.20", "192.168.1.0/24",
])
def test_protected_addresses(address):
    assert is_protected(address)


@pytest.mark.parametrize("address", ["203.0.113.7", "100.12.196.99", "2001:db8::1", "8.8.8.8", "pas-une-ip"])
def test_public_addresses_not_protected(address):
    assert not is_protected(address)


def test_split_protected_keeps_order():
    kept, protected = split_protected(["203.0.113.7", "192.168.1.2", "198.51.100.1", "127.0.0.1"])
    assert kept == ["203.0.113.7", "198.51.100.1"]
    assert protected == ["192.168.1.2", "127.0.0.1"]


def test_parse_ban_remaining_seconds():
    output = (
        "203.0.113.7 \t2026-11-10 10:00:00 + 600 = 2026-11-10 10:10:00\n"
        "198.51.100.1 \t2026-11-10 09:00:00 + -1 = 2038-01-19 04:14:07\n"
        "192.0.2.5 \t2026-11-10 08:00:00 + 60 = 2026-11-10 08:01:00\n"
        "ligne illisible\n"
    )
    remaining = parse_ban_remaining_seconds(output, datetime(2026, 11, 10, 10, 5, 0))
    assert remaining == {"203.0.113.7": 300, "198.51.100.1": None, "192.0.2.5": 0}


def test_nft_ban_command_carries_timeout():
    cmd = NftSerializer().build_ban_command(ip="203.0.113.7", set_name="blackhole", comment="Jail 'sshd'",
                                            timeout_seconds=300)
    assert cmd[-1] == '{ 203.0.113.7 timeout 300s comment "Jail \'sshd\'" }'
    assert NftSerializer().build_ban_command(ip="203.0.113.7", set_name="blackhole")[-1] == "{ 203.0.113.7 }"


def test_remove_ips_in_place_keeps_inode_mode_and_raw_bytes(tmp_path):
    log = tmp_path / "access.log"
    log.write_bytes(b"1.2.3.4 - GET /\n" + b"9.9.9.9 - caf\xe9 \xff\n" + b"1.2.3.45 - GET /x\n" + b"1.2.3.4 - POST\n")
    log.chmod(0o640)
    inode = log.stat().st_ino
    counts = remove_ips_in_place(log, ["1.2.3.4"])
    assert counts == {"1.2.3.4": 2}
    assert log.read_bytes() == b"9.9.9.9 - caf\xe9 \xff\n" + b"1.2.3.45 - GET /x\n"  # octets bruts gardes
    assert log.stat().st_ino == inode  # meme fichier : les ecrivains gardent leur descripteur
    assert stat.S_IMODE(log.stat().st_mode) == 0o640


def test_remove_ips_in_place_untouched_when_absent(tmp_path):
    log = tmp_path / "access.log"
    log.write_bytes(b"5.6.7.8 - GET /\n")
    before = log.stat().st_mtime_ns
    assert remove_ips_in_place(log, ["1.2.3.4"]) == {"1.2.3.4": 0}
    assert log.stat().st_mtime_ns == before


def test_create_like_parent_makes_shared_log(tmp_path):
    target = tmp_path / "var" / "log" / "waf-alerts.log"
    _create_like_parent(str(target))
    assert target.exists()
    assert stat.S_IMODE(target.stat().st_mode) == 0o664
    assert target.stat().st_uid == tmp_path.stat().st_uid
    _create_like_parent(str(target))  # deja present : rien ne change


def test_create_jail_refuses_section_defined_in_another_file(tmp_path):
    jail_d = tmp_path / "jail.d"
    jail_d.mkdir()
    (jail_d / "omega-jail-omega-serv-scan.conf").write_text("# Genere par Omega-Jail\n[omega-serv-scan]\nenabled = false\n")
    adapter = Fail2banAdapter()
    with patch.object(adapter, "list_jails", return_value=[]), patch.object(adapter, "_run_raw"):
        with pytest.raises(DomainJailAlreadyExistsError):
            adapter.create_jail("omega-serv-scan", "omega-serv-scan", str(tmp_path / "x.log"), jail_d_dir=str(jail_d))
    assert not (jail_d / "omega-serv-scan.conf").exists()
    assert not (tmp_path / "x.log").exists()

