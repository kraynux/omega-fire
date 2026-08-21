# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""CLI application main loop.

Interactive menu with arrow key navigation.
Uses real ActionRegistry to execute application use cases.

Conforms to Omega-Fire architecture charter:
- Pure navigation and rendering, no business logic
- No direct backend calls
- Actions executed via ActionRegistry with ActionContext
- Graying handled by tree_builder.py based on capability registry
"""
from __future__ import annotations

import signal
from dataclasses import dataclass
from typing import Any, Optional

from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from rich.live import Live
from rich.layout import Layout
from rich.table import Table
from rich import box

from omega_fire.core.capability_registry import CapabilityRegistry
from omega_fire.interfaces.cli.themes.registry import theme_registry
from omega_fire.interfaces.cli.renderers.styles import get_terminal_width, get_terminal_height
from omega_fire.interfaces.cli.renderers.icons import menu_icon
from omega_fire.interfaces.cli.menu_builder import build_main_menu
from omega_fire.interfaces.cli.tree_builder import build_menu_tree
from omega_fire.interfaces.cli.actions import (
    ActionRegistry,
    ActionContext,
    action_quit,
    action_5_1_live_tail,
    action_8_1_live_dashboard,
    action_8_6_lnav_analysis,
)
from omega_fire.interfaces.cli import keybindings as kb
from omega_fire.interfaces.cli.renderers.frame import render_frame, FrameMode
from omega_fire.interfaces.cli.renderers.pager import paginated
from omega_fire.interfaces.cli.help_text import get_help_entry

MAIN_MENU_LOGO_LINES = [
    "┌╦═══╦┐ ┌╦═╦═╦┐ ┌╦═══╦┐ ┌╦═══╦┐ ┌╦═══╦┐   ┌╦═══╦┐ ┌═╤╦╤═┐ ┌╦═══╦┐ ┌╦═══╦┐",
    "│║   ║│ │║ ║ ║│ ├╬══    │║  ═╦┐ ├╬═══╬┤ ═ ├╬══      │║│   │╠══╦╩┘ ├╬══   ",
    "└╩═══╩┘ └╩   ╩┘ └╩═══╩┘ └╩═══╩┘ └╩   ╩┘   └╩      └═╧╩╧═┘ └╩  ╚═┘ └╩═══╩┘",
]
MAIN_MENU_LOGO_SPLIT = 42  # colonne de coupure entre OMEGA et FIRE, verifiee sur les 3 lignes

# ----------------------------------------------------------------------
# Navigation state
# ----------------------------------------------------------------------
@dataclass
class NavigationState:
    """State of the navigation through the menu tree."""
    current_node: Any
    selected_index: int
    breadcrumb: list[str]
    nav_stack: list[tuple[Any, int]]
    running: bool
    needs_redraw: bool
    message: str = ""
    menu_root: Any = None
    overlay_mode: str = ""
    overlay_selected: int = 0
    jump_buffer: str = ""


# ----------------------------------------------------------------------
# Footer builder
# ----------------------------------------------------------------------
def _build_footer(overlay_mode: str = "") -> Text:
    """Build the footer, matching only the keys that actually work in
    the current mode.

    Previously a single fixed footer was shown regardless of
    overlay_mode, advertising shortcuts (notably [t] Thème) that the
    help and theme-select overlays never handled — a dead key from the
    user's point of view. Each mode now lists exactly what responds.
    """
    key_s = theme_registry.get_style("footer.key")
    label_s = theme_registry.get_style("footer.label")
    sep_s = theme_registry.get_style("footer.separator")
    footer = Text()

    def _entry(key: str, label: str, first: bool = False) -> None:
        if not first:
            footer.append(" │ ", style=sep_s)
        footer.append(f"  {key}" if first else key, style=key_s)
        footer.append(f" {label}", style=label_s)

    if overlay_mode == "help":
        _entry(f"{kb.KEY_ENTER}/{kb.KEY_ESC}/{kb.KEY_A}", "Fermer", first=True)
        _entry(kb.KEY_Q, kb.LABEL_QUIT)
    elif overlay_mode == "theme_select":
        _entry(kb.KEY_UP_DOWN, kb.LABEL_NAVIGATE, first=True)
        _entry(kb.KEY_ENTER, kb.LABEL_VALIDATE)
        _entry(kb.KEY_ESC, "Annuler")
        _entry(kb.KEY_Q, kb.LABEL_QUIT)
    else:
        _entry(kb.KEY_UP_DOWN, kb.LABEL_NAVIGATE, first=True)
        _entry(kb.KEY_ENTER, kb.LABEL_VALIDATE)
        _entry(kb.KEY_ESC, kb.LABEL_BACK)
        _entry(kb.KEY_A, kb.LABEL_HELP)
        _entry(kb.KEY_T, kb.LABEL_THEME)
        _entry(kb.KEY_R, kb.LABEL_REFRESH)
        _entry(kb.KEY_Q, kb.LABEL_QUIT)

    return footer


# ----------------------------------------------------------------------
# Theme helpers
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


# ----------------------------------------------------------------------
# Menu id shortcut (type "2.1" + Enter to jump there)
# ----------------------------------------------------------------------
def _resolve_menu_shortcut(menu_root: Any, typed: str) -> Optional[list]:
    """Resolve a typed id like "2.1" or "4" to the chain of nodes from
    the top-level section down to the target.

    The app's menu tree is uniformly two levels deep (root -> section
    -> leaf, see menu_builder.py) — this is a direct two-level lookup,
    not a generic arbitrary-depth path walker, because that's what the
    real tree actually looks like everywhere.

    Args:
        menu_root: The root MenuNode (state.menu_root).
        typed: The accumulated digits/dots typed by the user.

    Returns:
        [section] if typed matches a top-level section id (e.g. "4",
        or "0" for Quitter) ; [section, leaf] if typed matches a leaf
        under that section (e.g. "4.2") ; None if nothing matches.
    """
    typed = typed.strip()
    if not typed:
        return None
    section_id = typed.split(".", 1)[0]
    section = menu_root.find_child(section_id)
    if section is None:
        return None
    if section.id == typed:
        return [section]
    leaf = section.find_child(typed)
    if leaf is None:
        return None
    return [section, leaf]


def _jump_to_menu_path(state: "NavigationState", path: list) -> None:
    """Move the cursor to the given path, always resolved from the
    menu root — an absolute jump regardless of where the cursor
    currently was (works the same whether triggered from the main
    menu or from inside any sub-section).

    Rebuilds nav_stack/breadcrumb exactly as if the user had manually
    arrowed/Entered their way there, so Esc/Left afterward behaves
    normally. Positions the cursor on the target but never executes a
    leaf action by itself — landing on "2.1" highlights it, a further
    Enter is still needed to run it (deliberate: a typo in the
    shortcut should never silently trigger an action).
    """
    state.current_node = state.menu_root
    state.selected_index = 0
    state.nav_stack = []
    state.breadcrumb = ["Menu Principal"]

    for node in path:
        siblings = state.current_node.children
        idx = next((i for i, c in enumerate(siblings) if c.id == node.id), 0)
        state.selected_index = idx
        if node.children:
            state.nav_stack.append((state.current_node, state.selected_index))
            state.current_node = node
            state.selected_index = 0
            state.breadcrumb.append(node.label)


# ----------------------------------------------------------------------
# Overlay builders
# ----------------------------------------------------------------------
def _get_contextual_help_node(state: "NavigationState") -> Any:
    """Node the help overlay should describe: the currently highlighted
    child if browsing a list (a section or an action about to be
    entered/executed), otherwise the current node itself (e.g. a leaf
    with no children).

    This is what gives the help "continuity" across sub-sections: it
    always follows wherever the cursor currently is, at any depth.
    """
    children = state.current_node.children
    if children and 0 <= state.selected_index < len(children):
        return children[state.selected_index]
    return state.current_node


def _build_help_body(state: "NavigationState") -> Group:
    """Build the contextual help overlay content using Rich visual style.

    Shows a detailed guide (interfaces/cli/help_text.py) for the node
    the cursor currently points to, when one has been written. Falls
    back to the node's short menu_builder.py description if no
    detailed entry exists yet — never an empty overlay. The keyboard
    shortcuts legend is always shown below, regardless.
    """
    heading_s = theme_registry.get_style("text.heading")
    key_s = theme_registry.get_style("footer.key")
    label_s = theme_registry.get_style("footer.label")
    muted_s = theme_registry.get_style("text.muted")
    warning_s = theme_registry.get_style("action.warning")
    border_s = theme_registry.get_style("border.default")

    node = _get_contextual_help_node(state)
    entry = get_help_entry(node.id)

    content = []
    content.append(Align.center(Text(f"AIDE — {node.label}", style=heading_s)))
    content.append(Text(""))

    if entry is not None:
        content.append(Text(entry.summary, style=label_s))
        content.append(Text(""))

        if entry.usage:
            content.append(Text("Comment l'utiliser :", style=heading_s))
            for line in entry.usage:
                content.append(Text(f"  • {line}", style=label_s))
            content.append(Text(""))

        if entry.consequences:
            content.append(Text("Conséquences :", style=heading_s))
            for line in entry.consequences:
                content.append(Text(f"  • {line}", style=label_s))
            content.append(Text(""))

        if entry.warnings:
            content.append(Text("Points d'attention :", style=warning_s))
            for line in entry.warnings:
                content.append(Text(f"  ⚠ {line}", style=warning_s))
            content.append(Text(""))

        if entry.mechanism:
            content.append(Text("Sous le capot :", style=muted_s))
            content.append(Text(f"  {entry.mechanism}", style=muted_s))
            content.append(Text(""))
    else:
        fallback = node.description or "Aucune aide détaillée pour cette section pour l'instant."
        content.append(Text(fallback, style=label_s))
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
        ("0-9 . Enter", "Aller directement à un numéro de menu (ex: 2.1 puis Entrée)"),
        ("a", "Fermer cette aide"),
        ("t", "Ouvrir le sélecteur de thème"),
        ("r", "Rafraîchir l'affichage (recentrage après redimensionnement du terminal)"),
        ("q", "Quitter l'application"),
        ("Ctrl+C", "Quitter immédiatement"),
        ("◀ / ▶", "Pagination : page précédente / suivante (quand un affichage dépasse la hauteur du terminal)"),
        ("d", "Pagination : aller à la première page"),
        ("f", "Pagination : aller à la dernière page"),
        ("q", "Pagination : fermer l'affichage en cours (même touche que quitter l'application, sens selon le contexte)"),
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
            line.append(f"   ▸ {marker} {theme_name}", style=selected_s)
            if is_current:
                line.append("  (actif)", style=selected_s)
        else:
            line.append(f"     {marker} {theme_name}", style=item_s)
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
# Main layout builder
# ----------------------------------------------------------------------
def _build_layout(state: NavigationState) -> Layout:
    """Build the full screen layout."""
    current_node = state.current_node
    selected_index = state.selected_index
    breadcrumb = state.breadcrumb
    root = Layout()
    root.split_column(
        Layout(name="header", size=3),
        Layout(name="body", ratio=1),
        Layout(name="footer", size=3),
    )
    
    # === HEADER ===
    term_w = get_terminal_width()
    term_h = get_terminal_height()
    header_text = Text()
    header_text.append("🛡 OMEGA-FIRE v3.0", style=theme_registry.get_style("menu.title"))
    theme_name = theme_registry.get_active().display_name
    header_text.append(f"  │  {theme_name}  │  {term_w}x{term_h}",
                       style=theme_registry.get_style("text.muted"))
    root["header"].update(
        Panel(header_text, border_style=theme_registry.get_style("border.default"), padding=(0, 2))
    )
    
    # === BODY ===
    if state.overlay_mode == "help":
        root["body"].update(
            Panel(
                Align.center(_build_help_body(state), vertical="middle"),
                border_style=theme_registry.get_style("border.default"),
                padding=(1, 2),
            )
        )
    elif state.overlay_mode == "theme_select":
        root["body"].update(
            Panel(
                Align.center(_build_theme_select_body(state.overlay_selected), vertical="middle"),
                border_style=theme_registry.get_style("border.default"),
                padding=(1, 2),
            )
        )
    else:
        body_parts = []
        if len(breadcrumb) > 1:
            breadcrumb_panel = Panel(
                Text(" ▸ ".join(breadcrumb[-3:]), style=theme_registry.get_style("text.header")),
                border_style=theme_registry.get_style("border.accent"),
                box=box.ROUNDED,
                padding=(0, 1),
            )
            body_parts.append(breadcrumb_panel)
            body_parts.append(Text(""))
        title = current_node.label.upper() if current_node.id == "root" else current_node.label

        # Logo ASCII : uniquement sur le menu principal, jamais dans les sous-menus.
        # Meme couleur que l'intitule des entrees de menu (menu.item) - pas
        # border.accent, qui est reserve a la couleur du numero.
        if current_node.id == "root":
            vivid_style = theme_registry.get_style("menu.title")
            normal_style = theme_registry.get_style("menu.item")
            # Ligne du haut et du bas (traits horizontaux) en vif,
            # ligne du milieu (montants verticaux) en normal -> relief
            row_styles = [vivid_style, normal_style, vivid_style]
            for logo_line, row_style in zip(MAIN_MENU_LOGO_LINES, row_styles):
                body_parts.append(Align.center(Text(logo_line, style=row_style)))
            body_parts.append(Text(""))
            body_parts.append(Text(""))

        children = current_node.children
        menu_table = Table(
            box=box.ROUNDED,
            show_header=False,
            show_lines=True,
            expand=True,
            padding=(0, 1),
            border_style=theme_registry.get_style("border.default"),
        )
        menu_table.add_column("menu", ratio=1)

        for i, child in enumerate(children):
            icon = menu_icon(child.id) if current_node.id == "root" and child.id[0].isdigit() else "▸"
            is_selected = (i == selected_index)
            is_disabled = not child.enabled
            marker = "▸" if is_selected else " "

            cell = Text()
            id_style = theme_registry.get_style("border.accent")
            if is_disabled:
                cell.append(f"{marker} ", style="dim")
                cell.append(f"{child.id}.", style=id_style)
                cell.append(f" {icon} {child.label}", style="dim")
                cell.append("     (indisponible)", style="dim")
            elif is_selected:
                label_style = theme_registry.get_style("menu.selected")
                cell.append(f"{marker} ", style=label_style)
                cell.append(f"{child.id}.", style=id_style)
                cell.append(f" {icon} {child.label}", style=label_style)
            else:
                label_style = theme_registry.get_style("menu.item")
                cell.append(f"{marker} ", style=label_style)
                cell.append(f"{child.id}.", style=id_style)
                cell.append(f" {icon} {child.label}", style=label_style)
            if child.description and not is_disabled:
                cell.append(f"\n   {child.description}", style=theme_registry.get_style("text.muted"))

            menu_table.add_row(cell)

        section_panel = Panel(
            menu_table,
            title=Text(title, style=theme_registry.get_style("text.heading")),
            title_align="center",
            border_style=theme_registry.get_style("border.accent"),
            box=box.ROUNDED,
            padding=(0, 1),
        )
        body_parts.append(section_panel)

        if state.message:
            body_parts.append(Text(""))
            body_parts.append(Align.center(Text(state.message, style="bold yellow")))
        body_group = Group(*body_parts)
        root["body"].update(
            Panel(
                Align.center(body_group, vertical="middle"),
                border_style=theme_registry.get_style("border.default"),
                padding=(1, 2),
            )
        )
    
    # === FOOTER ===
    root["footer"].update(
        Panel(
            Align.center(_build_footer(state.overlay_mode)),
            border_style=theme_registry.get_style("border.default"),
            padding=(0, 1),
        )
    )
    return root


def _determine_footer_mode(action_id: str) -> str:
    return None


# ----------------------------------------------------------------------
# Confirmation de sortie
# ----------------------------------------------------------------------
def _confirm_exit(console: Console) -> bool:
    """Demande confirmation avant de quitter l'application."""
    console.show_cursor(True)
    console.print()

    dialog_width = min(get_terminal_width() - 10, 60)

    body = Group(
        Align.center(Text("⚠ Interruption détectée", style=theme_registry.get_style("menu.selected"))),
        Text(""),
        Align.center(Text("Historique et configuration conservés", style=theme_registry.get_style("text.header"))),
        Align.center(Text("Les règles du firewall restent actives", style=theme_registry.get_style("text.header"))),
    )
    question_panel = Panel(
        body,
        title="[ Fermeture d'Omega-Fire ]",
        title_align="center",
        border_style=theme_registry.get_style("border.accent"),
        box=box.ROUNDED,
        padding=(1, 3),
        width=dialog_width,
    )
    console.print(Align.center(question_panel))
    console.print()

    prompt_text = "Voulez-vous vraiment quitter l'application ? (o/N) : "
    term_w = get_terminal_width()
    box_left_margin = max((term_w - dialog_width) // 2, 0)
    prompt_pad = box_left_margin + max((dialog_width - len(prompt_text)) // 2, 0)

    try:
        response = console.input(" " * prompt_pad + f"[menu.selected]{prompt_text}[/menu.selected]").strip().lower()
        console.print()
        ... 
        console.print()
        if response in ["o", "oui", "y", "yes"]:
            result_panel = Panel(
                Align.center(Text("Session fermée avec succès. À bientôt !",
                                   style=theme_registry.get_style("border.accent"))),
                border_style=theme_registry.get_style("border.accent"),
                box=box.ROUNDED,
                padding=(1, 3),
                width=dialog_width,
            )
            console.print(Align.center(result_panel))
            return True
        else:
            result_panel = Panel(
                Align.center(Text("Reprise de la session...", style=theme_registry.get_style("text.muted"))),
                border_style=theme_registry.get_style("border.default"),
                box=box.ROUNDED,
                padding=(1, 3),
                width=dialog_width,
            )
            console.print(Align.center(result_panel))
            return False
    except (EOFError, KeyboardInterrupt):
        return False


def _handle_quit_key(
    state: "NavigationState",
    live: Live,
    console: Console,
    registry: CapabilityRegistry,
    container: Any,
) -> None:
    """Graceful quit sequence, shared by normal mode and any overlay.

    Stops the Live display and restores cursor visibility before going
    through action_quit() (save + confirmation) — never an abrupt
    `state.running = False` mid-render, which leaves the terminal in
    the alternate screen buffer with the cursor hidden (observed as a
    black screen). Restores the Live display if the user cancels.

    Previously only the normal-mode 'q' handler did this properly; the
    help and theme-select overlays used to just set state.running =
    False directly, skipping cleanup entirely.
    """
    try:
        live.stop()
        console.show_cursor(True)
        ctx = ActionContext(
            capability_registry=registry,
            console=console,
            container=container,
            state=state,
        )
        with paginated(console):
            action_quit(ctx)
        state.running = ctx.state.running
    except Exception as e:
        state.message = f"Erreur : {str(e)}"
    finally:
        if state.running:
            console.show_cursor(False)
            console.clear()
            live.start()
        state.needs_redraw = True


# ----------------------------------------------------------------------
# Main application loop
# ----------------------------------------------------------------------
def run_app(
    registry: CapabilityRegistry,
    console: Optional[Console] = None,
    container: Any = None,
) -> int:
    """Run the interactive CLI application."""
    console = console or Console()
    
    # 1. Create ActionRegistry with the capability registry
    action_registry = ActionRegistry(registry)
    
    # 2. Build the menu tree with actions wired via ActionRegistry._actions
    menu_root = build_main_menu(action_registry=action_registry._actions)
    
    # 3. Apply capability-based graying via tree_builder
    menu_root = build_menu_tree(menu_root, registry)
    
    # 4. Initialize navigation state
    state = NavigationState(
        current_node=menu_root,
        selected_index=0,
        breadcrumb=["Menu Principal"],
        nav_stack=[],
        running=True,
        needs_redraw=True,
        message="",
        menu_root=menu_root,
        overlay_mode="",
        overlay_selected=0,
    )
    
    # 5. Handle terminal resize
    def handle_resize(signum, frame):
        state.needs_redraw = True
    signal.signal(signal.SIGWINCH, handle_resize)
    
    console.clear()
    
    # 6. Main event loop
    # auto_refresh=False : toutes les mises à jour de cette boucle sont
    # déclenchées explicitement par une touche (state.needs_redraw +
    # live.update(..., refresh=True)) — jamais par un timer. Avec
    # auto_refresh=True (défaut), un thread d'arrière-plan tente un
    # refresh périodique et prend le même verrou interne que nos appels
    # explicites : une contention possible sur ce verrou, même brève,
    # ajoutait une latence perceptible et imprévisible en plus de celle
    # déjà corrigée par refresh=True. Aucun intérêt à garder ce thread
    # ici, rien n'anime l'écran entre deux touches.
    with Live(
        _build_layout(state),
        console=console,
        screen=True,
        auto_refresh=False,
    ) as live:
        while state.running:
            try:
                while state.running:
                    if state.needs_redraw:
                        # refresh=True force un redessin immédiat — sans lui,
                        # Live.update() (refresh=False par défaut) attend le
                        # prochain tick du thread d'auto-refresh interne
                        # (refresh_per_second=1 ci-dessus), donc jusqu'à ~1s
                        # de latence perçue après chaque touche, même si
                        # l'appel a lieu tout de suite.
                        live.update(_build_layout(state), refresh=True)
                        state.needs_redraw = False
                    
                    key = kb._getch()
                    
                    # === OVERLAY MODE: HELP ===
                    if state.overlay_mode == "help":
                        if kb.is_escape(key) or kb.is_enter(key) or kb.is_help(key):
                            state.overlay_mode = ""
                            state.needs_redraw = True
                        elif kb.is_quit(key):
                            _handle_quit_key(state, live, console, registry, container)
                        continue
                    
                    # === OVERLAY MODE: THEME SELECT ===
                    if state.overlay_mode == "theme_select":
                        available_themes = _get_available_themes()
                        if kb.is_escape(key):
                            state.overlay_mode = ""
                            state.needs_redraw = True
                        elif kb.is_arrow_up(key):
                            state.overlay_selected = (state.overlay_selected - 1) % len(available_themes)
                            state.needs_redraw = True
                        elif kb.is_arrow_down(key):
                            state.overlay_selected = (state.overlay_selected + 1) % len(available_themes)
                            state.needs_redraw = True
                        elif kb.is_enter(key) or kb.is_arrow_right(key):
                            selected_theme = available_themes[state.overlay_selected]
                            try:
                                theme_registry.set_active(selected_theme, force=True)
                            except Exception:
                                pass
                            state.overlay_mode = ""
                            state.needs_redraw = True
                        elif kb.is_quit(key):
                            _handle_quit_key(state, live, console, registry, container)
                        continue

                    # === NORMAL MODE ===

                    # --- Raccourci numérique (ex: "2.1" + Entrée) ---
                    # Intercepté avant tout le reste : les chiffres ne sont
                    # utilisés nulle part ailleurs en navigation normale
                    # (a/t/q, flèches, Entrée, Esc), donc aucune ambiguïté.
                    # Tant qu'un raccourci est en cours de saisie, seuls
                    # chiffres/point/Entrée/Esc sont pris en compte — le
                    # reste est ignoré pour éviter un état de navigation
                    # incohérent pendant la frappe.
                    if key.isdigit() or (key == "." and state.jump_buffer):
                        state.jump_buffer += key
                        state.message = f"Aller à : {state.jump_buffer}"
                        state.needs_redraw = True
                        continue
                    elif state.jump_buffer and kb.is_enter(key):
                        path = _resolve_menu_shortcut(state.menu_root, state.jump_buffer)
                        state.jump_buffer = ""
                        if path is None:
                            state.message = "Raccourci invalide."
                        else:
                            _jump_to_menu_path(state, path)
                            state.message = ""
                        state.needs_redraw = True
                        continue
                    elif state.jump_buffer and kb.is_escape(key):
                        state.jump_buffer = ""
                        state.message = ""
                        state.needs_redraw = True
                        continue
                    elif state.jump_buffer:
                        continue

                    if kb.is_refresh(key):
                        # Redessin forcé (SIGWINCH met déjà needs_redraw à
                        # True sur un redimensionnement, mais _getch()
                        # bloque jusqu'à la touche suivante — un appui
                        # explicite permet de recentrer immédiatement sans
                        # attendre une autre touche par hasard).
                        state.needs_redraw = True
                    elif kb.is_help(key):
                        state.overlay_mode = "help"
                        state.needs_redraw = True
                    elif kb.is_theme(key):
                        available_themes = _get_available_themes()
                        try:
                            current_idx = available_themes.index(theme_registry.get_active().name)
                        except ValueError:
                            current_idx = 0
                        state.overlay_mode = "theme_select"
                        state.overlay_selected = current_idx
                        state.needs_redraw = True
                    elif kb.is_arrow_up(key):
                        state.message = ""
                        children = state.current_node.children
                        if children:
                            state.selected_index = (state.selected_index - 1) % len(children)
                            state.needs_redraw = True
                    elif kb.is_arrow_down(key):
                        state.message = ""
                        children = state.current_node.children
                        if children:
                            state.selected_index = (state.selected_index + 1) % len(children)
                            state.needs_redraw = True
                    elif kb.is_arrow_left(key):
                        state.message = ""
                        if state.nav_stack:
                            state.current_node, state.selected_index = state.nav_stack.pop()
                            state.breadcrumb.pop()
                            state.needs_redraw = True
                    elif kb.is_arrow_right(key) or kb.is_enter(key):
                        state.message = ""
                        children = state.current_node.children
                        if not children:
                            continue
                        child = children[state.selected_index]
                        if not child.enabled:
                            state.message = "Cette section est indisponible"
                            state.needs_redraw = True
                            continue
                        
                        # Special case: Quit
                        if child.id == "0":
                            if child.action:
                                try:
                                    live.stop()
                                    console.show_cursor(True)
                                    ctx = ActionContext(
                                        capability_registry=registry,
                                        console=console,
                                        container=container,
                                        state=state,
                                    )
                                    with paginated(console):
                                        child.action(ctx)
                                    # Synchronisation explicite de l'arrêt
                                    state.running = ctx.state.running
                                except Exception as e:
                                    state.message = f"Erreur : {str(e)}"
                                finally:
                                    if state.running:
                                        try:
                                            console.show_cursor(False)
                                            console.clear()
                                            live.start()
                                        except Exception:
                                            pass
                                        state.needs_redraw = True
                            continue
                        
                        # Submenu: enter it
                        if child.children:
                            state.nav_stack.append((state.current_node, state.selected_index))
                            state.current_node = child
                            state.selected_index = 0
                            state.breadcrumb.append(child.label)
                            state.needs_redraw = True
                        
                        # Leaf node with action: execute it
                        elif child.is_leaf() and child.is_actionable():
                            try:
                                live.stop()
                                console.show_cursor(True)
                                console.clear()

                                ctx = ActionContext(
                                    capability_registry=registry,
                                    console=console,
                                    container=container,
                                    state=state,
                                )

                                if child.action in (action_5_1_live_tail, action_8_1_live_dashboard, action_8_6_lnav_analysis):
                                    # Écrans à rafraîchissement continu ou à
                                    # prise de contrôle complète du terminal
                                    # (Live Tail, Tableau de bord temps réel,
                                    # analyse lnav 8.6 — pty + écran alternatif) :
                                    # incompatibles avec la pagination, qui ne
                                    # vide son buffer qu'au prochain input()
                                    # réel — le contenu resterait bufferisé
                                    # indéfiniment et casserait l'effet live.
                                    # Exclusion par référence de fonction (pas
                                    # par id) : le menu "8.5" (Menu 8) pointe
                                    # vers le même action_5_1_live_tail que
                                    # "5.1" (Menu 5) — un id seul ne suffit
                                    # pas à couvrir cet alias.
                                    child.action(ctx)
                                else:
                                    with paginated(console):
                                        child.action(ctx)

                            except Exception as e:
                                state.message = f"Erreur : {str(e)}"
                            finally:
                                try:
                                    console.show_cursor(False)
                                    console.clear()
                                    live.start()
                                except Exception:
                                    pass
                                state.needs_redraw = True
                                
                    elif kb.is_escape(key):
                        state.message = ""
                        if state.nav_stack:
                            state.current_node, state.selected_index = state.nav_stack.pop()
                            state.breadcrumb.pop()
                            state.needs_redraw = True
                        else:
                            # ESC au menu principal : demander confirmation
                            try:
                                live.stop()
                                if _confirm_exit(console):
                                    state.running = False
                                else:
                                    console.clear()
                                    console.show_cursor(False)
                                    live.start()
                                    state.needs_redraw = True
                            except Exception:
                                state.running = False

                    # Quit (q) en mode normal -> flow classique (action_quit),
                    # partagé avec les overlays via _handle_quit_key()
                    elif kb.is_quit(key):
                        _handle_quit_key(state, live, console, registry, container)

            except (EOFError, KeyboardInterrupt):
                # CTRL+C dans les menus : demander confirmation
                try:
                    live.stop()
                    if _confirm_exit(console):
                        state.running = False
                    else:
                        console.clear()
                        console.show_cursor(False)
                        live.start()
                        state.needs_redraw = True
                except Exception:
                    state.running = False

    return 0
# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Boucle principale de l'application CLI interactive.
# - Navigation avec flèches, Enter, Esc, a, t, q.
# - Overlays pour aide et sélection de thème.
# - Exécute les actions via ActionRegistry avec ActionContext.
#
# Pourquoi dans interfaces/cli/ (charte) :
# - Navigation, prompts et rendu uniquement.
# - Pas de logique métier.
# - Pas d'appels système directs.
# - Actions exécutées via ActionRegistry (pas d'appel direct aux backends).
#
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier (c'est le rôle de domain/).
# ❌ Pas d'appels système (c'est le rôle de infrastructure/).
# ❌ Pas de décision de grisage (c'est le rôle de tree_builder.py).
# ❌ Pas de dépendance vers application/ ou infrastructure/.
#
# Points clés :
# - NavigationState : dataclass qui contient l'état de navigation.
# - run_app() : fonction principale qui démarre l'application.
# - Crée ActionRegistry avec capability_registry.
# - Construit l'arbre via build_main_menu(action_registry._actions).
# - Applique le grisage via build_menu_tree(menu_root, registry).
# - Boucle Live avec refresh 1Hz.
# - Gère les overlays (help, theme_select) et la navigation normale.
# - Exécute les actions avec ActionContext(registry, console, container, state).
# - FIX CRITIQUE : live.stop() / console.show_cursor(True) avant l'action,
#   et live.start() / console.show_cursor(False) dans le bloc finally.
# - Gère SIGWINCH pour redimensionnement terminal.
# - Footer standardisé via keybindings constants.
#---------------------------------------------------------------------->
