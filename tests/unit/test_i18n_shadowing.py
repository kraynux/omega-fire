# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Aucune fonction ne peut a la fois appeler `_()` et affecter `_` (retour utilisateur
2026-10-28 : `r, _, _ = select.select(...)` dans render_lnav_live faisait de `_` une variable
locale ; le `_("🛡  OMEGA-FIRE …")` ajoute par le marquage i18n levait TypeError, lnav ne
s'ouvrait plus en 8.6, 5.2 et 5.3)."""
from __future__ import annotations

import ast
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src" / "omega_fire"


def _shadowing_functions() -> list[str]:
    found: list[str] = []
    for path in sorted(SRC.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for function in ast.walk(tree):
            if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            stores = calls = False
            for node in ast.walk(function):
                if isinstance(node, ast.Name) and node.id == "_" and isinstance(node.ctx, ast.Store):
                    stores = True
                elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "_":
                    calls = True
            if stores and calls:
                found.append(f"{path.relative_to(SRC)}:{function.lineno} {function.name}")
    return found


class NoShadowedTranslatorTest(unittest.TestCase):
    def test_pas_de_variable_jetable_nommee_underscore(self) -> None:
        self.assertEqual(_shadowing_functions(), [])


if __name__ == "__main__":
    unittest.main()
