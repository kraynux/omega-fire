# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Contrat de la machine pour le bouclier du port WireGuard (3.7.0, omega-lib D-018) : la table, ses fichiers et
son service sont ecrits par omega_lib.shield ; ce port lit la machine et lance les commandes (omega-fire est root)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from omega_lib.shield.models import ShieldSettings, ShieldStatus


@dataclass(frozen=True)
class CommandLine:
    command: tuple[str, ...]
    code: int
    detail: str


class WgShieldPort(Protocol):
    def init_name(self) -> str:
        """« systemd », « openrc », « runit » ou « none »."""
        ...

    def runit_dir(self) -> str: ...

    def kernel_release(self) -> str: ...

    def modules_ready(self) -> bool:
        """Faux : noyau mis a jour sans redemarrage, `nft_limit` ne peut plus etre charge."""
        ...

    def tailscaled_port(self) -> int: ...

    def devices(self) -> tuple[str, ...]:
        """Cartes reseau materielles."""
        ...

    def settings(self) -> ShieldSettings | None: ...

    def status(self, *, refresh: bool = True) -> ShieldStatus | None:
        """`refresh` : l'etat est recalcule tout de suite (script root `etat`) au lieu d'attendre la minute."""
        ...

    def stage(self, files: dict[str, str]) -> str:
        """Ecrit les fichiers prepares (dossier d'omega-fire) ; rend le dossier."""
        ...

    def run(self, commands: Sequence[tuple[str, ...]], *, keep_going: bool = False) -> list[CommandLine]:
        """Lance les commandes dans l'ordre ; s'arrete a la premiere en echec sauf `keep_going` (retrait)."""
        ...

    def now(self) -> float: ...
