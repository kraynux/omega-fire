# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Rendering styles and layout utilities for Omega-Fire CLI.

Provides helpers for terminal size detection, dynamic text centering,
width calculations, truncation, wrapping, and optimal size hints.

All functions are pure rendering utilities with no business logic.
They are consumed by dashboard.py, tables.py, logs_live.py and
monitoring_live.py to adapt the display to the actual terminal size.

Conforms to Omega-Fire architecture charter:
- Pure rendering logic, no business rules
- No dependency on domain/, application/, or infrastructure/
- Uses only standard library (shutil) and Rich
"""

# Taille minimale du terminal pour lancer Omega-Fire
# En dessous, l'interface ne peut pas s'afficher correctement
MIN_TERMINAL_WIDTH = 80
MIN_TERMINAL_HEIGHT = 24
import shutil
from typing import Optional


# ----------------------------------------------------------------------
# Terminal size constants
# ----------------------------------------------------------------------
OPTIMAL_WIDTH = 120
OPTIMAL_HEIGHT = 40
MIN_WIDTH = 80
MIN_HEIGHT = 24


# ----------------------------------------------------------------------
# Terminal size detection
# ----------------------------------------------------------------------
def get_terminal_width() -> int:
    """Get the current terminal width in columns.
    
    Returns:
        Terminal width in columns (minimum MIN_WIDTH for safety).
    """
    try:
        size = shutil.get_terminal_size((MIN_WIDTH, MIN_HEIGHT))
        return max(size.columns, MIN_WIDTH)
    except Exception:
        return MIN_WIDTH


def get_terminal_height() -> int:
    """Get the current terminal height in rows.
    
    Returns:
        Terminal height in rows (minimum MIN_HEIGHT for safety).
    """
    try:
        size = shutil.get_terminal_size((MIN_WIDTH, MIN_HEIGHT))
        return max(size.lines, MIN_HEIGHT)
    except Exception:
        return MIN_HEIGHT


# ----------------------------------------------------------------------
# Text layout helpers
# ----------------------------------------------------------------------
def center_text(text: str, width: Optional[int] = None) -> str:
    """Center a text string within the given width.
    
    Args:
        text: Text to center.
        width: Optional width (uses terminal width if None).
    
    Returns:
        Centered text with left padding.
    """
    if width is None:
        width = get_terminal_width()
    
    text_len = len(text)
    if text_len >= width:
        return text
    
    padding = (width - text_len) // 2
    return " " * padding + text


def calculate_content_width(
    desired_width: int,
    terminal_width: Optional[int] = None,
) -> int:
    """Calculate the actual content width with margins.
    
    Args:
        desired_width: Desired content width.
        terminal_width: Optional terminal width (auto-detected if None).
    
    Returns:
        Actual content width (capped to terminal width minus 4 margin columns).
    """
    if terminal_width is None:
        terminal_width = get_terminal_width()
    
    # Leave 4 columns for margins (2 on each side)
    max_content = terminal_width - 4
    return min(desired_width, max_content)


def calculate_margins(
    content_width: int,
    terminal_width: Optional[int] = None,
) -> tuple[int, int]:
    """Calculate left and right margins for centering content.
    
    Args:
        content_width: Width of the content to center.
        terminal_width: Optional terminal width (auto-detected if None).
    
    Returns:
        Tuple of (left_margin, right_margin).
    """
    if terminal_width is None:
        terminal_width = get_terminal_width()
    
    total_margin = terminal_width - content_width
    if total_margin <= 0:
        return (0, 0)
    
    left = total_margin // 2
    right = total_margin - left
    return (left, right)


def calculate_inner_width(panel_width: int) -> int:
    """Calculate the inner width available inside a panel.
    
    This is the KEY formula to prevent border dislocation:
    inner_width = panel_width - 4 (2 for borders │, 2 for padding).
    
    Args:
        panel_width: Total width of the panel (including borders).
    
    Returns:
        Inner width available for content and separators.
    """
    return max(panel_width - 4, 1)


def calculate_panel_width(terminal_width: Optional[int] = None) -> int:
    """Calculate the outer panel width with terminal margins.
    
    The panel is centered in the terminal with 2 columns of margin
    on each side.
    
    Args:
        terminal_width: Optional terminal width (auto-detected if None).
    
    Returns:
        Panel width (terminal_width - 4), minimum 40.
    """
    if terminal_width is None:
        terminal_width = get_terminal_width()
    
    return max(terminal_width - 4, 40)


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to fit within max_length, adding suffix if needed.
    
    Args:
        text: Text to truncate.
        max_length: Maximum length including suffix.
        suffix: Suffix to add when truncating (default: "...").
    
    Returns:
        Truncated text with suffix if needed.
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def wrap_text(text: str, width: Optional[int] = None) -> list[str]:
    """Wrap text to fit within the given width.
    
    Args:
        text: Text to wrap.
        width: Optional width (uses terminal width if None).
    
    Returns:
        List of lines.
    """
    if width is None:
        width = get_terminal_width()
    
    words = text.split()
    lines: list[str] = []
    current_line: list[str] = []
    current_length = 0
    
    for word in words:
        word_len = len(word)
        separator_len = 1 if current_line else 0
        
        if current_length + separator_len + word_len > width:
            lines.append(" ".join(current_line))
            current_line = [word]
            current_length = word_len
        else:
            current_line.append(word)
            current_length += separator_len + word_len
    
    if current_line:
        lines.append(" ".join(current_line))
    
    return lines


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Helpers de rendu pur pour l'adaptation au terminal
# - Détection fiable via shutil.get_terminal_size()
# - Calculs de largeur pour garantir la continuité des bordures
# Pourquoi dans interfaces/cli/renderers/ (charte) :
# - Rendu pur, aucune logique métier
# - Utilise uniquement des fonctions standard (shutil)
# - Pas de dépendance vers domain/, application/, infrastructure/
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier (pas de règles de blacklist, politiques)
# ❌ Pas d'appels système complexes
# ❌ Pas de modification forcée de la taille du terminal
# ❌ Pas de couleurs hardcodées
# Points clés :
# - Constantes : OPTIMAL_WIDTH=120, OPTIMAL_HEIGHT=40, MIN_WIDTH=80, MIN_HEIGHT=24
# - get_terminal_width() / get_terminal_height() : détection avec fallback sécurisé
# - center_text() : centre un texte dans la largeur donnée
# - calculate_content_width() : largeur utile avec marges (4 colonnes)
# - calculate_margins() : marges gauche/droite pour centrage
# - calculate_inner_width() : FORMULE CLÉ pour éviter la dislocation
#   inner_width = panel_width - 4 (2 bordures │ + 2 padding)
# - calculate_panel_width() : largeur du panel centré (term_width - 4, min 40)
# - truncate_text() : tronque avec suffixe "..."
# - wrap_text() : découpe un texte en lignes
# Intégration prévue :
# - dashboard.py utilisera calculate_panel_width() et calculate_inner_width()
#   pour garantir que les séparateurs s'arrêtent exactement au bon endroit
# - dashboard.py utilisera center_text() pour le splash screen
# - tables.py utilisera calculate_content_width() pour adapter les tableaux
#
# check_terminal_size()/print_size_hint() supprimées (2026-08-16) : jamais
# appelées nulle part (seul app/bootstrap.py::check_terminal_size(), une
# fonction distincte et réellement utilisée, existe pour ce rôle) — c'était
# aussi la seule source de markup Rich codé en dur de ce fichier.
#---------------------------------------------------------------------->
