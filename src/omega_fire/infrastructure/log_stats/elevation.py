# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
# Porte d'omega-log (infrastructure/privileged/elevation.py) le 2026-11-09 (OMEGA-FIRE_PLAN_LOGS_NIVEAU_SERV_LOG.md) : garder identique a la source.
"""Detection root + authentification sudo ponctuelle — ADAPTE depuis
omega-serv (core/platform_info.py::running_as_root +
infrastructure/services/systemd_service_manager.py::_run_privileged).
`authenticate_sudo` isole le `sudo -v` (rafraichit le cache
d'authentification sur le VRAI terminal, via run_interactive) des
operations fichier privilegiees elles-memes (privileged_file_ops.py) qui
suivent : une fois le cache sudo chaud, elles n'ont plus besoin d'un
terminal interactif."""
from __future__ import annotations

import os
from dataclasses import dataclass

from omega_fire.ports.log_process_runner import ProcessRunnerPort
from omega_fire.shared.i18n import _


class PermissionRequiredError(OSError):
    """Levee par un use case (process_ip.py, _log_reading.py...) quand
    une PermissionError survient SANS qu'un ProcessRunnerPort n'ait ete
    fourni pour retomber sur une operation privilegiee — signal destine
    a l'ecran TUI appelant : authentifier via `request_elevation()`
    (interfaces/tui/screens/_elevation.py) puis rappeler le MEME use
    case en passant cette fois `runner=container.process_runner`.

    `__reduce__` EXPLICITE (2026-10-04, plan de performance — voir
    infrastructure/concurrency/process_pool.py) : cette exception
    traverse desormais une frontiere de PROCESSUS (ProcessPoolExecutor)
    quand un calcul deporte rencontre un fichier protege — le
    `__reduce__` par defaut d'OSError reconstruit l'instance via
    `cls(*self.args)`, soit `cls(message_complet)` au lieu de
    `cls(path)` (double-encapsule le message, `.path` lui-meme restant
    correct via l'etat restaure separement) — sans consequence
    fonctionnelle (jamais affiche tel quel, seul `.path` est lu), mais
    corrige ici proprement plutot que laisse comme curiosite."""

    def __init__(self, path: str) -> None:
        super().__init__(_("Permission refusée sur {path} (élévation requise).").format(path=path))
        self.path = path

    def __reduce__(self) -> tuple:
        return (self.__class__, (self.path,))


def running_as_root() -> bool:
    """`os.getuid` n'existe pas hors POSIX - retourne False dans ce cas
    plutot que de lever (meme choix que omega-serv)."""
    return hasattr(os, "getuid") and os.getuid() == 0


@dataclass(frozen=True, slots=True)
class ElevationResult:
    success: bool
    message: str = ""


def authenticate_sudo(runner: ProcessRunnerPort) -> ElevationResult:
    """Authentifie/rafraichit le cache sudo AVANT toute operation fichier
    privilegiee. Toujours a appeler depuis un contexte ou le vrai
    terminal a ete libere (`OmegaScreen._maybe_suspend()`) - sudo lit son
    mot de passe sur ce terminal, jamais sur celui, virtuel, de
    Textual."""
    if running_as_root():
        return ElevationResult(success=True)
    code = runner.run_interactive(["sudo", "-v"])
    if code != 0:
        return ElevationResult(success=False, message=_("Authentification sudo échouée ou "
                                                        "annulée."))
    return ElevationResult(success=True)
