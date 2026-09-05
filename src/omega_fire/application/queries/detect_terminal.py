# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Use case : detecter le terminal et resoudre son profil de rendu."""
from __future__ import annotations

from omega_lib.terminal.models import TerminalProfile
from omega_lib.terminal.service import resolve_render_profile

from omega_fire.ports.terminal_detector import TerminalDetector


def detect_terminal(*, terminal_detector: TerminalDetector) -> TerminalProfile:
    signals = terminal_detector.detect()
    return resolve_render_profile(signals)
