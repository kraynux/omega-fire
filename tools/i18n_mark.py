#!/usr/bin/env python3
# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Marquage des textes a traduire (OMEGA-FIRE_PLAN-DETAILLE_I18N.md, lot 4 ; repris d'omega-serv).

Outil de developpement (tools/ n'est jamais livre). Ne marque QUE les textes classes TRADUIRE
par l'inventaire FINAL (tools/i18n_inventory.py apres garde-fous et decisions de l'utilisateur ;
cle = fichier + ligne + texte, pour que le garde-fou « texte affiche ET compare ailleurs »,
calcule sur tout le projet, soit respecte) :
  "Texte"                    -> _("Texte")
  f"Fichier {path} absent"   -> _("Fichier {path} absent").format(path=path)
Les variables d'une f-string deviennent des champs NOMMES (le traducteur peut deplacer les mots
autour) ; un choix affiche a l'interieur d'un champ ('active' if x else 'desactive') est marque
lui aussi.

Jamais marques (signales dans le rapport) : texte aussi COMPARE tel quel ailleurs dans le code
(le traduire casserait la comparaison), format a champ imbrique ({x:{width}}),
ancienne interface --legacy-cli (Q1, exclue par l'inventaire).
Ajoute `from omega_fire.shared.i18n import _` ; renomme en `_ignored` une variable jetable `_`
d'une fonction qui contient un texte marque (sinon `_` y deviendrait locale).

Usage : tools/i18n_mark.py [--apply] [--src DOSSIER]   (sans --apply : passage a blanc)
"""
from __future__ import annotations

import argparse
import ast
import importlib.util
import keyword
import sys
from collections import Counter, defaultdict
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
MARK = "_"
IMPORT_LINE = "from omega_fire.shared.i18n import _\n"


def _load_inventory():
    spec = importlib.util.spec_from_file_location("i18n_inventory", PROJECT / "tools" / "i18n_inventory.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["i18n_inventory"] = module
    spec.loader.exec_module(module)
    return module


def quote(text: str) -> str:
    out = text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\t", "\\t").replace("\r", "\\r")
    return f'"{out}"'


class Offsets:
    """ast donne des colonnes en OCTETS UTF-8 ; on travaille en caracteres."""

    def __init__(self, source: str) -> None:
        self.lines = source.splitlines(keepends=True)
        self.starts = [0]
        for line in self.lines:
            self.starts.append(self.starts[-1] + len(line))

    def index(self, lineno: int, byte_col: int) -> int:
        line = self.lines[lineno - 1]
        return self.starts[lineno - 1] + len(line.encode("utf-8")[:byte_col].decode("utf-8"))

    def span(self, node: ast.AST) -> tuple[int, int]:
        return self.index(node.lineno, node.col_offset), self.index(node.end_lineno, node.end_col_offset)


class FileMarker:
    def __init__(self, path: Path, rel: str, inventory, targets: set[tuple[int, str]], compared: set[str],
                 report: list[str], src_root: Path) -> None:
        self.path, self.rel, self.inv, self.report = path, rel, inventory, report
        self.source = path.read_text(encoding="utf-8")
        self.offsets = Offsets(self.source)
        self.scanner = inventory.FileScanner("omega-fire", src_root, path)
        self.tree = self.scanner.tree
        self.parents = self.scanner.parents
        self.targets, self.compared = targets, compared
        self.edits: list[tuple[int, int, str]] = []
        self.marked_scopes: set[int] = set()

    # -- classement -----------------------------------------------------------------------
    def already_marked(self, node: ast.AST) -> bool:
        parent = self.parents.get(id(node))
        return isinstance(parent, ast.Call) and isinstance(parent.func, ast.Name) and parent.func.id in ("_", "N_", "ngettext")

    def scope_of(self, node: ast.AST) -> int:
        current = self.parents.get(id(node))
        while current is not None:
            if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                return id(current)
            current = self.parents.get(id(current))
        return id(self.tree)

    # -- reecriture -----------------------------------------------------------------------
    def segment(self, node: ast.AST) -> str:
        start, end = self.offsets.span(node)
        return self.source[start:end]

    def displayed_nested(self, field: ast.FormattedValue) -> list[ast.Constant]:
        found = []
        for node in ast.walk(field.value):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.strip() \
                    and self.inv._LETTER.search(node.value) and self._displayed(node, field):
                found.append(node)
        return found

    def _displayed(self, node: ast.AST, field: ast.FormattedValue) -> bool:
        child, current = node, self.parents.get(id(node))
        while current is not None and current is not field:
            if isinstance(current, (ast.Call, ast.Subscript, ast.Compare, ast.keyword, ast.Attribute)):
                return False
            if isinstance(current, ast.IfExp) and child is current.test:
                return False
            if not isinstance(current, (ast.BinOp, ast.BoolOp, ast.IfExp, ast.JoinedStr, ast.FormattedValue)):
                return False
            child, current = current, self.parents.get(id(current))
        return True

    def expression_source(self, field: ast.FormattedValue) -> str:
        expr = field.value
        start, end = self.offsets.span(expr)
        text = self.source[start:end]
        for const in sorted(self.displayed_nested(field), key=lambda c: -self.offsets.span(c)[0]):
            cs, ce = self.offsets.span(const)
            text = text[: cs - start] + f"{MARK}(" + text[cs - start: ce - start] + ")" + text[ce - start:]
        return text

    @staticmethod
    def placeholder_for(expr: ast.AST) -> str:
        if isinstance(expr, ast.Name):
            name = expr.id.lstrip("_") or "value"
        elif isinstance(expr, ast.Attribute):
            name = expr.attr.lstrip("_") or "value"
        elif isinstance(expr, ast.Subscript) and isinstance(expr.slice, ast.Constant) and isinstance(expr.slice.value, str) \
                and expr.slice.value.isidentifier():
            name = expr.slice.value
        elif isinstance(expr, ast.Call) and isinstance(expr.func, ast.Name) and expr.func.id == "len":
            name = "count"
        else:
            name = "value"
        if keyword.iskeyword(name) or not name.isidentifier():
            name = f"{name}_"
        return name

    def fstring_replacement(self, node: ast.JoinedStr) -> str | None:
        parts: list[str] = []
        args: dict[str, str] = {}
        by_source: dict[str, str] = {}
        for value in node.values:
            if isinstance(value, ast.Constant):
                parts.append(str(value.value).replace("{", "{{").replace("}", "}}"))
                continue
            assert isinstance(value, ast.FormattedValue)
            spec = ""
            if value.format_spec is not None:
                if any(isinstance(v, ast.FormattedValue) for v in value.format_spec.values):
                    return None
                spec = ":" + "".join(str(v.value) for v in value.format_spec.values)
            conversion = {-1: "", 115: "!s", 114: "!r", 97: "!a"}[value.conversion]
            expr_src = self.expression_source(value)
            if expr_src in by_source:
                name = by_source[expr_src]
            else:
                base = self.placeholder_for(value.value)
                name, n = base, 2
                while name in args:
                    name, n = f"{base}{n}", n + 1
                args[name] = expr_src
                by_source[expr_src] = name
            parts.append("{" + name + conversion + spec + "}")
        literal = quote("".join(parts))
        if not args:
            return f"{MARK}({literal})"
        return f"{MARK}({literal}).format(" + ", ".join(f"{k}={v}" for k, v in args.items()) + ")"

    def collect(self) -> None:
        for node in ast.walk(self.tree):
            if isinstance(node, ast.JoinedStr):
                if self.scanner._inside_fstring(node):
                    continue
                text = self.inv.render_fstring(node)
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                if self.scanner._inside_fstring(node):
                    continue
                text = node.value
            else:
                continue
            if id(node) in self.scanner.docstrings or not self.inv._LETTER.search(text) or self.already_marked(node):
                continue
            if (node.lineno, text) not in self.targets:
                continue
            if text in self.compared:
                self.report.append(f"SAUTE (texte compare ailleurs) {self.rel}:{node.lineno} {text[:60]!r}")
                continue
            if isinstance(node, ast.JoinedStr):
                replacement = self.fstring_replacement(node)
                if replacement is None:
                    self.report.append(f"SAUTE (format imbrique) {self.rel}:{node.lineno}")
                    continue
            else:
                replacement = f"{MARK}({self.segment(node)})"
            start, end = self.offsets.span(node)
            self.edits.append((start, end, replacement))
            self.marked_scopes.add(self.scope_of(node))

    def rename_throwaway(self) -> None:
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Name) and node.id == MARK and isinstance(node.ctx, ast.Store) \
                    and self.scope_of(node) in self.marked_scopes:
                start, end = self.offsets.span(node)
                self.edits.append((start, end, "_ignored"))
            elif isinstance(node, ast.Name) and node.id == MARK and isinstance(node.ctx, ast.Load) \
                    and self.scope_of(node) in self.marked_scopes:
                parent = self.parents.get(id(node))
                if not (isinstance(parent, ast.Call) and parent.func is node):
                    self.report.append(f"ATTENTION `_` lu comme variable {self.rel}:{node.lineno} - a verifier")

    def result(self) -> str | None:
        if not self.edits:
            return None
        text = self.source
        for start, end, replacement in sorted(self.edits, key=lambda e: -e[0]):
            text = text[:start] + replacement + text[end:]
        if not any(line.strip() == IMPORT_LINE.strip() for line in text.splitlines()):
            text = self.insert_import(text)
        return text

    @staticmethod
    def insert_import(text: str) -> str:
        tree = ast.parse(text)
        last = 0
        for stmt in tree.body:
            if isinstance(stmt, (ast.Import, ast.ImportFrom)):
                last = stmt.end_lineno
            elif isinstance(stmt, ast.Expr) and isinstance(getattr(stmt, "value", None), ast.Constant) and last == 0:
                last = stmt.end_lineno  # docstring du module
            elif last:
                break
        lines = text.splitlines(keepends=True)
        lines.insert(last, IMPORT_LINE)
        return "".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--src", type=Path, default=PROJECT / "src" / "omega_fire")
    args = parser.parse_args(argv)
    inventory = _load_inventory()
    rules = inventory.load_rule_decisions(PROJECT.parent / "I18N_DECISIONS.md")
    lines = inventory.load_line_decisions(PROJECT.parent / "i18n_inventaire.csv")
    entries, _skipped, _missing = inventory.scan()
    inventory.apply_decisions(entries, rules, lines)
    compared = {e.text for e in entries if e.reason in {"valeur comparee", "cle de dictionnaire", "index / cle d'acces"}}
    targets: dict[str, set[tuple[int, str]]] = defaultdict(set)
    for e in entries:
        if e.source == "omega-fire" and e.category == inventory.TRADUIRE \
                and not e.reason.startswith("marque pour traduction"):
            targets[e.file].add((e.line, e.text))
    report: list[str] = []
    stats: Counter = Counter()
    by_zone: dict[str, int] = defaultdict(int)
    for path in sorted(args.src.rglob("*.py")):
        if "__pycache__" in path.parts or path.name == "i18n.py" and path.parent.name == "shared":
            continue
        rel = path.relative_to(args.src).as_posix()
        if not targets.get(rel):
            continue
        marker = FileMarker(path, rel, inventory, targets[rel], compared, report, args.src)
        marker.collect()
        marker.rename_throwaway()
        new_text = marker.result()
        if new_text is None:
            continue
        stats["fichiers"] += 1
        stats["textes"] += sum(1 for e in marker.edits if e[2] != "_ignored")
        stats["renommages"] += sum(1 for e in marker.edits if e[2] == "_ignored")
        by_zone[marker.scanner.zone] += sum(1 for e in marker.edits if e[2] != "_ignored")
        try:
            compile(new_text, str(path), "exec")
        except SyntaxError as e:
            report.append(f"ERREUR DE SYNTAXE apres marquage {rel}:{e.lineno} {e.msg} - fichier NON modifie")
            continue
        if args.apply:
            path.write_text(new_text, encoding="utf-8")
    print(f"{'APPLIQUE' if args.apply else 'PASSAGE A BLANC'} : {stats['textes']} textes marques dans "
          f"{stats['fichiers']} fichiers, {stats['renommages']} variables `_` renommees")
    print("par zone :", dict(by_zone))
    for line in report:
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
