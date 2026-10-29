# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Bibliotheque de logs (menu 5.1, version 3.5) : les logs importes, qui alimentent les
Favoris (5.2) et Voir les logs (5.3). Reprise d'omega-serv (refonte du 2026-10-15) et
d'omega-log, eux-memes nes des epingles d'omega-fire.

Trois origines (`access`) :
- `file`       : chemin epingle a la main ;
- `omega-serv` : journal d'une instance omega-serv detectee (import automatique) ;
- `ssh`        : copie locale d'un log distant recupere par scp.

Pures donnees, aucune I/O : l'etat reel (existe, taille, date) est recalcule a chaque
affichage par application/commands/manage_log_library.py, jamais fige a l'ajout."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

ACCESS_FILE = "file"
ACCESS_OMEGA_SERV = "omega-serv"
ACCESS_SSH = "ssh"


@dataclass(frozen=True, slots=True)
class LibraryRecord:
    """Entree persistee : identite seule. `source` = instance omega-serv ou label de la
    source distante (None pour un chemin epingle a la main)."""
    path: str
    access: str = ACCESS_FILE
    source: str | None = None


@dataclass(frozen=True, slots=True)
class LogFile:
    """Entree de la Bibliotheque avec son etat au moment de l'affichage."""
    path: str
    access: str = ACCESS_FILE
    source: str | None = None
    exists: bool = False
    size_bytes: int | None = None
    modified_at: datetime | None = None

    @property
    def is_stale(self) -> bool:
        """Present mais vide : service arrete, log herite..."""
        return self.exists and self.size_bytes == 0
