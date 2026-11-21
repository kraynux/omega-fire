# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""ufw et firewalld, pour `omega-fire.sh port ouvrir` (ports/host_firewall.py). Sorties lues en LC_ALL=C (ufw
traduit ses messages). firewalld : règle riche ajoutée au runtime ET en permanent (survit au redémarrage sans
recharger toute la configuration)."""

from __future__ import annotations

import ipaddress
import os
import shutil
import subprocess
from collections.abc import Callable, Sequence

from omega_fire.ports.host_firewall import ADDED, ALREADY, FAILED

Run = Callable[[Sequence[str]], tuple[int, str]]


def _run(command: Sequence[str]) -> tuple[int, str]:
    try:
        result = subprocess.run(
            list(command),
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ, "LC_ALL": "C", "LANG": "C"},
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return 127, str(error)
    return result.returncode, (result.stdout + result.stderr).strip()


class SystemHostFirewall:
    def __init__(self, run: Run = _run, which: Callable[[str], str | None] = shutil.which) -> None:
        self._run = run
        self._which = which

    def active_name(self) -> str:
        if self._which("ufw"):
            code, output = self._run(["ufw", "status"])
            if code == 0 and output.splitlines()[:1] == ["Status: active"]:
                return "ufw"
        if self._which("firewall-cmd"):
            code, output = self._run(["firewall-cmd", "--state"])
            if code == 0 and output.strip() == "running":
                return "firewalld"
        return ""

    def allow(self, port: int, source: str, comment: str) -> tuple[str, str]:
        name = self.active_name()
        if name == "ufw":
            code, output = self._run(["ufw", "allow", "proto", "tcp", "from", source, "to", "any", "port",
                                      str(port), "comment", comment])
            if code != 0:
                return FAILED, output
            added = "Rule added" in output or "Rules updated" in output
            return (ALREADY if "Skipping" in output and not added else ADDED), output
        if name == "firewalld":
            family = "ipv6" if ipaddress.ip_network(source, strict=False).version == 6 else "ipv4"
            rule = (f'rule family="{family}" source address="{source}" port port="{port}" protocol="tcp" '
                    "accept")
            states = []
            for extra in ([], ["--permanent"]):
                code, output = self._run(["firewall-cmd", *extra, f"--add-rich-rule={rule}"])
                if code != 0 and "ALREADY_ENABLED" not in output:
                    return FAILED, output
                states.append("ALREADY_ENABLED" in output)
            return (ALREADY if all(states) else ADDED), ""
        return FAILED, "no active host firewall"
