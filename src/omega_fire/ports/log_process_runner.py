# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
# Porte d'omega-log (ports/process_runner_port.py) le 2026-11-09 (OMEGA-FIRE_PLAN_LOGS_NIVEAU_SERV_LOG.md) : garder identique a la source.
"""Contrat d'execution de processus externe — porte verbatim depuis
omega-serv (ports/process_runner_port.py) : pur contrat, aucune
dependance omega_serv. Sert ici a l'elevation ponctuelle (sudo) pour
l'acces aux logs proteges de /var/log (plan_omega_log.md §5.1, revise
2026-10-03 : sudo ponctuel au moment de l'action plutot que la
delegation par groupe seule, qui ne couvre pas tous les cas reels —
ex. /var/log/audit, root:root 700)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ProcessResult:
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


class ProcessRunnerPort(Protocol):
    def run(self, args: list[str], input_text: str | None = None, timeout: float | None = None) -> ProcessResult:
        ...

    def run_interactive(self, args: list[str]) -> int:
        """Execute en HERITANT INTEGRALEMENT les descripteurs du
        terminal reel (jamais de capture stdout/stderr/stdin) - reserve
        aux commandes qui ont reellement besoin d'un terminal
        interactif complet, typiquement `sudo -v` pour authentifier/
        rafraichir le cache sudo AVANT une commande privilegiee
        capturee separement (meme raisonnement que omega-serv : une
        commande privilegiee lancee directement avec une sortie
        capturee empeche l'invite de mot de passe sudo de s'afficher
        et de fonctionner correctement sur le vrai terminal). Ne
        retourne QUE le code de retour, aucune sortie a capturer par
        construction."""
        ...
