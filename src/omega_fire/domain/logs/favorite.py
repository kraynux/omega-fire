# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Favori (menu 5.2) : un ou plusieurs logs de la Bibliotheque + un lecteur, enregistres
sous un nom et lances directement (repris d'omega-serv / omega-log)."""
from __future__ import annotations

from dataclasses import dataclass

from omega_fire.domain.logs.viewer_type import ViewerType


@dataclass(frozen=True, slots=True)
class Favorite:
    name: str
    paths: tuple[str, ...]
    viewer: ViewerType
