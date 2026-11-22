# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Contrat du pare-feu de la machine géré hors d'omega-fire (ufw, firewalld) : un paquet doit être accepté par
lui ET par les règles d'omega-fire. Utilisé par `omega-fire.sh port ouvrir` (demande omega-serv du 2026-11-17)."""

from __future__ import annotations

from typing import Protocol

ADDED = "ajoutee"
ALREADY = "deja"
FAILED = "echec"
REMOVED = "retiree"
ABSENT = "absente"


class HostFirewallPort(Protocol):
    def active_name(self) -> str:
        """« ufw » ou « firewalld » s'il est actif ; « » sinon."""
        ...

    def allow(self, port: int, source: str, comment: str) -> tuple[str, str]:
        """Autorise `port`/tcp depuis `source` (CIDR). Rend (ADDED | ALREADY | FAILED, détail)."""
        ...

    def remove(self, port: int, source: str) -> tuple[str, str]:
        """Retire l'autorisation posée par `allow` (`port fermer`, 2026-11-21). Rend (REMOVED | ABSENT | FAILED,
        détail)."""
        ...
