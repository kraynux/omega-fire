# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Terminal detection.

Automatically detects the terminal emulator and its capabilities
to suggest the most appropriate default theme.
Supports 13 known terminals + SSH modes + heuristics for unknown modern terminals.
"""
import os
import sys
from typing import Optional
from omega_fire.interfaces.cli.themes.normalization import normalize_name


class TerminalInfo:
    """Container for terminal capabilities."""

    def __init__(
        self,
        name: str,
        colors: str,
        supports_emojis: bool,
        supports_live: bool,
        recommended_args: list[str],
    ):
        self.name = name
        self.colors = colors
        self.supports_emojis = supports_emojis
        self.supports_live = supports_live
        self.recommended_args = recommended_args

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "colors": self.colors,
            "supports_emojis": self.supports_emojis,
            "supports_live": self.supports_live,
            "recommended_args": self.recommended_args,
        }


class TerminalDetector:
    """Detects terminal capabilities to suggest a default theme."""

    # Profiles based on official compatibility matrix
    TERMINAL_PROFILES = {
        normalize_name("Ghostty"): TerminalInfo("Ghostty", "24-bit", True, True, []),
        normalize_name("Alacritty"): TerminalInfo("Alacritty", "24-bit", True, True, []),
        normalize_name("WezTerm"): TerminalInfo("WezTerm", "24-bit", True, True, []),
        normalize_name("Kitty"): TerminalInfo("Kitty", "24-bit", True, True, []),
        normalize_name("Konsole"): TerminalInfo("Konsole", "256", True, True, []),
        normalize_name("GNOME Terminal"): TerminalInfo("GNOME Terminal", "256", True, True, []),
        normalize_name("Terminator"): TerminalInfo("Terminator", "256", True, True, []),
        normalize_name("xfce4-terminal"): TerminalInfo("xfce4-terminal", "256", True, True, []),
        normalize_name("urxvt"): TerminalInfo("urxvt", "256", False, True, ["--no-emoji"]),
        normalize_name("xterm"): TerminalInfo("xterm", "16", False, True, ["--no-emoji", "--no-color"]),
        normalize_name("Linux TTY"): TerminalInfo("Linux TTY", "16", False, False, ["--plain"]),
    }

    def __init__(self):
        """Initialize the detector."""
        self._term = normalize_name(os.environ.get("TERM", ""))
        self._term_program = normalize_name(os.environ.get("TERM_PROGRAM", ""))
        self._colorterm = normalize_name(os.environ.get("COLORTERM", ""))
        self._ssh = "SSH_CLIENT" in os.environ or "SSH_CONNECTION" in os.environ

    def detect(self) -> TerminalInfo:
        """Detect the terminal and return its capabilities.

        Detection priority:
        1. Known terminals via $TERM_PROGRAM
        2. Modern 24-bit override via $COLORTERM (e.g. Terminator)
        3. SSH sessions
        4. Known terminals via pattern in $TERM (specific first, then xterm)
        5. Multiplexers (screen, tmux)
        6. Heuristics for unknown modern terminals
        7. Ultimate fallback
        """
        # 1. Check for known modern terminals via $TERM_PROGRAM
        if self._term_program in self.TERMINAL_PROFILES:
            return self.TERMINAL_PROFILES[self._term_program]

        # 2. SSH detection (prioritized over generic TERM matching)
        if self._ssh:
            if self._colorterm in ("truecolor", "24bit") or "256" in self._term:
                return TerminalInfo("SSH moderne", "256", True, True, ["--no-emoji"])
            return TerminalInfo("SSH ancien", "partiel", False, False, ["--plain"])

        # 3. Specific terminals matching before generic xterm
        if "ghostty" in self._term:
            return self.TERMINAL_PROFILES[normalize_name("Ghostty")]
        if "terminator" in self._term:
            return self.TERMINAL_PROFILES[normalize_name("Terminator")]
        if "gnome" in self._term:
            return self.TERMINAL_PROFILES[normalize_name("GNOME Terminal")]
        if "kitty" in self._term:
            return self.TERMINAL_PROFILES[normalize_name("Kitty")]
        if "alacritty" in self._term:
            return self.TERMINAL_PROFILES[normalize_name("Alacritty")]
        if "wezterm" in self._term:
            return self.TERMINAL_PROFILES[normalize_name("WezTerm")]
        if "konsole" in self._term:
            return self.TERMINAL_PROFILES[normalize_name("Konsole")]
        if "xfce" in self._term:
            return self.TERMINAL_PROFILES[normalize_name("xfce4-terminal")]
        if "rxvt" in self._term or "urxvt" in self._term:
            return self.TERMINAL_PROFILES[normalize_name("urxvt")]
        if self._term == normalize_name("linux"):
            return self.TERMINAL_PROFILES[normalize_name("Linux TTY")]

        # 4. Handle COLORTERM truecolor overrides (e.g., Terminator exporting xterm-256color)
        if self._colorterm in ("truecolor", "24bit"):
            return TerminalInfo("Terminator / Modern 24-bit", "24-bit", True, True, [])

        # 5. Generic xterm fallback
        if "xterm" in self._term:
            return self.TERMINAL_PROFILES[normalize_name("xterm")]

        # 6. Multiplexers (screen, tmux)
        if "screen" in self._term or "tmux" in self._term:
            if "256" in self._term or self._colorterm:
                return TerminalInfo("Multiplexer (256-color)", "256", True, True, [])
            return TerminalInfo("Multiplexer", "256", True, True, [])

        # 7. Heuristics for unknown modern terminals
        if self._term.endswith("-256color"):
            return TerminalInfo("Unknown (256-color)", "256", True, True, [])

        if any(x in self._term for x in ("foot", "rio", "mlterm", "sakura")):
            return TerminalInfo("Unknown modern (24-bit)", "24-bit", True, True, [])

        if self._colorterm and self._colorterm not in ("", "none"):
            return TerminalInfo("Unknown (24-bit via COLORTERM)", "24-bit", True, True, [])

        if "256" in self._term:
            return TerminalInfo("Unknown (256)", "256", True, True, [])

        # 8. Ultimate fallback
        return TerminalInfo("Unknown (16)", "16", False, True, ["--no-emoji"])

    def detect_best_theme(self) -> str:
        """Detect the best default theme based on terminal capabilities."""
        terminal = self.detect()

        if terminal.colors in ("24-bit", "256") and terminal.supports_emojis:
            return "omega-base"
        if terminal.colors == "256":
            return "omega-dark"
        if terminal.colors in ("16", "partiel"):
            return "omega-mono"
        return "omega-minimal"

    def is_ssh(self) -> bool:
        """Check if running over SSH."""
        return self._ssh

    def get_terminal_info(self) -> dict:
        """Get detailed terminal information."""
        terminal = self.detect()
        info = terminal.to_dict()
        info["is_ssh"] = self._ssh
        info["suggested_theme"] = self.detect_best_theme()
        return info


def detect_terminal_theme() -> str:
    """Convenience function to detect the best default theme."""
    detector = TerminalDetector()
    return detector.detect_best_theme()


def get_terminal_info() -> dict:
    """Convenience function to get terminal info."""
    detector = TerminalDetector()
    return detector.get_terminal_info()
