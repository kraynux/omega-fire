# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Scan de securite du 2026-11-21 : F1, F2, F3, F4, F6, F7, F8, F10 (F5 et F9 : --legacy-cli figee)."""
import asyncio
import os
import socket
import stat
from pathlib import Path

import pytest

from omega_fire.domain.log_stats.parser import extract_ip
from omega_fire.domain.logs.rotation_schedule import (
    build_rotation_cron_line,
    build_rotation_service_unit,
)
from omega_fire.infrastructure.backends.fail2ban.adapter import _create_like_parent
from omega_fire.infrastructure.desktop.browser_opener import session_environment
from omega_fire.infrastructure.probe import omega_serv_detector
from omega_fire.infrastructure.storage.files.archive_store import ArchiveStore
from omega_fire.infrastructure.storage.files.log_ip_removal import remove_ips_in_place
from omega_fire.interfaces.tui.app import OmegaFireApp


def test_f1_lien_a_la_place_du_log_refuse(tmp_path):
    cible = tmp_path / "ld.so.preload"
    log_dir = tmp_path / "log"
    log_dir.mkdir()
    (log_dir / "access.log").symlink_to(cible)
    with pytest.raises(OSError):
        _create_like_parent(str(log_dir / "access.log"))
    assert not cible.exists()


def test_f1_lien_dans_le_chemin_suivi_seulement_si_root(tmp_path):
    vrai = tmp_path / "etc"
    vrai.mkdir()
    (tmp_path / "log").symlink_to(vrai)  # lien d'un compte ordinaire
    with pytest.raises(OSError):
        _create_like_parent(str(tmp_path / "log" / "sub" / "access.log"))
    assert not (vrai / "sub").exists()


def test_f2_socket_x_d_un_autre_compte_ignoree(tmp_path):
    x11 = tmp_path / "x11"
    x11.mkdir()
    (x11 / "X0").write_text("pas une socket")
    sock = socket.socket(socket.AF_UNIX)
    try:
        sock.bind(str(x11 / "X1"))
        env = session_environment(os.getuid() + 12345, current={}, proc_dir=tmp_path / "proc",
                                  run_dir=tmp_path / "run", x11_dir=x11)
        assert env == {}  # ni le fichier ordinaire, ni la socket d'un autre compte
        mine = session_environment(os.getuid(), current={}, proc_dir=tmp_path / "proc",
                                   run_dir=tmp_path / "run", x11_dir=x11)
        assert mine.get("DISPLAY") == ":1"
    finally:
        sock.close()


def test_f3_nom_de_log_avec_balisage_ignore(tmp_path):
    log_dir = tmp_path / "var" / "log"
    log_dir.mkdir(parents=True)
    (log_dir / "access.log").write_text("")
    (log_dir / "[@click=app.screenshot('x')]a.log").write_text("")
    instance = type("I", (), {"root": tmp_path})()
    original = omega_serv_detector.magnet_info
    omega_serv_detector.magnet_info = lambda _instance: None
    try:
        names = [p.name for p in omega_serv_detector.instance_log_files(instance)]
    finally:
        omega_serv_detector.magnet_info = original
    assert names == ["access.log"]


def test_f3_f4_aucune_action_par_balisage():
    app = OmegaFireApp.__new__(OmegaFireApp)
    assert asyncio.run(app._broker_event("click", object(), None)) is False


def test_f4_premier_champ_non_ip_ignore(tmp_path):
    from omega_fire.interfaces.tui.screens.top_ips_screen import _count_ips

    log = tmp_path / "access.log"
    log.write_text(
        '[@click=app.screenshot()]203.0.113.9[/] - - [16/Nov/2026:02:48:52 +0000] "GET / HTTP/1.1" 200 10\n'
        '203.0.113.7 - - [16/Nov/2026:02:48:52 +0000] "GET / HTTP/1.1" 200 10\n'
    )
    counts = _count_ips(log, None)[0]
    assert counts == {"203.0.113.7": 1}


def test_f6_archive_jamais_lisible_par_les_autres(tmp_path):
    source = tmp_path / "auth.log"
    source.write_text("secret\n")
    archive = ArchiveStore(tmp_path / "backups").create_archive("backup_auth", [source])
    assert stat.S_IMODE(archive.stat().st_mode) & 0o007 == 0


def test_f7_ip_ancree_et_non_nom_d_utilisateur():
    assert extract_ip("sshd[1]: Invalid user 192.168.1.10 from 203.0.113.9 port 4242") == "203.0.113.9"
    assert extract_ip('203.0.113.7 - - [16/Nov/2026:02:48:52 +0000] "GET /from 1.2.3.4 port 5" 404 1') == "203.0.113.7"
    assert extract_ip("authentication failure; rhost=198.51.100.4  user=10.0.0.1") == "198.51.100.4"
    assert extract_ip("erreur 10.0.0.1 puis 10.0.0.2") == "10.0.0.1"


def test_f8_lien_jamais_reecrit(tmp_path):
    cible = tmp_path / "auth.log"
    cible.write_text("1.2.3.4 garde\n")
    lien = tmp_path / "access.log"
    lien.symlink_to(cible)
    with pytest.raises(OSError):
        remove_ips_in_place(lien, ["1.2.3.4"])
    assert cible.read_text() == "1.2.3.4 garde\n"


def test_f10_planificateurs_en_umask_007():
    assert "UMask=0007" in build_rotation_service_unit(python_executable="/p", project_root="/r")
    assert "umask 007;" in build_rotation_cron_line(python_executable="/p", project_root="/r")
    root = Path(__file__).resolve().parents[2]
    assert "umask 002" not in (root / "omega-fire.sh").read_text(encoding="utf-8")
    assert "chmod -R 2775" not in (root / "install.sh").read_text(encoding="utf-8")
