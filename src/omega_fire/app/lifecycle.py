# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Application lifecycle management."""
import signal
import sys
from typing import Optional
from rich.console import Console

class ApplicationLifecycle:
    """Manages the application lifecycle."""
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self._running = False
        self._registry = None  # CapabilityRegistry sera initialisé plus tard

    def start(self) -> None:
        """Start the application and set up signal handlers."""
        self._running = True
        signal.signal(signal.SIGINT, self._handle_sigint)
        signal.signal(signal.SIGTERM, self._handle_sigterm)
        self.console.print("[green]Application started.[/green]")

    def _handle_sigint(self, signum, frame):
        """Handle Ctrl+C."""
        self.console.print("\n[yellow]Interrupted by user (Ctrl+C)[/yellow]")
        self._running = False

    def _handle_sigterm(self, signum, frame):
        """Handle termination signal."""
        self.console.print("\n[yellow]Termination signal received[/yellow]")
        self._running = False

    def is_running(self) -> bool:
        """Check if the application is running."""
        return self._running

    def get_registry(self):
        """Get the capability registry (None before initialization)."""
        return self._registry

    def request_shutdown(self) -> None:
        """Request graceful shutdown."""
        self._running = False

    def stop(self) -> None:
        """Stop the application."""
        self._running = False
        self.console.print("[yellow]Application stopped.[/yellow]")

def create_lifecycle(console: Optional[Console] = None) -> ApplicationLifecycle:
    """Factory function to create an ApplicationLifecycle."""
    return ApplicationLifecycle(console)
