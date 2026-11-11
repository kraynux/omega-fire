# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Retrait des lignes d'un log qui contiennent certaines IP, SUR PLACE (correctif 2026-11-10).

Avant : `open(path, "w")` (troncature immediate) puis reecriture d'une copie lue avant la confirmation.
Sur un log vivant (journal d'omega-serv, d'omega-waf) ecrit pendant ce temps, les lignes arrivees entre
la lecture et l'ecriture etaient perdues, et les octets non UTF-8 supprimes (lecture errors="ignore").

Maintenant :
- meme fichier (meme inode) : proprietaire, groupe et droits inchanges, meme lance en root, et les
  ecrivains qui gardent le fichier ouvert (O_APPEND) continuent d'ecrire au bon endroit ;
- lecture binaire, octets non UTF-8 conserves (surrogateescape) ;
- le contenu est relu juste avant la reecriture, y compris ce qui a ete ajoute pendant le filtrage :
  la fenetre ou une ligne peut se perdre est reduite a l'instant de la reecriture elle-meme."""
from __future__ import annotations

import os
from pathlib import Path

from omega_fire.domain.logs.ip_lines import split_lines_by_ips

_ENCODING = "utf-8"
_ERRORS = "surrogateescape"


def _decode_lines(data: bytes) -> list[str]:
    return data.decode(_ENCODING, _ERRORS).splitlines(keepends=True)


def remove_ips_in_place(path: Path, ips: list[str]) -> dict[str, int]:
    """Retire du fichier les lignes qui contiennent l'une des IP. Rend le nombre de lignes retirees par
    IP. Leve OSError si le fichier ne peut pas etre lu ou ecrit (rien n'est alors modifie)."""
    with open(path, "r+b") as handle:
        data = handle.read()
        tail = handle.read()  # ajoute pendant la lecture
        while tail:
            data += tail
            tail = handle.read()
        counts, kept = split_lines_by_ips(_decode_lines(data), ips)
        if not any(counts.values()):
            return counts
        extra = handle.read()  # ajoute pendant le filtrage : filtre aussi, jamais perdu
        while extra:
            more_counts, more_kept = split_lines_by_ips(_decode_lines(extra), ips)
            for ip, count in more_counts.items():
                counts[ip] += count
            kept += more_kept
            extra = handle.read()
        handle.seek(0)
        handle.write("".join(kept).encode(_ENCODING, _ERRORS))
        handle.truncate()
        handle.flush()
        os.fsync(handle.fileno())
    return counts
