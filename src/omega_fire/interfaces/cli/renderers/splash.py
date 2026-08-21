# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Splash screen renderer for Omega-Fire CLI.

Provides the welcome screen displayed at application startup.
Uses the SPLASH model: Live(screen=True) + Layout + threading for
clean redraw on terminal resize.
Captures keyboard shortcuts (a, t, q) like the main menu.

CRITICAL: Uses theme_registry.get_style() for splash text (text.heading,
text.main, text.muted) instead of hardcoded splash_*_style properties.
This ensures the splash text colors actually change when the theme changes.

Conforms to Omega-Fire architecture charter:
- Pure rendering logic, no business rules
- Uses theme_registry for all styling (no hardcoded colors)
- Uses styles.py helpers for dynamic width calculations
- Uses keybindings.py for standardized shortcuts
- No dependency on domain/, application/, or infrastructure/
"""
import sys
import os
import tty
import termios
import fcntl
import threading
from typing import Optional

from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from rich.live import Live
from rich.layout import Layout
from rich.table import Table

from omega_fire.interfaces.cli.themes.registry import theme_registry
from omega_fire.interfaces.cli.renderers.styles import (
    get_terminal_width,
    get_terminal_height,
)
from omega_fire.interfaces.cli import keybindings as kb


# ----------------------------------------------------------------------
# Logo ASCII valide (bouclier + banniere OMEGA-FIRE, 23 lignes)
# ----------------------------------------------------------------------
# Chaque ligne est stockee "brute" (sans padding de centrage) - le
# centrage est fait a l'affichage via Align.center(), comme le reste
# du fichier. Zones identifiees pour la coloration par theme_registry :
#   0-2  : container "LINUX FIREWALL SUITE" (bordure + texte)
#   3    : barre de version (meme largeur que le corps du bouclier)
#   4-8  : container de la banniere OMEGA-FIRE (bordure + logo 3 lignes + bordure) -
#          meme logo que le menu principal (box-drawing, 73 caracteres de large),
#          colore en 3 nuances : ligne du haut/bas en menu.title (vif),
#          ligne du milieu en menu.item (normal)
#   9-20 : corps et pointe du bouclier (le caractere ▒ marque l'omega incruste)
#   21-22 : tagline finale
OMEGA_FIRE_LOGO_LINES: list[str] = [
    "┌────────────────────────┐",
    "│  LINUX FIREWALL SUITE  │",
    "▄▄▄ └────────────────────────┘ ▄▄▄",
    "█░▒▓████████▓▒░v3.0░▒▓████████▓▒░█",
    "┌───────────────────────────────────────────────────────────────────────────┐",
    "│ ┌╦═══╦┐ ┌╦═╦═╦┐ ┌╦═══╦┐ ┌╦═══╦┐ ┌╦═══╦┐   ┌╦═══╦┐ ┌═╤╦╤═┐ ┌╦═══╦┐ ┌╦═══╦┐ │",
    "│ │║   ║│ │║ ║ ║│ ├╬══    │║  ═╦┐ ├╬═══╬┤ ═ ├╬══      │║│   │╠══╦╩┘ ├╬══    │",
    "│ └╩═══╩┘ └╩   ╩┘ └╩═══╩┘ └╩═══╩┘ └╩   ╩┘   └╩      └═╧╩╧═┘ └╩  ╚═┘ └╩═══╩┘ │",
    "└───────────────────────────────────────────────────────────────────────────┘",
    "█░▒▓██████████████████████████▓▒░█",
    "█░▒▓████████▒▒▒▒▒▒▒▒▒▒████████▓▒░█",
    "█░▒▓███████▒▒████████▒▒███████▓▒░█",
    "█░▒▓███████▒▒████████▒▒███████▓▒░█",
    "█░▒▓███████▒▒████████▒▒███████▓▒░█",
    "▀█░▒▓████████▒▒████▒▒████████▓▒░█▀",
    "▀█░▒▓████▒▒▒▒████▒▒▒▒████▓▒░█▀",
    "▀█░▒▓████████████████▓▒░█▀",
    "▀█░▒▓████████████▓▒░█▀",
    "▀█░▒▓████████▓▒░█▀",
    "▀█░▒▓████▓▒░█▀",
    "▀▀▀▀▀▀▀▀▀▀",

    "FIREWALL | RULES | BAN & IP CONTROL | ORCHESTRATION | LOGS",
    "INTER-OPERABILITE | AUDIT | EXPORT | BACKUP | MONITORING",
]

_LFS_BOX = (0, 2)
_VERSION_BAR = 3
_OMEGA_BOX = (4, 8)
_OMEGA_LOGO_ROWS = (5, 7)  # les 3 lignes du logo lui-meme, a l'interieur du container
_SHIELD = (9, 20)
_TAGLINE_START = 21

def _render_omega_fire_logo() -> Group:
    """Construit le logo complet (bouclier + banniere) avec coloration
    par zone via theme_registry - aucune couleur en dur.

    Regle de coloration : les cadres/containers (LINUX FIREWALL SUITE,
    barre de version, cadre du container OMEGA-FIRE) partagent la meme
    couleur que le corps du bouclier (menu.item), pour une continuite
    visuelle - inchange par rapport a la version precedente.

    Le logo OMEGA-FIRE lui-meme (les 3 lignes a l'interieur du
    container, identique a celui du menu principal) suit sa propre
    regle a 3 nuances : ligne du haut et du bas en menu.title (vif),
    ligne du milieu en menu.item (normal) - pour donner du relief,
    validee sur le menu principal puis reprise ici a l'identique.

    L'omega incruste dans le bouclier (caractere ▒) utilise
    text.heading pour se detacher du corps du bouclier - inchange.

    Renfort visuel (nouveau) : l'angle du bouclier (ligne 14, seul
    endroit ou la forme casse du bloc plein vers le triangle qui se
    resserre) recoit un renfort en menu.title sur ses coins "▀█" et
    "█▀". La pointe finale (ligne 20, "▀██▓██▀") recoit le meme
    traitement uniquement sur son caractere central "▓".
    """
    item_s = theme_registry.get_style("menu.item")
    title_s = theme_registry.get_style("menu.title")
    heading_s = theme_registry.get_style("text.heading")

    # ligne du haut / bas du logo (dans le container) en vif, milieu en normal
    logo_row_styles = {
        _OMEGA_LOGO_ROWS[0]: title_s,
        _OMEGA_LOGO_ROWS[0] + 1: item_s,
        _OMEGA_LOGO_ROWS[1]: title_s,
    }

    # Ligne unique correspondant a l'angle du bouclier (transition
    # rectangle -> triangle, seul endroit ou la forme casse)
    _SHIELD_ANGLE_LINE = 14

    lines = []
    for i, raw in enumerate(OMEGA_FIRE_LOGO_LINES):
        t = Text()
        if _LFS_BOX[0] <= i <= _LFS_BOX[1]:
            for ch in raw:
                t.append(ch, style=item_s if ch in "┌┐└┘─│" else title_s)
        elif i == _VERSION_BAR:
            t.append(raw, style=item_s)
        elif i in (_OMEGA_BOX[0], _OMEGA_BOX[1]):
            t.append(raw, style=item_s)
        elif _OMEGA_LOGO_ROWS[0] <= i <= _OMEGA_LOGO_ROWS[1]:
            row_style = logo_row_styles[i]
            for ch in raw:
                t.append(ch, style=item_s if ch == "│" else row_style)
        elif i == _SHIELD_ANGLE_LINE:
            # L'angle : coins "▀█" / "█▀" en renfort title_s
            n = len(raw)
            for idx, ch in enumerate(raw):
                if idx < 2 or idx >= n - 2:
                    t.append(ch, style=title_s)
                elif ch == "▒":
                    t.append(ch, style=heading_s)
                else:
                    t.append(ch, style=item_s)
        elif i == _SHIELD[1]:
            # Test : ligne 20 "▀██▓██▀" entierement en heading_s
            for ch in raw:
                t.append(ch, style=title_s)
        elif _SHIELD[0] <= i <= _SHIELD[1]:
            # Reste du bouclier (9-13, 15-19) : inchange
            for ch in raw:
                t.append(ch, style=heading_s if ch == "▒" else item_s)
        else:
            for ch in raw:
                t.append(ch, style=title_s if ch == "|" else item_s)
        lines.append(Align.center(t))
    return Group(*lines)

# ----------------------------------------------------------------------
# Textes du splash screen
# ----------------------------------------------------------------------
HEADER_LINE = "󰦝️ Omega-Fire"
HEADER_LINE_ASCII = "Omega-Fire"

SUBTITLE_LINE = "Poste de gestion de sécurité réseau"
SUBTITLE_LINE_ASCII = "Poste de gestion de securite reseau"

# Conservees pour reutilisation eventuelle ailleurs - plus affichees ici,
# le logo integre deja sa propre tagline ("FIREWALL | RULES | ...").
TAGLINE_LINE_1 = "Firewall, Rules, BAN & IP Control, Orchestration,"
TAGLINE_LINE_2 = "Logs Manager, Audit, Export, Backup & Monitoring ..."

VERSION = "v3.0"


# ----------------------------------------------------------------------
# Key capture (same as app.py)
# ----------------------------------------------------------------------
def _set_nonblocking(fd: int) -> None:
    flags = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)


def _set_blocking(fd: int) -> None:
    flags = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, flags & ~os.O_NONBLOCK)


def _flush_stdin() -> None:
    try:
        termios.tcflush(sys.stdin.fileno(), termios.TCIFLUSH)
    except Exception:
        pass


def _getch() -> str:
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        _flush_stdin()
        tty.setcbreak(fd)
        first = sys.stdin.read(1)
        if first != '\x1b':
            _flush_stdin()
            return first
        _set_nonblocking(fd)
        try:
            seq = ''
            for _ in range(5):
                try:
                    ch = sys.stdin.read(1)
                    if ch:
                        seq += ch
                    else:
                        break
                except (IOError, OSError):
                    break
        finally:
            _set_blocking(fd)
        _flush_stdin()
        return '\x1b' + seq
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


# ----------------------------------------------------------------------
# Footer text (splash-specific) - uses keybindings constants
# ----------------------------------------------------------------------
def _render_splash_footer(use_emoji: bool) -> Text:
    """Render the splash screen footer with standard keybindings."""
    key_s = theme_registry.get_style("footer.key")
    label_s = theme_registry.get_style("footer.label")
    sep_s = theme_registry.get_style("footer.separator")

    footer = Text()
    footer.append(f"  {kb.KEY_UP_DOWN}", style=key_s)
    footer.append(f" {kb.LABEL_NAVIGATE}", style=label_s)
    footer.append(" │ ", style=sep_s)
    footer.append(kb.KEY_ENTER, style=key_s)
    footer.append(f" {kb.LABEL_VALIDATE}", style=label_s)
    footer.append(" │ ", style=sep_s)
    footer.append(kb.KEY_A, style=key_s)
    footer.append(f" {kb.LABEL_HELP}", style=label_s)
    footer.append(" │ ", style=sep_s)
    footer.append(kb.KEY_T, style=key_s)
    footer.append(f" {kb.LABEL_THEME}", style=label_s)
    footer.append(" │ ", style=sep_s)
    footer.append(kb.KEY_Q, style=key_s)
    footer.append(f" {kb.LABEL_QUIT}", style=label_s)
    return footer


# ----------------------------------------------------------------------
# Overlay builders (same as app.py)
# ----------------------------------------------------------------------
def _get_available_themes() -> list[str]:
    """Get all available themes dynamically from the registry."""
    try:
        names = theme_registry.get_theme_names()
        if names:
            return sorted(names)
    except Exception:
        pass
    return ["omega-base", "omega-dark", "omega-light", "omega-neon", "omega-mono"]


def _build_help_body() -> Group:
    """Build the help overlay content using Rich visual style."""
    heading_s = theme_registry.get_style("text.heading")
    key_s = theme_registry.get_style("footer.key")
    label_s = theme_registry.get_style("footer.label")
    muted_s = theme_registry.get_style("text.muted")
    border_s = theme_registry.get_style("border.default")

    content = []
    content.append(Align.center(Text("AIDE - RACCOURCIS CLAVIER", style=heading_s)))
    content.append(Text(""))

    table = Table(
        show_header=True,
        header_style="bold",
        expand=True,
        border_style=border_s,
    )
    table.add_column("Touche", style=key_s, width=15, justify="center")
    table.add_column("Action", style=label_s)

    shortcuts = [
        ("↑ / ↓", "Naviguer dans les menus et listes"),
        ("← / Esc", "Retour au menu parent"),
        ("→ / Enter", "Valider / Entrer dans un sous-menu"),
        ("a", "Afficher cette aide"),
        ("t", "Ouvrir le sélecteur de thème"),
        ("q", "Quitter l'application"),
        ("Ctrl+C", "Quitter immédiatement"),
    ]

    for key, action in shortcuts:
        table.add_row(key, action)

    content.append(table)
    content.append(Text(""))
    content.append(Align.center(Text(
        "Appuyez sur Esc ou Enter pour fermer cette aide",
        style=muted_s,
    )))

    return Group(*content)


def _build_theme_select_body(selected_index: int) -> Group:
    """Build the theme selection overlay content using Rich visual style."""
    heading_s = theme_registry.get_style("text.heading")
    selected_s = theme_registry.get_style("menu.selected")
    item_s = theme_registry.get_style("menu.item")
    muted_s = theme_registry.get_style("text.muted")

    current_name = theme_registry.get_active().name
    available_themes = _get_available_themes()

    content = []
    content.append(Align.center(Text("SÉLECTIONNEZ UN THÈME", style=heading_s)))
    content.append(Text(""))

    for i, theme_name in enumerate(available_themes):
        is_current = (theme_name == current_name)
        is_selected = (i == selected_index)

        line = Text()
        marker = "★" if is_current else " "

        if is_selected:
            line.append(f"  ▸ {marker} {theme_name}", style=selected_s)
            if is_current:
                line.append("  (actif)", style=selected_s)
        else:
            line.append(f"    {marker} {theme_name}", style=item_s)
            if is_current:
                line.append("  (actif)", style=muted_s)

        content.append(line)
        content.append(Text(""))

    content.append(Align.center(Text(
        "↑↓ Naviguer │ Enter Valider │ Esc Annuler",
        style=muted_s,
    )))

    return Group(*content)


# ----------------------------------------------------------------------
# Main splash renderer (SPLASH model with keyboard capture)
# ----------------------------------------------------------------------
def render_splash(
    console: Optional[Console] = None,
    wait_for_key: bool = True,
) -> bool:
    """Render the splash screen using the SPLASH model.
    
    CRITICAL: Uses theme_registry.get_style() for splash text colors.
    This ensures the text actually changes when the theme changes,
    instead of using hardcoded splash_*_style properties.
    
    Captures keyboard shortcuts (a, t, q) like the main menu.
    Shows overlays for help and theme selection.

    Returns:
        True si l'utilisateur a validé (Entrée) — bootstrap.py doit
        poursuivre vers l'application ; False s'il a quitté (q/Ctrl+C) —
        bootstrap.py doit fermer proprement. Bug réel corrigé référentiel
        §51 (2026-08-17) : la fonction ne retournait jamais rien
        explicitement (implicitement None, toujours "falsy"), donc
        l'application se fermait systématiquement après le splash quelle
        que soit la touche pressée.
    """
    console = console or Console(theme=theme_registry.get_rich_theme())
    theme = theme_registry.get_active()
    use_emoji = theme.prefers_emojis
    
    # Overlay state
    overlay_mode = ""  # "", "help", "theme_select"
    overlay_selected = 0
    
    def build_layout() -> Layout:
        """Build the complete splash screen layout."""
        # Refresh theme reference (in case theme changed during splash)
        current_theme = theme_registry.get_active()
        current_use_emoji = current_theme.prefers_emojis
        
        root = Layout()
        root.split_column(
            Layout(name="header", size=3),
            Layout(name="body", ratio=1),
            Layout(name="prompt", size=3),
            Layout(name="footer", size=3),
        )
        
        # === HEADER ===
        term_width = get_terminal_width()
        term_height = get_terminal_height()
        
        shield = "\U0001f6e1\ufe0f " if current_use_emoji else ""
        header_text = Text()
        header_text.append(f"{shield}OMEGA-FIRE {VERSION}", style=theme_registry.get_style("menu.title"))
        header_text.append(f"       │  ", style=theme_registry.get_style("text.muted"))
        header_text.append(f"Thème: {current_theme.display_name}", style=theme_registry.get_style("text.muted"))
        header_text.append(f"  │  Terminal: {term_width}x{term_height}", style=theme_registry.get_style("text.muted"))
        
        root["header"].update(
            Panel(header_text, border_style=theme_registry.get_style("border.default"), padding=(0, 2))
        )
        
        # === BODY ===
        if overlay_mode == "help":
            root["body"].update(
                Panel(
                    Align.center(_build_help_body(), vertical="middle"),
                    border_style=theme_registry.get_style("border.default"),
                    padding=(1, 2),
                )
            )
        elif overlay_mode == "theme_select":
            root["body"].update(
                Panel(
                    Align.center(_build_theme_select_body(overlay_selected), vertical="middle"),
                    border_style=theme_registry.get_style("border.default"),
                    padding=(1, 2),
                )
            )
        else:
            # Normal splash content - CRITICAL: use dynamic theme styles
            body_content = []
            
            # Title & Subtitle use text.heading (changes with theme)
            title = HEADER_LINE if current_use_emoji else HEADER_LINE_ASCII
            body_content.append(Align.center(Text(title, style=theme_registry.get_style("text.heading"))))
            
            subtitle = SUBTITLE_LINE if current_use_emoji else SUBTITLE_LINE_ASCII
            body_content.append(Align.center(Text(subtitle, style=theme_registry.get_style("text.heading"))))
            body_content.append(Text(""))
            
            # Logo : bouclier + banniere, colore par zone via theme_registry
            body_content.append(_render_omega_fire_logo())
            
            body_group = Group(*body_content)
            
            root["body"].update(
                Panel(
                    Align.center(body_group, vertical="middle"),
                    border_style=theme_registry.get_style("border.default"),
                    padding=(1, 2),
                )
            )
        
        # === PROMPT ===
        if overlay_mode:
            prompt_text = Text(
                "  Overlay actif - Esc pour fermer",
                style=theme_registry.get_style("text.muted"),
            )
        else:
            prompt_text = Text(
                "  Appuyez sur Enter pour continuer...",
                style=theme_registry.get_style("text.main"),
            )
        root["prompt"].update(
            Panel(prompt_text, border_style=theme_registry.get_style("border.default"), padding=(0, 2))
        )
        
        # === FOOTER ===
        footer_text = _render_splash_footer(current_use_emoji)
        root["footer"].update(
            Panel(footer_text, border_style=theme_registry.get_style("border.default"), padding=(0, 2))
        )
        
        return root
    
    # Entrée = poursuivre, q/Ctrl+C = quitter — cf. docstring et
    # référentiel §51. Défaut True : wait_for_key=False (pas d'attente
    # de touche) doit laisser l'appelant poursuivre normalement.
    should_proceed = True

    console.clear()
    with Live(build_layout(), console=console, screen=True, refresh_per_second=4) as live:
        stop_event = threading.Event()

        def refresh_loop():
            while not stop_event.is_set():
                live.update(build_layout())
                stop_event.wait(2)

        refresh_thread = threading.Thread(target=refresh_loop, daemon=True)
        refresh_thread.start()

        if wait_for_key:
            try:
                while True:
                    key = _getch()

                    # === OVERLAY MODE: HELP ===
                    if overlay_mode == "help":
                        if kb.is_escape(key) or kb.is_enter(key) or kb.is_help(key):
                            overlay_mode = ""
                            live.update(build_layout())
                        elif kb.is_quit(key):
                            should_proceed = False
                            break
                        continue

                    # === OVERLAY MODE: THEME SELECT ===
                    if overlay_mode == "theme_select":
                        available_themes = _get_available_themes()
                        if kb.is_escape(key):
                            overlay_mode = ""
                            live.update(build_layout())
                        elif kb.is_arrow_up(key):
                            overlay_selected = (overlay_selected - 1) % len(available_themes)
                            live.update(build_layout())
                        elif kb.is_arrow_down(key):
                            overlay_selected = (overlay_selected + 1) % len(available_themes)
                            live.update(build_layout())
                        elif kb.is_enter(key) or kb.is_arrow_right(key):
                            selected_theme = available_themes[overlay_selected]
                            try:
                                theme_registry.set_active(selected_theme, force=True)
                                # CRITICAL: Update the console's theme after change
                                console._theme = theme_registry.get_rich_theme()
                            except Exception:
                                pass
                            overlay_mode = ""
                            live.update(build_layout())
                        elif kb.is_quit(key):
                            should_proceed = False
                            break
                        continue

                    # === NORMAL MODE ===
                    if kb.is_help(key):
                        overlay_mode = "help"
                        live.update(build_layout())
                    elif kb.is_theme(key):
                        available_themes = _get_available_themes()
                        try:
                            current_idx = available_themes.index(theme_registry.get_active().name)
                        except ValueError:
                            current_idx = 0
                        overlay_mode = "theme_select"
                        overlay_selected = current_idx
                        live.update(build_layout())
                    elif kb.is_enter(key):
                        should_proceed = True
                        break
                    elif kb.is_quit(key):
                        should_proceed = False
                        break

            except (EOFError, KeyboardInterrupt):
                should_proceed = False
        else:
            stop_event.set()
            refresh_thread.join(timeout=1)
            return True

        stop_event.set()
        refresh_thread.join(timeout=1)

    return should_proceed


# <-- INFO DEV ---------------------------------------------------------
# Role :
# - Ecran d'accueil Omega-Fire affiche au demarrage de l'application
# - Utilise le modele SPLASH : Live(screen=True) + Layout + thread
# - Redraw propre au redimensionnement de fenetre
# - Capture les raccourcis clavier (a, t, q) comme le menu principal
# - Affiche les overlays d'aide et de selection de theme
#
# Pourquoi dans interfaces/cli/renderers/ (charte) :
# - Rendu pur, aucune logique metier
# - Utilise uniquement Rich (Layout, Live, Panel, Text), theme_registry et styles.py
# - Utilise keybindings.py pour les constantes de raccourcis
# - Pas de dependance vers domain/, application/, infrastructure/
# - Respecte la regle de dependance : dependances vers l'interieur uniquement
#
# Ce qu'il ne contient PAS :
# - Pas de logique metier (pas de regles firewall, pas de decisions)
# - Pas d'appels systeme directs (pas de subprocess, pas de systemctl)
# - Pas de couleurs hardcodees (tout vient des themes via theme_registry)
# - Pas de modification du registre (lecture seule des styles)
# - Pas de logique de navigation (geree par interfaces/cli/app.py)
# - Pas de definitions de raccourcis (c'est keybindings.py)
#
# Points cles :
# - OMEGA_FIRE_LOGO_LINES : logo ASCII valide (23 lignes, bouclier + banniere).
#   Le logo OMEGA-FIRE (lignes 5-7, a l'interieur de son container) est le
#   MEME logo box-drawing que celui du menu principal (app.py, MAIN_MENU_LOGO_LINES) -
#   remplace l'ancienne banniere figlet. Colore en 3 nuances (haut/bas vif =
#   menu.title, milieu normal = menu.item), regle validee sur le menu principal
#   puis reprise ici a l'identique. Toutes les autres couleurs (cadres, bouclier,
#   omega incruste) restent inchangees par rapport a la version precedente.
# - HEADER_LINE / SUBTITLE_LINE : textes au-dessus du logo
# - TAGLINE_LINE_1 / TAGLINE_LINE_2 : conservees pour reutilisation eventuelle,
#   plus affichees ici (le logo integre deja sa propre tagline)
# - VERSION : version de l'application affichee dans le header
# - CRITICAL : Utilise theme_registry.get_style("text.heading"), "text.main", "text.muted",
#   "menu.item", "menu.title" pour tout le texte du splash au lieu des proprietes
#   splash_*_style hardcodees. Cela garantit que les couleurs changent reellement
#   quand le theme change.
# - Tagline sur 2 lignes, centrees
# - Footer avec raccourcis standardises (keybindings.py) :
#     * ↑↓ Naviguer │ Enter Valider │ a Aide │ t Thème │ q Quitter
# - Fallback ASCII automatique si le theme ne supporte pas les emojis
# - Parametre wait_for_key=False pour les tests sans attente
# - Mode alternate screen (screen=True) pour controle total du terminal
# - Thread de refresh toutes les 2 secondes pour redraw propre au resize
#
# CRITICAL - Application du theme :
# - La Console est creee avec theme=theme_registry.get_rich_theme()
# - Les textes du splash utilisent theme_registry.get_style(...) qui sont
#   definis differemment dans chaque theme.
# - Apres changement de theme via overlay, on met a jour console._theme
#   pour que le nouveau theme soit pris en compte immediatement.
# - build_layout() relit theme_registry.get_active() a chaque appel
#   pour prendre en compte les changements de theme en cours de splash.
#
# Capture clavier :
# - Utilise _getch() (meme implementation que app.py)
# - Capture les touches a, t, q, Enter, Esc, fleches
# - Gere les overlays help et theme_select comme le menu principal
# - Coherence totale des raccourcis entre splash et menu
#
# Overlays :
# - Mode "help" : affiche un tableau Rich avec tous les raccourcis
#   Ferme avec Esc, Enter ou a
# - Mode "theme_select" : affiche la liste DYNAMIQUE des themes avec selection
#   ↑↓ pour naviguer, Enter pour appliquer, Esc pour annuler
#   Le theme actif est marque avec ★, la selection avec ▸
#   Applique le theme avec force=True pour eviter le fallback automatique
#   Met a jour console._theme pour prise en compte immediate
#
# CRITICAL - Footer :
# - Utilise le caractere "│" directement comme separateur
# - N'utilise PAS theme_registry.get_style('footer.separator') comme texte
#   car get_style() retourne un objet Style, pas une chaine
# - Les constantes de raccourcis viennent de keybindings.py (KEY_UP_DOWN, KEY_ENTER, etc.)
# - Garantit la coherence avec le footer du menu principal (app.py)
#
# Coherence avec app.py :
# - Le footer affiche EXACTEMENT les memes raccourcis que le menu principal
# - Les deux utilisent les constantes de keybindings.py
# - Les deux utilisent les memes overlays (help et theme_select)
# - Les deux utilisent _getch() pour la capture clavier
# - Les deux appliquent le Rich Theme actif a leur Console
# - Cela garantit une experience utilisateur coherente dans toute l'application
# - Raccourcis : ↑↓ Naviguer │ Enter Valider │ a Aide │ t Thème │ q Quitter
#
# Integration prevue :
# - app/bootstrap.py appellera render_splash() au demarrage de l'application
# - Le splash screen est affiche avant le menu principal
# - L'utilisateur peut tester les themes et voir l'aide avant d'entrer dans le menu
# - Appuyer sur Enter pour acceder au menu principal
#---------------------------------------------------------------------->
