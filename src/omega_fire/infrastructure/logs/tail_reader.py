# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Lecture d'un log pour le lecteur Classique (5.2 / 5.3, version 3.5) : dernieres lignes lues
depuis la FIN du fichier (jamais le fichier entier : un journal reel peut faire 100 Mo et
plus), puis suivi incremental des lignes ajoutees, rotation et troncature comprises."""
from __future__ import annotations

import os
from pathlib import Path

_CHUNK = 65536


def read_last_lines(path: Path, count: int) -> list[str]:
    with open(path, "rb") as handle:
        handle.seek(0, os.SEEK_END)
        position = handle.tell()
        data = b""
        while position > 0 and data.count(b"\n") <= count:
            step = min(_CHUNK, position)
            position -= step
            handle.seek(position)
            data = handle.read(step) + data
    lines = data.decode("utf-8", errors="replace").splitlines()
    return lines[-count:]


class FileTailReader:
    """Lignes ajoutees depuis la derniere lecture. Fichier remplace (rotation) ou raccourci
    (troncature) : reprise au debut du nouveau contenu."""

    def __init__(self, path: Path) -> None:
        self._path = path
        stat = path.stat()
        self._inode = stat.st_ino
        self._offset = stat.st_size
        self._partial = b""

    def read_new_lines(self) -> list[str]:
        stat = self._path.stat()
        if stat.st_ino != self._inode or stat.st_size < self._offset:
            self._inode, self._offset, self._partial = stat.st_ino, 0, b""
        if stat.st_size == self._offset:
            return []
        with open(self._path, "rb") as handle:
            handle.seek(self._offset)
            data = self._partial + handle.read(stat.st_size - self._offset)
        self._offset = stat.st_size
        *complete, self._partial = data.split(b"\n")
        return [line.decode("utf-8", errors="replace") for line in complete]
