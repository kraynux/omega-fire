# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Marquage i18n (OMEGA-FIRE_PLAN-DETAILLE_I18N.md, lot 4) : ce qui est relu par le code ne doit
jamais passer par _() - historique d'audit, faux stderr des adaptateurs, valeurs comparees dans
les modeles HTML - et aucune phrase n'est traduite avant l'installation de la langue."""
from __future__ import annotations

import ast
import re
import subprocess
import sys
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
SRC = PROJECT / "src" / "omega_fire"
DECISIONS = PROJECT.parent / "I18N_DECISIONS.md"


def _marked_calls(tree: ast.AST):
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "_":
            yield node


def _sources():
    for path in sorted(SRC.rglob("*.py")):
        if "__pycache__" not in path.parts:
            yield path, ast.parse(path.read_text(encoding="utf-8"))


class MarkingContractsTest(unittest.TestCase):
    def test_audit_titles_stay_source_text(self) -> None:
        # L'historique est relu (`e.action.strip() == _AUDIT_EXPORT_ACTION_TITLE`) : un titre
        # traduit ne correspondrait plus apres un changement de langue.
        for path, tree in _sources():
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign) and any(
                        isinstance(t, ast.Name) and t.id.endswith("ACTION_TITLE") for t in node.targets):
                    with self.subTest(fichier=path.name, ligne=node.lineno):
                        self.assertIsInstance(node.value, ast.Constant)
                if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "log_action_result":
                    with self.subTest(fichier=path.name, ligne=node.lineno):
                        self.assertFalse(list(_marked_calls(node)))

    def test_type_annotations_never_marked(self) -> None:
        for path, tree in _sources():
            for node in ast.walk(tree):
                annotations = []
                if isinstance(node, ast.arg) and node.annotation is not None:
                    annotations.append(node.annotation)
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.returns is not None:
                    annotations.append(node.returns)
                elif isinstance(node, ast.AnnAssign):
                    annotations.append(node.annotation)
                for annotation in annotations:
                    with self.subTest(fichier=path.name, ligne=annotation.lineno):
                        self.assertFalse(list(_marked_calls(annotation)))

    def test_adapter_stderr_never_marked(self) -> None:
        # fail2ban/adapter.py relit `"not found" in stderr` : le faux stderr reste en anglais.
        for path, tree in _sources():
            for node in ast.walk(tree):
                if isinstance(node, ast.keyword) and node.arg == "stderr":
                    with self.subTest(fichier=path.name, ligne=node.value.lineno):
                        self.assertFalse(list(_marked_calls(node.value)))

    def test_texts_compared_in_html_templates_never_marked(self) -> None:
        compared: set[str] = set()
        for template in SRC.rglob("*.j2"):
            for test in re.finditer(r"\{%-?\s*(?:el)?if\s+(.*?)-?%\}", template.read_text(encoding="utf-8"), re.S):
                compared.update(re.findall(r"""["']([^"']+)["']""", test.group(1)))
        rules_export = ast.parse((SRC / "interfaces/tui/screens/export_rules_screen.py").read_text(encoding="utf-8"))
        marked = {c.args[0].value for c in _marked_calls(rules_export)
                  if c.args and isinstance(c.args[0], ast.Constant)}
        self.assertFalse(compared & marked)

    def test_nothing_translated_before_language_is_installed(self) -> None:
        # Modules charges par bootstrap + early_language AVANT install_language_early() : une
        # phrase traduite au chargement y resterait en francais.
        code = ("import sys; import omega_fire.app.bootstrap, omega_fire.app.early_language; "
                "print('\\n'.join(m.__file__ for n, m in sys.modules.items() "
                "if n.startswith('omega_fire') and getattr(m, '__file__', None)))")
        files = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True,
                               cwd=PROJECT, env={"PYTHONPATH": str(PROJECT / "src")}).stdout.split()
        self.assertTrue(files)

        def import_time_calls(node: ast.AST):
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                    for default in child.args.defaults + [d for d in child.args.kw_defaults if d]:
                        yield from (c for c in _marked_calls(default))
                    continue
                if isinstance(child, ast.Call) and getattr(child.func, "id", None) == "_":
                    yield child
                yield from import_time_calls(child)

        for name in files:
            with self.subTest(module=Path(name).name):
                self.assertFalse(list(import_time_calls(ast.parse(Path(name).read_text(encoding="utf-8")))))


@unittest.skipUnless(DECISIONS.is_file(), "decisions de l'inventaire absentes (hors poste de developpement)")
class MarkingCompleteTest(unittest.TestCase):
    def test_every_text_to_translate_is_marked(self) -> None:
        result = subprocess.run([sys.executable, str(PROJECT / "tools" / "i18n_mark.py")],
                                capture_output=True, text=True, check=True, cwd=PROJECT)
        self.assertIn("0 textes marques dans 0 fichiers", result.stdout, result.stdout)


if __name__ == "__main__":
    unittest.main()
