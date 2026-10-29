# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Lance `scp` pour l'import distant de la Bibliotheque de logs (menu 5.1). argv en liste
(domain/logs/remote_source.py::build_scp_command), jamais de shell."""
from __future__ import annotations

import subprocess
from dataclasses import dataclass

from omega_fire.shared.i18n import _


@dataclass(frozen=True, slots=True)
class ScpResult:
    ok: bool
    detail: str


def run_scp(command: list[str], timeout: float = 120.0) -> ScpResult:
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout,
                                   stdin=subprocess.DEVNULL, check=False)
    except FileNotFoundError:
        return ScpResult(False, _("scp introuvable"))
    except subprocess.TimeoutExpired:
        return ScpResult(False, _("délai dépassé ({value} s)").format(value=int(timeout)))
    if completed.returncode == 0:
        return ScpResult(True, "")
    return ScpResult(False, completed.stderr.strip() or _("code de retour {value}").format(value=completed.returncode))
