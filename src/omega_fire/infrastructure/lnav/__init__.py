# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Infrastructure lnav subsystem.

Encapsule lnav en tant que moteur d'analyse externe : sous-processus dans
un pty, définitions de format embarquées (formats/omega_fire/*.json), et
le répondeur minimal de capacités terminal requis pour que lnav (basé sur
notcurses) démarre sans bloquer. Ne modifie jamais lnav lui-même.
"""
from omega_fire.infrastructure.lnav.pty_session import (
    CONFIG_DIR,
    TerminalResponder,
    kill_lnav,
    relay_osc52,
    resize_pty,
    spawn_lnav,
    wait_dead,
)

__all__ = [
    "CONFIG_DIR",
    "TerminalResponder",
    "kill_lnav",
    "relay_osc52",
    "resize_pty",
    "spawn_lnav",
    "wait_dead",
]
