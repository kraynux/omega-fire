# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Centralized keybindings for Omega-Fire CLI.

Defines the standard keyboard shortcuts used across the entire application.
All renderers (splash, menu, dash) MUST use these constants to ensure
consistency in the footer display and key capture.

Standard shortcuts:
- ↑↓ : Navigate
- Enter : Validate / Enter submenu
- Esc : Back / Cancel
- a : Help (replaces F1 - avoids system shortcuts)
- t : Theme (replaces F2 - avoids system shortcuts)
- q : Quit (replaces F10 - avoids system shortcuts)

Also hosts the single low-level terminal read primitive (_getch and its
tty/termios/fcntl helpers), extracted from app.py so it can be shared
with other renderers (e.g. the pager) without duplicating this logic.
"""

import os
import sys
import tty
import termios
import fcntl

# ----------------------------------------------------------------------
# Display labels (for footer rendering)
# ----------------------------------------------------------------------
KEY_UP_DOWN = "↑↓"
KEY_ENTER = "Enter"
KEY_ESC = "Esc"
KEY_A = "a"
KEY_T = "t"
KEY_Q = "q"
KEY_R = "r"
KEY_D = "d"
KEY_F = "f"

LABEL_NAVIGATE = "Naviguer"
LABEL_VALIDATE = "Valider"
LABEL_ENTER = "Entrer"
LABEL_BACK = "Retour"
LABEL_HELP = "Aide"
LABEL_THEME = "Thème"
LABEL_MENU = "Menu"
LABEL_QUIT = "Quitter"
LABEL_REFRESH = "Rafraîchir"
LABEL_PAGE_START = "Début"
LABEL_PAGE_END = "Fin"

# ----------------------------------------------------------------------
# Raw escape sequences (for key capture)
# ----------------------------------------------------------------------
# Arrow keys
SEQ_ARROW_UP = "\x1b[A"
SEQ_ARROW_DOWN = "\x1b[B"
SEQ_ARROW_RIGHT = "\x1b[C"
SEQ_ARROW_LEFT = "\x1b[D"

# Enter / Return
SEQ_ENTER_CR = "\r"
SEQ_ENTER_LF = "\n"

# Escape
SEQ_ESC = "\x1b"

# Ctrl+C
SEQ_CTRL_C = "\x03"


# ----------------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------------
def is_arrow_up(key: str) -> bool:
    return key == SEQ_ARROW_UP


def is_arrow_down(key: str) -> bool:
    return key == SEQ_ARROW_DOWN


def is_arrow_left(key: str) -> bool:
    return key == SEQ_ARROW_LEFT


def is_arrow_right(key: str) -> bool:
    return key == SEQ_ARROW_RIGHT


def is_enter(key: str) -> bool:
    return key in (SEQ_ENTER_CR, SEQ_ENTER_LF)


def is_escape(key: str) -> bool:
    return key == SEQ_ESC


def is_help(key: str) -> bool:
    """Check if the key is 'a' for help."""
    return key == KEY_A


def is_theme(key: str) -> bool:
    """Check if the key is 't' for theme."""
    return key == KEY_T


def is_quit(key: str) -> bool:
    """Check if the key is quit (q or Ctrl+C)."""
    return key == KEY_Q or key == SEQ_CTRL_C


def is_refresh(key: str) -> bool:
    """Check if the key is 'r' for a forced redraw (recentrage après
    redimensionnement du terminal)."""
    return key == KEY_R


def is_page_start(key: str) -> bool:
    """Check if the key is 'd' for Début (jump to first page)."""
    return key == KEY_D


def is_page_end(key: str) -> bool:
    """Check if the key is 'f' for Fin (jump to last page)."""
    return key == KEY_F


# ----------------------------------------------------------------------
# Low-level terminal input (extracted from app.py)
# ----------------------------------------------------------------------
def _set_nonblocking(fd: int) -> None:
    flags = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)


def _set_blocking(fd: int) -> None:
    flags = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, flags & ~os.O_NONBLOCK)


def _flush_stdin() -> None:
    try:
        termios.tcflush(sys.stdin.fileno(), termios.TCIFLUSH)
    except Exception:
        pass


def _getch() -> str:
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        _flush_stdin()
        tty.setcbreak(fd)
        first = sys.stdin.read(1)
        if first != '\x1b':
            _flush_stdin()
            return first
        _set_nonblocking(fd)
        try:
            seq = ''
            for _ in range(5):
                try:
                    ch = sys.stdin.read(1)
                    if ch:
                        seq += ch
                    else:
                        break
                except (IOError, OSError):
                    break
        finally:
            _set_blocking(fd)
            _flush_stdin()
        return '\x1b' + seq
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


# <-- INFO DEV ---------------------------------------------------------
# Role :
# - Module centralise pour les raccourcis clavier de toute l'application
# - Definit les constantes d'affichage (footer) et de capture (sequences)
# - Tous les renderers (splash, menu, dash) DOIVENT utiliser ces constantes
# - Garantit la coherence visuelle et fonctionnelle entre les ecrans
#
# Pourquoi dans interfaces/cli/ (charte) :
# - C'est de la logique d'interface utilisateur (raccourcis clavier)
# - Pas de logique metier
# - Pas de dependance vers domain/, application/, infrastructure/
# - Utilise uniquement par les renderers et la boucle de navigation
#
# Ce qu'il ne contient PAS :
# ❌ Pas de logique metier
# ❌ Pas de dependance vers d'autres couches
# ❌ Pas de rendu Rich
#
# Points cles :
# - Raccourcis lettres simples (a, t, q, d, f) au lieu de F1-F10
#   Evite les conflits avec les raccourcis systeme (KDE/GNOME)
# - Constantes d'affichage : KEY_UP_DOWN, KEY_ENTER, KEY_ESC, KEY_A, KEY_T, KEY_Q, KEY_D, KEY_F
# - Labels : LABEL_NAVIGATE, LABEL_VALIDATE, LABEL_BACK, etc.
# - Sequences brutes : SEQ_ARROW_UP, SEQ_ESC, SEQ_CTRL_C
# - Fonctions helpers : is_arrow_up(), is_enter(), is_help(), is_theme(), is_quit(), is_page_start(), is_page_end()
# - _getch() : seul appel systeme du module (tty/termios/fcntl), extrait
#   de app.py pour etre partage avec les autres renderers (ex. pager.py)
#   sans dupliquer la lecture clavier bas niveau
#
# Standards de raccourcis (a respecter partout) :
# - ↑↓ : Naviguer (dans les listes/menus)
# - Enter : Valider / Entrer dans un sous-menu
# - Esc : Retour / Annuler
# - a : Aide (remplace F1 - evite conflits systeme)
# - t : Changer de theme (remplace F2 - evite conflits systeme)
# - q : Quitter (remplace F10 - evite conflits systeme)
# - Ctrl+C : Quitter immediatement
#
# Integration :
# - interfaces/cli/renderers/splash.py : utilise les constantes pour le footer
# - interfaces/cli/app.py : utilise les helpers pour la capture clavier
# - interfaces/cli/renderers/dashboard.py : utilisera les constantes
#---------------------------------------------------------------------->
