# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
# Porte d'omega-log (infrastructure/privileged/privileged_file_ops.py) le 2026-11-09 (OMEGA-FIRE_PLAN_LOGS_NIVEAU_SERV_LOG.md) : garder identique a la source.
"""Operations fichier privilegiees (sudo ponctuel) — complement de
application/guards/permission_guard.py pour les cas ou la delegation
par groupe ne suffit pas (ex. /var/log/audit, /var/log/fail2ban.log*,
root:root 600/700 — illisibles meme en etant dans le bon groupe).

Toujours appele APRES authenticate_sudo() (elevation.py) : le cache sudo
est alors chaud, chaque fonction ici capture stdout/stderr normalement
(ProcessRunnerPort.run()), sans jamais avoir besoin d'un terminal
interactif supplementaire.

Jamais de lecture/ecriture Python directe sur le chemin protege : tout
passe par une commande shell privilegiee (`sudo cat/tee/truncate/rm/cp`)
— c'est `sudo` qui verifie et autorise l'acces, pas ce module."""
from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from omega_fire.ports.log_process_runner import ProcessRunnerPort
from omega_fire.shared.i18n import _

_TIMEOUT_SECONDS = 10.0


@dataclass(frozen=True, slots=True)
class PrivilegedOpResult:
    success: bool
    content: str = ""
    message: str = ""


def read_file_privileged(runner: ProcessRunnerPort, path: str) -> PrivilegedOpResult:
    """Lecture complete via `sudo cat` — decodage errors="replace", meme
    convention que le reste du projet (domain/logs/parser.py et toutes
    les lectures non privilegiees)."""
    result = runner.run(["sudo", "cat", path], timeout=_TIMEOUT_SECONDS)
    if not result.ok:
        return PrivilegedOpResult(success=False, message=result.stderr.strip() or _("code {returncode}").format(returncode=result.returncode))
    return PrivilegedOpResult(success=True, content=result.stdout)


def read_new_bytes_privileged(runner: ProcessRunnerPort, path: str, offset: int) -> PrivilegedOpResult:
    """Lecture incrementale via `sudo tail -c +N` (N = 1er octet a lire,
    convention 1-indexee de `tail`, d'ou offset+1) — equivalent
    privilegie de LiveTailReader.read_new_lines(). `offset` attendu est
    TOUJOURS une taille en octets deja connue (stat() ne necessite pas
    la permission de lecture), jamais recalculee a partir du texte
    decode ici (un caractere de remplacement errors="replace" ne
    correspond pas a un octet, le suivi d'offset deraillerait sinon)."""
    if offset <= 0:
        return read_file_privileged(runner, path)
    result = runner.run(["sudo", "tail", "-c", f"+{offset + 1}", path], timeout=_TIMEOUT_SECONDS)
    if not result.ok:
        return PrivilegedOpResult(success=False, message=result.stderr.strip() or _("code {returncode}").format(returncode=result.returncode))
    return PrivilegedOpResult(success=True, content=result.stdout)


def truncate_file_privileged(runner: ProcessRunnerPort, path: str) -> PrivilegedOpResult:
    """Troncature EN PLACE via `sudo truncate -s 0` — meme inode,
    proprietaire/permissions inchanges (equivalent privilegie de
    purge_logs.py::purge_log_content, meme raisonnement : un service qui
    garde ce fichier ouvert ne doit jamais perdre son descripteur)."""
    result = runner.run(["sudo", "truncate", "-s", "0", path], timeout=_TIMEOUT_SECONDS)
    if not result.ok:
        return PrivilegedOpResult(success=False, message=result.stderr.strip() or _("code {returncode}").format(returncode=result.returncode))
    return PrivilegedOpResult(success=True)


def delete_file_privileged(runner: ProcessRunnerPort, path: str) -> PrivilegedOpResult:
    result = runner.run(["sudo", "rm", "-f", path], timeout=_TIMEOUT_SECONDS)
    if not result.ok:
        return PrivilegedOpResult(success=False, message=result.stderr.strip() or _("code {returncode}").format(returncode=result.returncode))
    return PrivilegedOpResult(success=True)


def overwrite_file_privileged(runner: ProcessRunnerPort, path: str, content: str) -> PrivilegedOpResult:
    """Remplacement COMPLET du contenu via un fichier temporaire que
    nous possedons (ecrit normalement) puis `sudo cp` vers la cible —
    jamais d'ecriture Python directe sur la cible. `cp` vers une
    destination EXISTANTE ecrase son contenu sans toucher a son
    proprietaire/permissions (contrairement a `mv`, qui remplacerait
    l'inode) : memes garanties que truncate_file_privileged ci-dessus."""
    fd, tmp_name = tempfile.mkstemp(prefix="omega-log-priv-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        result = runner.run(["sudo", "cp", "--", tmp_name, path], timeout=_TIMEOUT_SECONDS)
    finally:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
    if not result.ok:
        return PrivilegedOpResult(success=False, message=result.stderr.strip() or _("code {returncode}").format(returncode=result.returncode))
    return PrivilegedOpResult(success=True)


def append_file_privileged(runner: ProcessRunnerPort, path: str, content: str) -> PrivilegedOpResult:
    """Ajout en fin de fichier via `sudo tee -a`, alimente par stdin —
    pas de fichier temporaire necessaire ici (contrairement a
    overwrite_file_privileged : rien a faire lire a `cp`)."""
    result = runner.run(["sudo", "tee", "-a", "--", path], input_text=content, timeout=_TIMEOUT_SECONDS)
    if not result.ok:
        return PrivilegedOpResult(success=False, message=result.stderr.strip() or _("code {returncode}").format(returncode=result.returncode))
    return PrivilegedOpResult(success=True)


def stage_protected_copy_privileged(runner: ProcessRunnerPort, source: Path, dest_dir: Path) -> PrivilegedOpResult:
    """Copie un fichier protege vers `dest_dir` (que NOUS possedons deja)
    en conservant son nom exact, puis nous en rend proprietaire (`sudo
    chown`) — pour rotate_logs.py : permet de passer cette copie a
    ArchiveStore/tarfile (qui n'a, lui, jamais de privilege sudo) sans
    toucher au fichier source original. `cp` prealable (pas de lecture
    Python) : copie bit-a-bit, aucun risque d'encodage meme sur un log
    binaire. Le chemin stage dans `.content` en cas de succes."""
    dest = dest_dir / source.name
    copy_result = runner.run(["sudo", "cp", "--", str(source), str(dest)], timeout=_TIMEOUT_SECONDS)
    if not copy_result.ok:
        return PrivilegedOpResult(success=False, message=copy_result.stderr.strip() or _("code {returncode}").format(returncode=copy_result.returncode))

    chown_result = runner.run(
        ["sudo", "chown", f"{os.getuid()}:{os.getgid()}", str(dest)], timeout=_TIMEOUT_SECONDS,
    )
    if not chown_result.ok:
        dest.unlink(missing_ok=True)
        return PrivilegedOpResult(success=False, message=chown_result.stderr.strip() or _("code {returncode}").format(returncode=chown_result.returncode))

    return PrivilegedOpResult(success=True, content=str(dest))
