# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Rendre le vrai terminal a un programme interactif (lnav) le temps de l'appel, repris tel
quel d'omega-serv / omega-log (`_maybe_suspend`, `_ensure_terminal_truly_released`).

Deux protections par-dessus `App.suspend()` (jamais un correctif dans Textual) :
- une exception levee pendant l'appel est attrapee DANS le bloc suspendu puis relancee
  apres la reprise : sinon l'interface ne reprenait pas, l'utilisateur restait devant le
  terminal de lancement (retour utilisateur 2026-10-28, lnav 8.6 / 5.2 / 5.3) ;
- le thread clavier de Textual est reellement arrete avant l'appel (bug reel rencontre
  dans omega-serv : il lisait le meme terminal en meme temps que le programme lance)."""
from __future__ import annotations

import termios
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from textual.app import SuspendNotSupported

_INPUT_THREAD_JOIN_TIMEOUT_SECONDS = 1.0


def ensure_terminal_truly_released(app: Any) -> None:
    """Best-effort, `getattr` partout : silencieux sur tout driver sans ces attributs."""
    driver = getattr(app, "_driver", None)
    if driver is None:
        return
    key_thread = getattr(driver, "_key_thread", None)
    if key_thread is not None and key_thread.is_alive():
        exit_event = getattr(driver, "exit_event", None)
        if exit_event is not None:
            exit_event.set()
        key_thread.join(timeout=_INPUT_THREAD_JOIN_TIMEOUT_SECONDS)
        if exit_event is not None:
            exit_event.clear()
    writer_thread = getattr(driver, "_writer_thread", None)
    if writer_thread is not None and writer_thread.is_alive():
        stop = getattr(writer_thread, "stop", None)
        if callable(stop):
            stop()
        else:
            writer_thread.join(timeout=_INPUT_THREAD_JOIN_TIMEOUT_SECONDS)
    fileno = getattr(driver, "fileno", None)
    if isinstance(fileno, int):
        try:
            termios.tcflush(fileno, termios.TCIFLUSH)
        except OSError:
            pass


@contextmanager
def suspended_terminal(app: Any) -> Iterator[None]:
    caught: BaseException | None = None
    try:
        with app.suspend():
            ensure_terminal_truly_released(app)
            try:
                yield
            except BaseException as exc:  # noqa: BLE001 - relancee plus bas, jamais avalee
                caught = exc
    except SuspendNotSupported:
        yield
        return
    if caught is not None:
        raise caught
