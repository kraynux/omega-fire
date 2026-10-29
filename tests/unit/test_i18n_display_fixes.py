# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Correctifs d'affichage hindi/arabe branches dans omega-fire (OMEGA-FIRE_PLAN-DETAILLE_I18N.md,
Q6 : modules partages dans omega-lib). Le mode bidi explicite du terminal ne s'active qu'en arabe ;
toute autre langue lance la TUI exactement comme avant."""
from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout

from omega_fire.app.bootstrap import _run_with_text_direction
from omega_lib.i18n.terminal_bidi import ENTER_EXPLICIT_MODE, LEAVE_EXPLICIT_MODE


class _FakeApp:
    def __init__(self) -> None:
        self.runs = 0

    def run(self) -> None:
        self.runs += 1


class TextDirectionTest(unittest.TestCase):
    def test_left_to_right_language_runs_without_terminal_codes(self) -> None:
        for code in ("fr", "en", "hi", "zh_CN"):
            app, out = _FakeApp(), io.StringIO()
            with redirect_stdout(out):
                _run_with_text_direction(app, code)
            self.assertEqual(app.runs, 1, code)
            self.assertEqual(out.getvalue(), "", code)

    def test_arabic_wraps_the_tui_in_explicit_bidi_mode(self) -> None:
        from textual._styles_cache import StylesCache

        from omega_lib.i18n import terminal_bidi

        self.addCleanup(setattr, StylesCache, "render_line", StylesCache.render_line)
        self.addCleanup(setattr, terminal_bidi, "_installed", terminal_bidi._installed)
        app, out = _FakeApp(), io.StringIO()
        with redirect_stdout(out):
            _run_with_text_direction(app, "ar")
        self.assertEqual(app.runs, 1)
        self.assertEqual(out.getvalue(), ENTER_EXPLICIT_MODE + LEAVE_EXPLICIT_MODE)


if __name__ == "__main__":
    unittest.main()
