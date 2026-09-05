# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Re-export depuis omega_lib (D-008) : garde la convention 'importer
depuis omega_fire.ports.X' uniforme dans tout le reste du code, meme
principe que les autres outils de la suite (CHECK/DEEP/FOLD)."""
from __future__ import annotations

from omega_lib.ports.settings_store import SettingsStore

__all__ = ["SettingsStore"]
