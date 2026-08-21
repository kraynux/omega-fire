# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Bootstrap module for Omega-Fire application.

Assembles and starts the application. Handles:
- Terminal size validation
- Theme initialization
- Splash screen display
- Capability registry initialization (system scan)
- Main menu launch

Conforms to Omega-Fire architecture charter:
- No business logic (only wiring and startup)
- Depends on interfaces/ for rendering and user interaction
- Depends on core/ for capability registry
- Depends on infrastructure/ for system probing
"""
import sys
from typing import Optional

from rich.console import Console

from omega_fire.interfaces.cli.renderers.styles import (
    MIN_TERMINAL_WIDTH,
    MIN_TERMINAL_HEIGHT,
)
from omega_fire.interfaces.cli.themes.registry import theme_registry


def check_terminal_size() -> bool:
    """Vérifie que le terminal respecte la taille minimale requise.

    Returns:
        True si la taille est suffisante, False sinon.
    """
    import shutil

    size = shutil.get_terminal_size()

    if size.columns < MIN_TERMINAL_WIDTH or size.lines < MIN_TERMINAL_HEIGHT:
        print(f"\n❌ Terminal trop petit : {size.columns}x{size.lines}")
        print(f"   Taille minimale requise : {MIN_TERMINAL_WIDTH}x{MIN_TERMINAL_HEIGHT}")
        print(f"   Veuillez redimensionner votre fenêtre et relancer.\n")
        return False

    return True

def bootstrap(console: Optional[Console] = None) -> int:
    """Orchestrate application startup sequence.

    Startup order:
    1. Check terminal size (reject if too small)
    2. Initialize theme
    3. Display splash screen (welcome + branding)
    4. Initialize container & capability registry (scan system)
    4.5 Initialize loggers (AppLogger & AuditLogger)
    5. Launch main menu (interactive loop)

    Args:
        console: Optional Rich console (uses default if None).

    Returns:
        Exit code (0 = success, 1 = error).
    """
    console = console or Console()

    # 1. Check terminal size
    if not check_terminal_size():
        return 1

    # 2. Initialize theme
    try:
        theme_registry.set_active("omega-base")
    except Exception:
        try:
            theme_registry.set_active("omega-mono")
        except Exception:
            pass

    # 3. Display splash screen
    from omega_fire.interfaces.cli.actions import _error, _warning
    from rich.text import Text

    try:
        from omega_fire.interfaces.cli.renderers.splash import render_splash
        proceed = render_splash(console=console, wait_for_key=True)
        if not proceed:
            from rich.panel import Panel
            from rich.align import Align
            from rich import box as rich_box
            import shutil

            dialog_width = min(shutil.get_terminal_size().columns - 10, 60)
            closing_panel = Panel(
                Align.center(Text("Fermeture d'Omega-Fire.", style=theme_registry.get_style("text.muted"))),
                border_style=theme_registry.get_style("border.accent"),
                box=rich_box.ROUNDED,
                padding=(1, 3),
                width=dialog_width,
            )
            console.print()
            console.print(Align.center(closing_panel))
            console.print()
            return 0
    except Exception as e:
        console.print(_error(f"Erreur splash : {e}"))

    import shutil
    from rich.text import Text
    from rich.spinner import Spinner
    from rich.live import Live
    from rich.panel import Panel
    from rich.align import Align
    from rich.console import Group
    from rich import box as rich_box

    dialog_width = min(shutil.get_terminal_size().columns - 10, 70)

    def _build_scan_panel(spinner: Spinner) -> Panel:
        body = Group(
            Align.center(Text("Initialisation d'Omega-Fire", style=theme_registry.get_style("text.heading"))),
            Text(""),
            Align.center(spinner),
            Text(""),
            Align.center(Text("Analyse des services installés", style=theme_registry.get_style("text.muted"))),
            Align.center(Text("(nftables, iptables, fail2ban, systemd...)", style=theme_registry.get_style("text.muted"))),
        )
        return Panel(
            body,
            border_style=theme_registry.get_style("border.accent"),
            box=rich_box.ROUNDED,
            padding=(1, 3),
            width=dialog_width,
        )

    from omega_fire.app.dependency_container import DependencyContainer

    console.print()
    spinner = Spinner("dots", style=theme_registry.get_style("border.accent"))
    container = None
    registry = None

    try:
        with Live(Align.center(_build_scan_panel(spinner)), console=console,
                   refresh_per_second=10, transient=True):
            container = DependencyContainer()
            registry = container.capability_registry
            scanner = container.scanner
            if hasattr(scanner, "scan_all"):
                scan_results = scanner.scan_all()
                registry.update_from_scan(scan_results)
            elif hasattr(scanner, "scan"):
                scanner.scan()
    except Exception as e:
        console.print(_warning(f"Scan système partiel : {e}"))
        if registry is None:
            from omega_fire.core.capability_registry import CapabilityRegistry
            registry = CapabilityRegistry()

    # 4.5. Initialize Loggers (AppLogger & AuditLogger)
    try:
        from omega_fire.infrastructure.logging.app_logger import AppLogger
        from omega_fire.infrastructure.logging.audit_logger import AuditLogger

        app_logger = AppLogger()
        audit_logger = AuditLogger()
        
        # Attache au conteneur si disponible
        if container is not None:
            container._cache["app_logger"] = app_logger
            container._cache["audit_logger"] = audit_logger

        # Logs automatiques de démarrage
        app_logger.info("Initialisation du système et des composants système réassignés.")
        audit_logger.log_event(
            event_type="system_startup",
            actor="system",
            action="bootstrap_init",
            result="success",
            details={"message": "Démarrage d'Omega-Fire et initialisation des composants."}
        )
    except Exception as e:
        pass

    # 5. Launch main menu
    from omega_fire.interfaces.cli.app import run_app
    return run_app(registry=registry, console=console, container=container)



def main() -> int:
    """Entry point for the application.

    Returns:
        Exit code (0 = success, 1 = error, 130 = SIGINT).
    """
    try:
        return bootstrap()
    except KeyboardInterrupt:
        # Sortie propre si interruption brutale avant le lancement de l'interface
        print("\n\n[+] Interruption système. Fermeture d'Omega-Fire.\n")
        return 130


if __name__ == "__main__":
    sys.exit(main())


# <-- INFO DEV ---------------------------------------------------------
# Role :
# - Point d'entree principal de l'application Omega-Fire
# - Orchestre la sequence de demarrage :
#     1. Verification taille terminal
#     2. Initialisation du theme
#     3. Affichage splash screen (modele SPLASH)
#     4. Scan systeme (peuple le registre de capacites)
#     4.5 Initialisation des loggers (app.log & audit.log)
#     5. Lancement du menu interactif (interfaces/cli/app.py)
#
# Pourquoi dans app/ (charte) :
# - Contient uniquement du cablage et du demarrage
# - Pas de logique metier
# - Depend de interfaces/ pour le rendu
# - Depend de core/ pour le registre
# - Depend de infrastructure/ pour les probes et les loggers
#
# Ce qu'il ne contient PAS :
# - Pas de logique metier
# - Pas de rendu direct
# - Pas de navigation (c'est interfaces/cli/app.py)
# - Pas de construction de menu (c'est menu_builder)
#
# Points cles :
# - check_terminal_size() : rejette si < 80x24
# - bootstrap() : orchestre les etapes de demarrage
# - main() : point d'entree avec gestion exceptions
# - Le registry peuple est passe a run_app()
# - Si le scan echoue, on continue avec un registre partiel
# - Scan systeme (etape 4) : message d'accompagnement a 3 lignes (sans
#   estimation de delai, non fiable d'une machine a l'autre) + spinner
#   Rich pendant le scan reel — reutilise _error()/_warning()
#   (interfaces/cli/actions.py) plutot que des couleurs Rich en dur.
#---------------------------------------------------------------------->
