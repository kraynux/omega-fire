#!/usr/bin/env python3
# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Remise des accents dans les textes francais affiches (OMEGA-FIRE_PLAN-DETAILLE_I18N.md, lot 3).

Repris d'omega-fire/tools/i18n_accents.py. Specifique omega-fire : seuls les textes TRADUIRE de
l'inventaire FINAL (garde-fou « valeur comparee ailleurs » compris) sont touches, jamais
l'ancienne interface --legacy-cli (Q1).

Outil de developpement (tools/ n'est jamais livre). Reutilisable pour les autres outils de la
suite (omega-fire, omega-suite) : meme inventaire, meme methode.

Ne touche QUE les textes classes TRADUIRE par l'inventaire (tools/i18n_inventory.py + decisions
de l'utilisateur) - jamais un identifiant, une cle, un chemin, une ligne de journal. Dans ces
textes, les morceaux techniques (options.waf.x, secure/waf, {variable}, --option...) sont
laisses tels quels.

Decision par mot (dictionnaire francais pyspellchecker + mots accentues de la doc du projet) :
  - mot sans accent inexistant en francais, une seule forme accentuee -> corrige (AUTO) ;
  - mot qui existe sans ET avec accent (a/a, ou/ou, supprime/supprime, cree/cree/cree) -> AMBIGU,
    jamais corrige automatiquement : decision par occurrence dans un fichier de decisions.
Une substitution d'accent garde le meme nombre de caracteres : le source est modifie en place,
aux positions exactes du texte (module tokenize), sans rien decaler.

Usage :
  tools/i18n_accents.py report  [--out FICHIER]   passage a blanc : bilan + ambiguites (rien modifie)
  tools/i18n_accents.py apply   --decisions FICHIER  applique AUTO + decisions d'ambiguites

Necessite pyspellchecker (environnement de developpement a part, jamais une dependance du projet) :
  python3 -m venv /tmp/accent-venv && /tmp/accent-venv/bin/pip install pyspellchecker
"""
from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import re
import sys
import tokenize
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT / "src" / "omega_fire"
DOC_CORPUS = (PROJECT / "README.md", *sorted((PROJECT / "docs").glob("*.md")))

_ESCAPE = re.compile(r"\\(?:x[0-9a-fA-F]{2}|u[0-9a-fA-F]{4}|U[0-9a-fA-F]{8}|N\{[^}]*\}|[0-7]{1,3}|.)", re.DOTALL)
_WORD = re.compile(r"[^\W\d_]+")
_TECH_CHARS = re.compile(r"[._/=#@<>\\{}|$%*+~`\[\]]")
_EDGE_PUNCT = " ,;:!?()«»\"'’…"
_CAMEL = re.compile(r"[a-z][A-Z]")

# Jamais accentues (revue du lot 3, 2026-10-21) : noms de modules et termes anglais/techniques
# que le dictionnaire prendrait pour des mots francais (Deception -> deception, email -> email,
# Referer = en-tete HTTP, o = une touche...).
NEVER_ACCENTED = {"deception", "defense", "referer", "medium", "scope", "select", "email", "o", "re", "reverse", "cable"}
NEVER_ACCENTED_UPPER = {"ca"}  # CA = autorite de certification ; "ca" minuscule -> "ca" (cedille)

# Mots-outils dont les deux formes existent : TOUJOURS ambigus, jamais tranches par la frequence.
ALWAYS_AMBIGUOUS = {"a", "ou", "la", "des", "du", "sur", "mur", "cote", "peche", "pres", "marche"}


def strip_accents(word: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", word) if unicodedata.category(c) != "Mn")


def has_accent(word: str) -> bool:
    return strip_accents(word) != word


def match_case(source: str, target: str) -> str:
    if source.isupper() and len(source) > 1:
        return target.upper()
    if source[:1].isupper():
        return target[:1].upper() + target[1:]
    return target


class Lexicon:
    def __init__(self) -> None:
        from spellchecker import SpellChecker  # outil de dev uniquement

        self.freq: Counter = Counter(dict(SpellChecker(language="fr").word_frequency.dictionary))
        for path in DOC_CORPUS:
            if path.is_file():
                for word in _WORD.findall(path.read_text(encoding="utf-8")):
                    if has_accent(word):
                        self.freq[word.lower()] += 50  # vocabulaire du projet : bonus
        self.by_base: dict[str, list[str]] = defaultdict(list)
        for word in self.freq:
            if has_accent(word):
                self.by_base[strip_accents(word)].append(word)

    def decide(self, word: str) -> tuple[str, list[str]]:
        """('keep'|'auto'|'ambiguous', candidats)."""
        lower = word.lower()
        if has_accent(lower) or len(lower) < 1 or lower in NEVER_ACCENTED:
            return "keep", []
        if lower in NEVER_ACCENTED_UPPER and word.isupper():
            return "keep", []
        candidates = sorted(self.by_base.get(lower, []), key=lambda w: -self.freq[w])
        if not candidates:
            return "keep", []
        own = self.freq.get(lower, 0)
        if lower in ALWAYS_AMBIGUOUS:
            return "ambiguous", candidates
        best = self.freq[candidates[0]]
        dominant = len(candidates) == 1 or best >= 20 * self.freq[candidates[1]]
        if own == 0:
            return ("auto", candidates[:1]) if dominant else ("ambiguous", candidates)
        if own >= 3 * best:
            return "keep", []  # forme sans accent nettement plus courante (de/de, les/les, liste/liste)
        if own * 50 < best and dominant:
            return "auto", candidates[:1]  # forme sans accent rarissime (gravite / gravite)
        return "ambiguous", candidates


@dataclass
class Occurrence:
    file: str
    line: int
    col: int
    word: str
    kind: str
    candidates: list[str]
    text: str
    line_text: str = ""

    @property
    def key(self) -> str:
        return f"{self.file}:{self.line}:{self.col}"


def _load_inventory():
    spec = importlib.util.spec_from_file_location("i18n_inventory", PROJECT / "tools" / "i18n_inventory.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["i18n_inventory"] = module
    spec.loader.exec_module(module)
    return module


def translatable_spans(inventory) -> dict[Path, list[tuple[tuple[int, int], tuple[int, int], str]]]:
    """Par fichier : (debut, fin) des noeuds texte classes TRADUIRE, avec leur texte."""
    rules = inventory.load_rule_decisions(PROJECT.parent / "I18N_DECISIONS.md")
    lines = inventory.load_line_decisions(PROJECT.parent / "i18n_inventaire.csv")
    spans: dict[Path, list] = defaultdict(list)
    # Inventaire final (avec le garde-fou post-scan d'omega-fire) : seule reference de ce qui
    # se traduit ; l'ancienne interface (--legacy-cli) n'y figure pas.
    entries, _skipped, _missing = inventory.scan()
    inventory.apply_decisions(entries, rules, lines)
    final = {(e.file, e.line, e.text) for e in entries if e.source == "omega-fire" and e.category == inventory.TRADUIRE}
    for path in sorted(SOURCE_ROOT.rglob("*.py")):
        if "__pycache__" in path.parts or inventory.is_legacy_cli(path.relative_to(SOURCE_ROOT).as_posix()):
            continue
        scanner = inventory.FileScanner("omega-fire", SOURCE_ROOT, path)
        for node in ast.walk(scanner.tree):
            if isinstance(node, ast.JoinedStr):
                if scanner._inside_fstring(node):
                    continue
                text = inventory.render_fstring(node)
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                if scanner._inside_fstring(node):
                    continue
                text = node.value
            else:
                continue
            if id(node) in scanner.docstrings or not inventory._LETTER.search(text):
                continue
            context, category, reason = scanner.classify(node, text)
            if (scanner.rel, node.lineno, text) in final:
                spans[path].append(((node.lineno, node.col_offset), (node.end_lineno, node.end_col_offset), text))
    return spans


def _displayed(node: ast.AST, field: ast.FormattedValue, parents: dict) -> bool:
    """Chaine affichee si, en remontant jusqu'au champ {..}, on ne traverse que des
    constructions de texte (concatenation, `or`, choix `x if c else y`, f-string imbriquee) ;
    argument d'appel, index, comparaison ou condition = cle/valeur technique."""
    child, current = node, parents.get(id(node))
    while current is not None and current is not field:
        if isinstance(current, (ast.Call, ast.Subscript, ast.Compare, ast.keyword, ast.Attribute)):
            return False
        if isinstance(current, ast.IfExp) and child is current.test:
            return False
        if not isinstance(current, (ast.BinOp, ast.BoolOp, ast.IfExp, ast.JoinedStr, ast.FormattedValue)):
            return False
        child, current = current, parents.get(id(current))
    return True


def nested_key_strings(path: Path) -> list[tuple[tuple[int, int], tuple[int, int]]]:
    """Chaines DANS une expression {..} de f-string qui ne sont PAS du texte affiche
    (entry.get('file'), d['reputation']...) : jamais touchees. Seules restent modifiables les
    valeurs d'affichage d'un choix `'active' if x else 'desactive'`."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    parents = {id(child): parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
    excluded = []
    for fstring in ast.walk(tree):
        if not isinstance(fstring, ast.JoinedStr):
            continue
        for value in fstring.values:
            if not isinstance(value, ast.FormattedValue):
                continue
            for node in ast.walk(value.value):
                if isinstance(node, ast.Constant) and isinstance(node.value, str) and not _displayed(node, value, parents):
                    excluded.append(((node.lineno, node.col_offset), (node.end_lineno, node.end_col_offset)))
    return excluded


def literal_pieces(path: Path, spans) -> list[tuple[int, int, int, str]]:
    """(ligne, col_debut, col_fin, texte source) des morceaux LITTERAUX (corps de chaine, partie
    texte d'une f-string) situes dans un noeud TRADUIRE. Jamais un commentaire, jamais {expr}."""
    pieces: list[tuple[int, int, int, str]] = []
    with path.open(encoding="utf-8") as handle:
        tokens = list(tokenize.generate_tokens(handle.readline))
    source_lines = path.read_text(encoding="utf-8").splitlines(keepends=True)

    excluded = nested_key_strings(path)

    def inside(pos: tuple[int, int]) -> bool:
        return any(start <= pos < end for start, end, _t in spans)

    for tok in tokens:
        if not inside(tok.start) or any(start <= tok.start < end for start, end in excluded):
            continue
        if tok.type == tokenize.STRING:
            match = re.match(r"^([rRbBuUfF]*)('''|\"\"\"|'|\")", tok.string)
            if not match or "r" in match.group(1).lower() or "b" in match.group(1).lower():
                continue
            quote_len = len(match.group(0))
            body_start = (tok.start[0], tok.start[1] + quote_len)
            body_end = (tok.end[0], tok.end[1] - len(match.group(2)))
            pieces.extend(_split_by_line(source_lines, body_start, body_end))
        elif tok.type == getattr(tokenize, "FSTRING_MIDDLE", -1):
            pieces.extend(_split_by_line(source_lines, tok.start, tok.end))
    return pieces


def _split_by_line(source_lines, start, end):
    result = []
    for line_no in range(start[0], end[0] + 1):
        line = source_lines[line_no - 1]
        begin = start[1] if line_no == start[0] else 0
        finish = end[1] if line_no == end[0] else len(line.rstrip("\n"))
        if finish > begin:
            result.append((line_no, begin, finish, line[begin:finish]))
    return result


_MARKUP = re.compile(r"<[a-zA-Z/!]|\b[a-z-]+=\\?[\"']")


def analyze_piece(text: str):
    """Mots candidats d'un morceau source : (offset, mot), morceaux techniques ignores.
    Un morceau de balisage HTML est ignore EN ENTIER (lot 4 : `class=\"container theme-orange\"`
    etait devenu `theme` -> `theme` accentue, classe CSS cassee - le guillemet echappe colle au
    mot le faisait passer pour du texte)."""
    if _MARKUP.search(text):
        return
    masked = _ESCAPE.sub(lambda m: " " * len(m.group(0)), text)
    for chunk in re.finditer(r"\S+", masked):
        raw = chunk.group(0)
        inner = raw.strip(_EDGE_PUNCT).rstrip(".").strip(_EDGE_PUNCT)  # point final / "..." = ponctuation
        if not inner or _TECH_CHARS.search(inner) or _CAMEL.search(inner) or re.search(r"\d", inner):
            continue
        if inner.startswith("-"):
            continue
        for word in _WORD.finditer(raw):
            yield chunk.start() + word.start(), word.group(0)


def collect(lexicon: Lexicon):
    inventory = _load_inventory()
    spans = translatable_spans(inventory)
    occurrences: list[Occurrence] = []
    for path, file_spans in spans.items():
        rel = path.relative_to(SOURCE_ROOT).as_posix()
        source_lines = path.read_text(encoding="utf-8").splitlines()
        for line_no, begin, _end, text in literal_pieces(path, file_spans):
            for offset, word in analyze_piece(text):
                kind, candidates = lexicon.decide(word)
                if kind == "keep":
                    continue
                context = next((t for s, e, t in file_spans if s <= (line_no, begin) < e), text)
                occurrences.append(Occurrence(rel, line_no, begin + offset, word, kind, candidates, context,
                                              source_lines[line_no - 1]))
    return occurrences


_NEXT_WORD = re.compile(r"[\s,]*([^\W\d_]+(?:'|’)?)")


def rule_decision(o: Occurrence) -> str | None:
    """Mots-outils tranches par une regle sure (la forme accentuee n'existe que dans des
    tournures precises), d'apres la ligne de code a la position exacte du mot."""
    lower = o.word.lower()
    before = o.line_text[:o.col].rstrip().lower()
    after_match = _NEXT_WORD.match(o.line_text, o.col + len(o.word))
    after = after_match.group(1).lower() if after_match else ""
    if lower == "des":
        return "dès" if after.rstrip("'’") in {"que", "qu", "lors", "maintenant", "reception", "demarrage",
                                               "chargement", "premier", "premiere", "1er"} else "des"
    if lower == "la":
        # "-la" : seulement apres un demonstratif (ceux-la) ; "corrigez-la" = pronom, sans accent
        demonstrative = o.line_text[o.col - 1:o.col] == "-" and before[:-1].endswith(("celle", "celui", "ceux", "celles"))
        return "là" if demonstrative or after in {"ou", "où"} else "la"
    if lower == "du":
        return "dû" if after in {"a", "à"} and before.endswith(("est", "etait", "était", "sont")) else "du"
    if lower == "sur":
        sure = before.endswith(("bien", "plus", "pas", "peu", "tres", "très", "etre", "être", "est")) \
            and after in {"", "que", "qu'", "de", "d'", "et", "pour", "car", "mais", "si"}
        return "sûr" if sure else "sur"
    return None


def _context(o: Occurrence, width: int = 55) -> str:
    line = o.line_text
    return (line[max(0, o.col - width):o.col] + "⟪" + o.word + "⟫" + line[o.col + len(o.word):o.col + len(o.word) + width]).strip()


def cmd_report(args) -> int:
    lexicon = Lexicon()
    occurrences = collect(lexicon)
    auto = [o for o in occurrences if o.kind == "auto"]
    ambiguous = [o for o in occurrences if o.kind == "ambiguous"]
    by_rule = {o.key: rule_decision(o) for o in ambiguous}
    auto_map = Counter((o.word.lower(), o.candidates[0]) for o in auto)
    amb_words = Counter(o.word.lower() for o in ambiguous)
    print(f"{len(occurrences)} mots a accentuer : AUTO {len(auto)} ({len(auto_map)} formes), "
          f"AMBIGU {len(ambiguous)} ({len(amb_words)} formes)")
    report = {
        "auto": [{"mot": w, "devient": c, "occurrences": n} for (w, c), n in auto_map.most_common()],
        "ambigu": [
            {"cle": o.key, "mot": o.word, "candidats": [o.word.lower(), *o.candidates], "texte": o.text,
             "contexte": _context(o), "decision": by_rule[o.key] or "", "par": "regle" if by_rule[o.key] else ""}
            for o in ambiguous
        ],
    }
    Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"   dont {sum(1 for v in by_rule.values() if v)} tranches par regle (des/la/du/sur), "
          f"{sum(1 for v in by_rule.values() if not v)} a trancher en contexte")
    print(f"-> {args.out}")
    print("Formes ambigues les plus frequentes :", ", ".join(f"{w}x{n}" for w, n in amb_words.most_common(40)))
    return 0


def cmd_apply(args) -> int:
    lexicon = Lexicon()
    decisions = json.loads(Path(args.decisions).read_text(encoding="utf-8"))
    resolved = {d["cle"]: d["decision"] for d in decisions.get("ambigu", []) if d.get("decision")}
    vetoed = {d["mot"] for d in decisions.get("auto", []) if d.get("refuse")}
    occurrences = collect(lexicon)
    edits: dict[str, dict[int, list[tuple[int, str, str]]]] = defaultdict(lambda: defaultdict(list))
    missing = 0
    for o in occurrences:
        if o.kind == "auto" and o.word.lower() not in vetoed:
            target = o.candidates[0]
        elif o.kind == "ambiguous":
            if o.key not in resolved:
                missing += 1
                continue
            target = resolved[o.key]
        else:
            continue
        if strip_accents(target) != o.word.lower() or len(target) != len(o.word):
            raise SystemExit(f"decision incoherente {o.key} : {o.word} -> {target}")
        edits[o.file][o.line].append((o.col, o.word, match_case(o.word, target)))
    changed_words = 0
    for rel, by_line in edits.items():
        path = SOURCE_ROOT / rel
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        for line_no, items in by_line.items():
            line = lines[line_no - 1]
            for col, old, new in items:
                if line[col:col + len(old)] != old:
                    raise SystemExit(f"{rel}:{line_no}:{col} : attendu {old!r}, trouve {line[col:col + len(old)]!r}")
                line = line[:col] + new + line[col + len(old):]
                changed_words += 1
            lines[line_no - 1] = line
        path.write_text("".join(lines), encoding="utf-8")
    print(f"{changed_words} mots accentues dans {len(edits)} fichiers ; {missing} ambiguite(s) sans decision laissee(s) telle(s) quelle(s)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    report = sub.add_parser("report")
    report.add_argument("--out", default=str(PROJECT.parent / "i18n_accents_rapport.json"))
    report.set_defaults(func=cmd_report)
    apply_parser = sub.add_parser("apply")
    apply_parser.add_argument("--decisions", required=True)
    apply_parser.set_defaults(func=cmd_apply)
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
