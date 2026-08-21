# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Gestion du pty et du sous-processus lnav.

Encapsule tout ce qui touche au processus externe lnav : ouverture d'un
pty, lancement, redimensionnement, arrêt propre, et le petit répondeur de
capacités terminal sans lequel lnav (notcurses) reste bloqué indéfiniment
au démarrage. Toute cette logique a été validée empiriquement pendant un
spike (voir docs/lnav_spike/poc_pty_lnav.py et referentiel_violations_actions.md
§87 pour le détail des blocages trouvés et corrigés).

Conforme à la charte d'architecture Omega-Fire :
- Seul point du sous-système lnav qui appelle subprocess/pty/fcntl/termios
- Ne modifie jamais lnav lui-même : lancé tel quel avec -I pointant sur
  nos définitions de format (formats/omega_fire/*.json, à côté de ce
  fichier)
- Aucune couleur ni logique de rendu ici (voir
  interfaces/cli/renderers/lnav_live.py)
"""
from __future__ import annotations

import fcntl
import os
import pty
import re
import signal
import struct
import subprocess
import termios
import time
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parent
LNAV_BINARY = "lnav"

_OSC52_RE = re.compile(rb"\x1b\]52;[^\x07\x1b]*(?:\x07|\x1b\\)")


def spawn_lnav(rows: int, cols: int, log_paths: list[Path]) -> tuple[int, int]:
    """Ouvre un pty et y lance lnav sur les fichiers donnés (fusionnés
    automatiquement par lnav si plusieurs). Retourne (master_fd, pid)."""
    if not log_paths:
        raise ValueError("au moins un fichier de log est requis")

    master_fd, slave_fd = pty.openpty()

    winsize = struct.pack("HHHH", rows, cols, 0, 0)
    fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, winsize)

    cmd = [LNAV_BINARY, "-I", str(CONFIG_DIR), *[str(p) for p in log_paths]]
    proc = subprocess.Popen(
        cmd,
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        preexec_fn=os.setsid,
        close_fds=True,
    )
    os.close(slave_fd)
    return master_fd, proc.pid


def resize_pty(master_fd: int, pid: int, rows: int, cols: int) -> None:
    winsize = struct.pack("HHHH", rows, cols, 0, 0)
    fcntl.ioctl(master_fd, termios.TIOCSWINSZ, winsize)
    try:
        os.killpg(os.getpgid(pid), signal.SIGWINCH)
    except ProcessLookupError:
        pass


def wait_dead(pid: int, timeout: float) -> bool:
    """Attend au plus `timeout` secondes que le process se termine (non
    bloquant, jamais indéfiniment). Retourne True s'il est mort."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            done_pid, _ = os.waitpid(pid, os.WNOHANG)
        except ChildProcessError:
            return True
        if done_pid == pid:
            return True
        time.sleep(0.1)
    return False


def kill_lnav(pid: int) -> None:
    """Arrêt propre avec filet de sécurité : SIGTERM, on attend un peu,
    SIGKILL si toujours vivant -- jamais de blocage indéfini."""
    try:
        os.killpg(os.getpgid(pid), signal.SIGTERM)
    except ProcessLookupError:
        return
    if wait_dead(pid, 3.0):
        return
    try:
        os.killpg(os.getpgid(pid), signal.SIGKILL)
    except ProcessLookupError:
        return
    wait_dead(pid, 2.0)


def relay_osc52(data: bytes, out_fd: int) -> int:
    """Relaie vers le vrai terminal toute séquence OSC 52 (presse-papier)
    présente dans `data`.

    lnav a son propre mécanisme natif de marquage/copie ('m' puis 'c' --
    "Copy the marked text to the X11 selection buffer or OS X clipboard",
    confirmé via son aide interne `lnav -H`). Il écrit sa réponse OSC 52
    dans le flux qu'il pense être le terminal (notre pty) ; comme le
    reste du flux de lnav n'est jamais renvoyé tel quel vers le vrai
    terminal (seulement notre reconstruction ANSI), cette séquence
    précise doit être relayée explicitement, sinon la copie de lnav
    n'atteint jamais le presse-papier réel. Retourne le nombre de
    séquences relayées."""
    matches = _OSC52_RE.findall(data)
    for seq in matches:
        os.write(out_fd, seq)
    return len(matches)


class TerminalResponder:
    """Répond au minimum vital aux sondes de capacités terminal que lnav
    envoie au démarrage (notcurses). Sans ça, lnav reste bloqué
    indéfiniment à attendre des réponses qu'un pty muet ne renverra
    jamais -- constaté empiriquement pendant le spike : DSR (position du
    curseur) et DA1 (device attributes) suffisent à débloquer le rendu ;
    les ~256 requêtes de couleurs (OSC 4) et les sondes graphiques Kitty
    restent sans réponse et lnav s'en passe sans problème.

    Répond à CHAQUE occurrence, pas seulement la première : lnav peut
    re-sonder (ex. après un redimensionnement) et une réponse à usage
    unique le laisserait bloqué indéfiniment en cours de session --
    aussi constaté empiriquement."""

    def __init__(self, master_fd: int, rows: int, cols: int) -> None:
        self._fd = master_fd
        self._rows = rows
        self._cols = cols
        self._buffer = b""

    def update_size(self, rows: int, cols: int) -> None:
        self._rows, self._cols = rows, cols

    def feed(self, data: bytes) -> None:
        self._buffer += data
        while b"\x1b[6n" in self._buffer:
            os.write(self._fd, f"\x1b[{self._rows};1R".encode())
            self._buffer = self._buffer.replace(b"\x1b[6n", b"", 1)
        while b"\x1b[c" in self._buffer:
            os.write(self._fd, b"\x1b[?1;2c")
            self._buffer = self._buffer.replace(b"\x1b[c", b"", 1)
        if len(self._buffer) > 8192:
            self._buffer = self._buffer[-256:]
