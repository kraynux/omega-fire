# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Demande de redemarrage de l'interface apres un changement de langue
(OMEGA-FIRE_PLAN-DETAILLE_I18N.md §5). Module feuille (evite un cycle d'import
app.py <-> settings_screen.py).

Deposee sur `OmegaFireApp.pending_restart` par l'ecran Reglages, lue par
app/bootstrap.py::bootstrap_tui() APRES `App.run()` : os.execv() relance le MEME Python sur la
MEME installation, nouveau processus = nouvelle langue chargee depuis le disque. Les regles
du pare-feu, fail2ban et les services ne sont jamais touches."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PendingInterfaceRestart:
    language_code: str
