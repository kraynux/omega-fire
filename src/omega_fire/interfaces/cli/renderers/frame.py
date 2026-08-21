# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Global frame renderer for Omega-Fire CLI.

Provides a single, robust outer container with fixed thin borders,
dynamic width adaptation, and context-aware footers.
Prevents dislocation by calculating inner widths dynamically at render time.

Conforms to Omega-Fire architecture charter:
- Pure rendering logic, no business rules
- Uses theme_registry for all styling
- No dependency on domain/, application/, or infrastructure/
"""
from typing import Optional, List, Callable

from rich.console import Console, RenderableType, Group
from rich.panel import Panel
from rich.text import Text
from rich.align import Align

from omega_fire.interfaces.cli.themes.registry import theme_registry
from omega_fire.interfaces.cli.renderers.styles import get_terminal_width, get_terminal_height


class FrameMode:
    """Available footer contexts."""
    MENU = "menu"
    SUBMENU = "submenu"
    INPUT = "input"
    CONFIRM = "confirm"
    LIST = "list"


class Frame:
    """Global application frame with header, content, and dynamic footer."""

    def __init__(self, console: Optional[Console] = None):
        self._console = console or Console()

    def render(
        self,
        content: RenderableType,
        footer_mode: str = FrameMode.MENU,
        input_line: Optional[str] = "Votre choix : █",
        header_extra: Optional[str] = None,
    ) -> None:
        """Render the complete framed interface."""
        term_width = get_terminal_width()
        
        # Outer panel width: leave 2 columns of margin on each side
        panel_width = max(term_width - 4, 40)
        
        # Inner width: panel_width minus 2 for borders (│) minus 2 for padding (1 left, 1 right)
        inner_width = panel_width - 4

        inner_parts = self._build_inner_content(
            content=content,
            footer_mode=footer_mode,
            input_line=input_line,
            header_extra=header_extra,
            inner_width=inner_width,
        )

        aligned_content = Align.left(Group(*inner_parts))

        panel = Panel(
            aligned_content,
            width=panel_width,
            border_style=theme_registry.get_style("border.default"),
            padding=(1, 1),
            expand=False,
        )

        centered_panel = Align.center(panel)

        self._console.print(centered_panel)

    def _build_inner_content(
        self,
        content: RenderableType,
        footer_mode: str,
        input_line: Optional[str],
        header_extra: Optional[str],
        inner_width: int,
    ) -> List[RenderableType]:
        parts: List[RenderableType] = []

        # 1. Header principal
        parts.append(self._render_header(header_extra))
        parts.append(self._render_separator(inner_width))

        # 2. Contenu principal de l'action / menu
        if isinstance(content, str):
            parts.append(Text(content))
        else:
            parts.append(content)

        parts.append(Text(""))

        # 3. Ligne d'interaction ou Footer (uniquement si spécifié)
        if input_line:
            parts.append(Text(input_line, style=theme_registry.get_style("text.main")))
            parts.append(Text(""))

        if footer_mode and footer_mode != "none":
            parts.append(self._render_separator(inner_width))
            parts.append(self._render_footer(footer_mode))

        return parts

    def _render_header(self, extra: Optional[str] = None) -> Text:
        title = Text("🛡  OMEGA-FIRE v3.0", style=theme_registry.get_style("menu.title"))
        theme_name = theme_registry.get_active().display_name
        theme_text = Text(f"  │  Thème: {theme_name}  │  ", style=theme_registry.get_style("text.muted"))
        
        term_width = get_terminal_width()
        term_height = get_terminal_height()
        
        size_text = Text(
            f"Terminal: {term_width}x{term_height}",
            style=theme_registry.get_style("text.muted"),
        )

        header = Text()
        header.append_text(title)
        header.append_text(theme_text)
        header.append_text(size_text)

        if extra:
            header.append(Text("  │  "))
            header.append(extra, style=theme_registry.get_style("text.heading"))

        return header

    def _render_separator(self, width: int) -> Text:
        """Render a horizontal separator that perfectly fits the inner panel width."""
        return Text("─" * width, style=theme_registry.get_style("border.default"))

    def _render_footer(self, mode: str) -> Text:
        footer = Text(style=theme_registry.get_style("text.muted"))

        mode_str = str(mode.value if hasattr(mode, 'value') else mode).lower()

        if "submenu" in mode_str:
            footer.append("≡  Sous-menu  │  ")
            footer.append("[T]hème", style=theme_registry.get_style("text.link"))
            footer.append("  │  ")
            footer.append("[A]ide", style=theme_registry.get_style("text.link"))
            footer.append("  │  ")
            footer.append("[M]enu principal", style=theme_registry.get_style("text.link"))
            footer.append("  │  ")
            footer.append("[Q]uitter", style=theme_registry.get_style("text.link"))

        elif "input" in mode_str:
            footer.append("✏  Saisie  │  ")
            footer.append("[Enter] Valider", style=theme_registry.get_style("action.info"))
            footer.append("  │  ")
            footer.append("[Esc] Annuler", style=theme_registry.get_style("action.warning"))
            footer.append("  │  ")
            footer.append("[Tab] Champ suivant", style=theme_registry.get_style("text.muted"))

        elif "confirm" in mode_str:
            footer.append("⚠  Confirmation  │  ")
            footer.append("o Oui", style=theme_registry.get_style("action.success"))
            footer.append("  │  ")
            footer.append("n Non", style=theme_registry.get_style("action.error"))
            footer.append("  │  ")
            footer.append("[Esc] Annuler", style=theme_registry.get_style("action.warning"))

        elif "list" in mode_str:
            footer.append("📋 Liste  │  ")
            footer.append("↑↓ Naviguer", style=theme_registry.get_style("text.link"))
            footer.append("  │  ")
            footer.append("[Enter] Valider", style=theme_registry.get_style("action.info"))
            footer.append("  │  ")
            footer.append("[Esc] Annuler", style=theme_registry.get_style("action.warning"))

        else:
            footer.append("📋 Menu  │  ")
            footer.append("[T]hème", style=theme_registry.get_style("text.link"))
            footer.append("  │  ")
            footer.append("[A]ide", style=theme_registry.get_style("text.link"))
            footer.append("  │  ")
            footer.append("[M]enu", style=theme_registry.get_style("text.link"))
            footer.append("  │  ")
            footer.append("[Q]uitter", style=theme_registry.get_style("text.link"))

        return footer


def render_frame(
    content: RenderableType,
    footer_mode: str = FrameMode.MENU,
    input_line: Optional[str] = "Votre choix : █",
    header_extra: Optional[str] = None,
    console: Optional[Console] = None,
) -> None:
    """Convenience function to render the global frame."""
    frame = Frame(console)
    frame.render(
        content=content,
        footer_mode=footer_mode,
        input_line=input_line,
        header_extra=header_extra,
    )


def render_action_frame(
    content_builder: Callable[[], RenderableType],
    footer_mode: str = FrameMode.SUBMENU,
    header_extra: Optional[str] = None,
    console: Optional[Console] = None,
) -> None:
    """Render an action's content within the global frame."""
    console = console or Console()
    content = content_builder()
    render_frame(
        content=content,
        footer_mode=footer_mode,
        input_line=None,
        header_extra=header_extra,
        console=console,
    )

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Container global robuste : un seul Panel avec bordures fines
# - Structure interne : header, séparateur, contenu, séparateur, footer
# - Empêche la dislocation en calculant dynamiquement inner_width = panel_width - 4
# - S'adapte au redimensionnement du terminal à chaque appel de render()
# Pourquoi dans interfaces/cli/renderers/ (charte) :
# - Rendu pur, aucune logique métier
# - Utilise uniquement Rich, theme_registry et layout.py
# - Pas de dépendance vers domain/, application/, infrastructure/
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier
# ❌ Pas de couleurs hardcodées
# ❌ Pas d'appels système
# ❌ Pas de Rule (pour respecter la contrainte utilisateur, géré via Text calculé)
# ❌ Pas de centrage interne du contenu (seul le Panel global est centré)
# Points clés :
# - panel_width = term_width - 4 (marges extérieures)
# - inner_width = panel_width - 4 (pour compenser les bordures │ et le padding)
# - _render_separator utilise inner_width pour garantir l'alignement parfait
# - Le contenu est Align.left à l'intérieur du Panel, le Panel est Align.center
# - footer_mode change dynamiquement les raccourcis affichés (Option B validée)
# Intégration prévue :
# - interfaces/cli/app.py utilisera render_frame() comme point d'entrée unique
# - interfaces/cli/renderers/dashboard.py l'utilisera pour le splash screen
# - Les actions passeront le bon footer_mode (INPUT, CONFIRM, etc.)
#---------------------------------------------------------------------->
