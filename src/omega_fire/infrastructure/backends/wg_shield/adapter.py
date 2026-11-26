# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Bouclier du port WireGuard sur la machine (ports/wg_shield.py) : lectures par omega-lib, commandes lancees
directement (omega-fire est root), fichiers prepares sous var/bouclier-wg/."""

from __future__ import annotations

import os
import subprocess
import time
from collections.abc import Sequence
from pathlib import Path

from omega_lib.infrastructure.shield.machine import (
    kernel_modules_ready,
    kernel_release,
    physical_devices,
    read_settings,
    read_status,
    tailscaled_port,
)
from omega_lib.shield.models import ShieldSettings, ShieldStatus
from omega_lib.shield.system import NONE, OPENRC, RUNIT, SCRIPT_PATH, SYSTEMD

from omega_fire.core.enums import ServiceManagerType
from omega_fire.infrastructure.config.paths import VAR_DIR
from omega_fire.ports.wg_shield import CommandLine

STAGING_DIR = VAR_DIR / "bouclier-wg"
_INIT_NAMES = {ServiceManagerType.SYSTEMD: SYSTEMD, ServiceManagerType.OPENRC: OPENRC,
               ServiceManagerType.RUNIT: RUNIT}


def _run_one(command: Sequence[str]) -> CommandLine:
    try:
        done = subprocess.run(list(command), capture_output=True, text=True, timeout=60, check=False,
                              stdin=subprocess.DEVNULL, env={**os.environ, "LC_ALL": "C", "LANG": "C"})
    except (OSError, subprocess.TimeoutExpired) as error:
        return CommandLine(tuple(command), 127, str(error))
    return CommandLine(tuple(command), done.returncode, (done.stdout + done.stderr).strip()[-2000:])


class SystemWgShield:
    def __init__(self, staging: Path = STAGING_DIR) -> None:
        self._staging = staging

    def init_name(self) -> str:
        try:
            from omega_fire.infrastructure.backends.service_manager.detector import (
                ServiceManagerDetector,
            )

            return _INIT_NAMES.get(ServiceManagerDetector().detect(), NONE)
        except Exception:  # noqa: BLE001 - systeme d'init introuvable : pas de remise au demarrage
            return NONE

    def runit_dir(self) -> str:
        for candidate in ("/var/service", "/run/runit/service", "/etc/service", "/service"):
            if Path(candidate).is_dir():
                return candidate
        return "/var/service"

    def kernel_release(self) -> str:
        return kernel_release()

    def modules_ready(self) -> bool:
        return kernel_modules_ready()

    def tailscaled_port(self) -> int:
        return tailscaled_port()

    def devices(self) -> tuple[str, ...]:
        return physical_devices()

    def settings(self) -> ShieldSettings | None:
        return read_settings()

    def status(self, *, refresh: bool = True) -> ShieldStatus | None:
        if refresh and os.geteuid() == 0 and Path(SCRIPT_PATH).is_file():
            _run_one((SCRIPT_PATH, "etat"))
        return read_status()

    def stage(self, files: dict[str, str]) -> str:
        self._staging.mkdir(parents=True, exist_ok=True)
        os.chmod(self._staging, 0o750)
        for name, content in files.items():
            temporary = self._staging / f".{name}.tmp"
            temporary.write_text(content, encoding="utf-8")
            temporary.replace(self._staging / name)
        return str(self._staging)

    def run(self, commands: Sequence[tuple[str, ...]], *, keep_going: bool = False) -> list[CommandLine]:
        lines: list[CommandLine] = []
        for command in commands:
            line = _run_one(command)
            lines.append(line)
            if line.code != 0 and not keep_going:
                break
        return lines

    def now(self) -> float:
        return time.time()
