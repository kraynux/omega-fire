# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Theme registry.

Manages the loading, selection, and fallback of Omega-Fire themes.
Reads the OMEGA_THEME environment variable or CLI args to select
the active theme, with automatic fallback to 'omega-dark' or 'omega-mono'
based on terminal detection.
"""
import os
from typing import Optional, Type
from rich.console import Console
from rich.theme import Theme
from rich.style import Style
from rich.panel import Panel
from omega_fire.interfaces.cli.themes.base import Theme as ThemeBase
from omega_fire.interfaces.exceptions import RenderError


class ThemeRegistry:
    """Registry for Omega-Fire themes.
    
    Loads available themes and provides the active theme based on
    environment variables, CLI arguments, or terminal auto-detection.
    Handles compatibility checks and automatic fallback.
    """
    
    def __init__(self, console: Optional[Console] = None):
        """Initialize the theme registry.
        
        Args:
            console: Optional Rich console for notifications
        """
        self._themes: dict[str, Type[ThemeBase]] = {}
        self._active_theme: Optional[ThemeBase] = None
        self._console = console or Console()
        self._fallback_history: list[tuple[str, str, str]] = []
    
    def register(self, theme_class: Type[ThemeBase]) -> None:
        """Register a theme class.
        
        Args:
            theme_class: A class inheriting from ThemeBase
        """
        instance = theme_class()
        self._themes[instance.name] = theme_class
    
    def get_theme_names(self) -> list[str]:
        """Get a list of all registered theme names.
        
        Returns:
            List of theme names
        """
        return list(self._themes.keys())
    
    def set_active(self, theme_name: str, force: bool = False, silent: bool = False) -> str:
        """Set the active theme with compatibility check and case-insensitive matching.
        
        Args:
            theme_name: Name of the theme to activate (case-insensitive)
            force: If True, activate even if incompatible (with warning)
            silent: If True, suppress warning panels on fallback/force
        
        Returns:
            Actual theme name activated (may differ if fallback occurred)
        
        Raises:
            RenderError: If the theme is not registered
        """
        from omega_fire.interfaces.cli.themes.normalization import normalize_name, find_case_insensitive
        
        # Normalize the requested theme name
        normalized_name = normalize_name(theme_name)
        
        # Find the actual registered theme (case-insensitive)
        actual_name = find_case_insensitive(self.get_theme_names(), normalized_name)
        
        if actual_name is None:
            raise RenderError(
                component="ThemeRegistry",
                reason=f"Theme '{theme_name}' is not registered. Available: {self.get_theme_names()}"
            )
        
        theme_instance = self._themes[actual_name]()
        
        # Check compatibility
        from omega_fire.interfaces.cli.themes.terminal import TerminalDetector
        terminal_info = TerminalDetector().get_terminal_info()
        
        # Terminator et terminaux modernes 256/24-bit sont réputés compatibles
        is_modern_term = terminal_info.get("colors") in ("24-bit", "256") and terminal_info.get("supports_emojis", True)
        is_compatible = theme_instance.is_compatible(terminal_info) or is_modern_term

        if not is_compatible:
            if not force:
                # Auto-fallback
                fallback_name = theme_instance.get_fallback_theme()
                reason = f"Theme '{actual_name}' is incompatible with terminal"
                
                self._fallback_history.append((actual_name, fallback_name, reason))
                
                # Notify user only if not in silent mode
                if not silent:
                    self._console.print(
                        Panel(
                            f"[yellow]⚠️  Theme '{actual_name}' is incompatible with your terminal.[/yellow]\n"
                            f"[cyan]↳ Falling back to '{fallback_name}'[/cyan]\n"
                            f"[dim]Reason: {reason}[/dim]",
                            title="Theme Fallback",
                            border_style="yellow",
                        )
                    )
                
                actual_name = fallback_name
            else:
                # Forced but degraded
                reason = f"Theme '{actual_name}' forced on incompatible terminal"
                self._fallback_history.append((actual_name, actual_name, reason))
                
                if not silent:
                    self._console.print(
                        f"[yellow]⚠️  Warning: Theme '{actual_name}' may be degraded on your terminal.[/yellow]"
                    )
        
        self._active_theme = self._themes[actual_name]()
        return actual_name
    
    def get_active(self) -> ThemeBase:
        """Get the currently active theme.
        
        Returns:
            Active ThemeBase instance
        
        Raises:
            RenderError: If no theme is active
        """
        if self._active_theme is None:
            raise RenderError(
                component="ThemeRegistry",
                reason="No theme is currently active. Call set_active() first."
            )
        return self._active_theme
    
    def get_rich_theme(self) -> Theme:
        """Get the Rich Theme object for the active theme.
        
        Returns:
            Rich Theme object
        """
        return self.get_active().get_rich_theme()
    
    def get_style(self, style_name: str) -> Style:
        """Get a specific style from the active theme.
        
        Args:
            style_name: Name of the style (e.g., 'status.available')
        
        Returns:
            Rich Style object
        """
        return self.get_active().get_style(style_name)
    
    def prefers_emojis(self) -> bool:
        """Check whether the active theme's visual identity includes emoji.

        Design choice of the theme, not a terminal capability check — see
        Theme.prefers_emojis docstring (themes/base.py) for the distinction.

        Returns:
            True if the active theme is emoji-inclusive
        """
        return self.get_active().prefers_emojis
    
    def supports_live(self) -> bool:
        """Check if the active theme supports live rendering.
        
        Returns:
            True if live rendering is supported
        """
        return self.get_active().supports_live_rendering
    
    def get_fallback_history(self) -> list[tuple[str, str, str]]:
        """Get the history of theme fallbacks.
        
        Returns:
            List of (requested, actual, reason) tuples
        """
        return self._fallback_history.copy()
    
    def clear_fallback_history(self) -> None:
        """Clear the fallback history."""
        self._fallback_history.clear()


# Global registry instance
theme_registry = ThemeRegistry()


def get_active_theme() -> ThemeBase:
    """Convenience function to get the active theme.
    
    Returns:
        Active ThemeBase instance
    """
    return theme_registry.get_active()
