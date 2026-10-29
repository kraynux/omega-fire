# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Les trois lecteurs de logs (5.2 Favoris, 5.3 Voir les logs) : SIMPLE (tableau de bord
temps reel avec etat : le Live Tail de 8.5), CLASSIC (lecture + suivi), LNAV (fusion de
plusieurs logs : 8.6). Garde-fou : 1 log -> les 3 ; 2 logs ou plus -> lnav seul, le seul
capable de fusionner (refus explicite, jamais une troncature)."""
from __future__ import annotations

from enum import Enum


class ViewerType(Enum):
    SIMPLE = "simple"
    CLASSIC = "classic"
    LNAV = "lnav"


def allowed_viewers(log_count: int) -> tuple[ViewerType, ...]:
    if log_count <= 1:
        return (ViewerType.SIMPLE, ViewerType.CLASSIC, ViewerType.LNAV)
    return (ViewerType.LNAV,)
