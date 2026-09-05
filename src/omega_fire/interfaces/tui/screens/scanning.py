# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran de scan systeme au demarrage : peuple le registre de capacites
avant d'afficher l'accueil, exactement comme bootstrap()::4. Initialize
container & capability registry (scan system) cote CLI — absent du
demarrage Textual jusqu'ici (retour utilisateur reel : plus aucun scan
automatique au lancement). Execute en arriere-plan (thread, jamais sur
le thread UI) pendant que l'indicateur de chargement tourne."""
from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Center, Middle
from textual.screen import Screen
from textual.widgets import LoadingIndicator, Static

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer


class ScanningScreen(Screen[None]):
    """Premier ecran apres le splash : scanne le systeme (backends,
    services, Fail2ban) pour peupler capability_registry avant d'ouvrir
    l'accueil. N'herite pas de OmegaScreen (comme splash.py/
    terminal_warning.py) : ecran de demarrage, pas de navigation `echap`."""

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container

    def compose(self) -> ComposeResult:
        with Middle(), Center():
            yield LoadingIndicator()
        with Middle(), Center():
            yield Static("Analyse du systeme en cours...", classes="omega-splash-prompt")

    def on_mount(self) -> None:
        def _work() -> None:
            try:
                registry = self._container.capability_registry
                scanner = self._container.scanner
                if hasattr(scanner, "scan_all"):
                    scan_results = scanner.scan_all()
                    registry.update_from_scan(scan_results)
                elif hasattr(scanner, "scan"):
                    scanner.scan()
            except Exception:
                pass
            self.app.call_from_thread(self.dismiss)

        self.run_worker(_work, thread=True)
