#!/usr/bin/env python3
# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Catalogues de traduction (OMEGA-FIRE_PLAN-DETAILLE_I18N.md, lot 4 ; repris d'omega-serv)
- outil de developpement (tools/ n'est jamais livre).

  extract          code Python + modeles .j2 -> src/omega_fire/locale/omega-fire.pot
  init LANGUE      cree locale/LANGUE/LC_MESSAGES/omega-fire.po (ex. en, es, ru, zh_CN)
  update           extract puis msgmerge de chaque .po (traductions existantes conservees)
  compile          .po -> .mo (msgfmt --check : {variables} identiques source/traduction)
  status           phrases traduites / a traduire / approximatives par langue

Necessite GNU gettext (xgettext, msginit, msgmerge, msgfmt) - jamais a l'execution d'omega-fire,
seulement ici et dans build-release.sh.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
SRC = PROJECT / "src" / "omega_fire"
LOCALE = SRC / "locale"
DOMAIN = "omega-fire"
POT = LOCALE / f"{DOMAIN}.pot"
KEYWORDS = ("_", "N_", "P_", "ngettext:1,2")
_J2_CALL = re.compile(r'_\(\s*"((?:[^"\\]|\\.)*)"\s*\)')


def run(args: list[str]) -> subprocess.CompletedProcess:
    # cwd=PROJECT : references "#: src/omega_fire/..." relatives, jamais le chemin absolu de la
    # machine de developpement dans les catalogues livres.
    result = subprocess.run(args, capture_output=True, text=True, check=False, cwd=PROJECT)
    if result.returncode != 0:
        sys.exit(f"echec : {' '.join(args)}\n{result.stderr}")
    return result


def shown(path: Path) -> str:
    return str(path.relative_to(PROJECT)) if path.is_relative_to(PROJECT) else str(path)


def po_files() -> list[Path]:
    return sorted(LOCALE.glob(f"*/LC_MESSAGES/{DOMAIN}.po"))


def extract() -> None:
    LOCALE.mkdir(parents=True, exist_ok=True)
    py_files = sorted(str(p.relative_to(PROJECT)) for p in SRC.rglob("*.py") if "__pycache__" not in p.parts)
    with tempfile.TemporaryDirectory() as tmp:
        listing = Path(tmp) / "files.txt"
        listing.write_text("\n".join(py_files) + "\n", encoding="utf-8")
        py_pot = Path(tmp) / "py.pot"
        run(["xgettext", "--language=Python", "--from-code=UTF-8", *[f"--keyword={k}" for k in KEYWORDS],
             "--add-comments=Traducteurs", f"--package-name={DOMAIN}", "--no-wrap", "--sort-by-file",
             "-o", str(py_pot), "-f", str(listing)])
        # Modeles Jinja2 : {{ _("...") }} releves ici (xgettext ne lit pas Jinja) - marques au
        # lot « langue des exports » (Q3).
        j2_pot = Path(tmp) / "j2.pot"
        entries: dict[str, list[str]] = {}
        for template in sorted(SRC.rglob("*.j2")):
            for number, line in enumerate(template.read_text(encoding="utf-8").splitlines(), 1):
                for match in _J2_CALL.finditer(line):
                    entries.setdefault(match.group(1), []).append(f"{template.relative_to(PROJECT)}:{number}")
        lines = ['msgid ""', 'msgstr ""', '"Content-Type: text/plain; charset=UTF-8\\n"', ""]
        for msgid, refs in entries.items():
            lines += [f"#: {' '.join(refs)}"]
            if "{" in msgid:
                lines += ["#, python-brace-format"]
            lines += [f"msgid {json.dumps(msgid, ensure_ascii=False)}", 'msgstr ""', ""]
        j2_pot.write_text("\n".join(lines), encoding="utf-8")
        run(["msgcat", "--use-first", "--no-wrap", "-o", str(POT), str(py_pot), str(j2_pot)])
    count = sum(1 for line in POT.read_text(encoding="utf-8").splitlines() if line.startswith("msgid ")) - 1
    print(f"{shown(POT)} : {count} phrases")


PLURAL_FORMS = {
    "en": "nplurals=2; plural=(n != 1);",
    "es": "nplurals=2; plural=(n != 1);",
    "ru": "nplurals=3; plural=(n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2);",
    "zh_CN": "nplurals=1; plural=0;",
    "hi": "nplurals=2; plural=(n != 1);",
    "pt_BR": "nplurals=2; plural=(n > 1);",
    "de": "nplurals=2; plural=(n != 1);",
    "ja": "nplurals=1; plural=0;",
    "it": "nplurals=2; plural=(n != 1);",
    "pl": "nplurals=3; plural=(n==1 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2);",
    "vi": "nplurals=1; plural=0;",
    "th": "nplurals=1; plural=0;",
    "ko": "nplurals=1; plural=0;",
    "nl": "nplurals=2; plural=(n != 1);",
    "id": "nplurals=1; plural=0;",
    "ar": "nplurals=6; plural=(n==0 ? 0 : n==1 ? 1 : n==2 ? 2 : n%100>=3 && n%100<=10 ? 3 : n%100>=11 ? 4 : 5);",
}


def init(language: str) -> None:
    """Copie du modele avec l'en-tete de la langue - SANS msginit : pour l'anglais, msginit
    recopie chaque phrase source dans la traduction, le catalogue se declarerait alors
    entierement traduit... en francais."""
    target = LOCALE / language / "LC_MESSAGES" / f"{DOMAIN}.po"
    if target.exists():
        sys.exit(f"{target} existe deja - utiliser 'update'")
    if not POT.exists():
        extract()
    text = POT.read_text(encoding="utf-8")
    plural = PLURAL_FORMS.get(language, "nplurals=2; plural=(n != 1);")
    text = text.replace('"Language: \\n"', f'"Language: {language}\\n"', 1)
    text = re.sub(r'"Plural-Forms: [^"]*"\n', "", text)
    text = text.replace('"Content-Transfer-Encoding: 8bit\\n"',
                        f'"Content-Transfer-Encoding: 8bit\\n"\n"Plural-Forms: {plural}\\n"\n"X-Omega-Status: testing\\n"', 1)
    text = text.replace("#, fuzzy\nmsgid \"\"", "msgid \"\"", 1)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    print(f"cree : {shown(target)} (statut : en test)")


def update() -> None:
    extract()
    for po in po_files():
        run(["msgmerge", "--update", "--backup=none", "--no-wrap", str(po), str(POT)])
        print(f"mis a jour : {shown(po)}")


def compile_all() -> None:
    for po in po_files():
        mo = po.with_suffix(".mo")
        run(["msgfmt", "--check", "-o", str(mo), str(po)])
        print(f"compile : {shown(mo)}")


def status() -> None:
    if not po_files():
        print("aucune langue (seulement le francais, langue source)")
    for po in po_files():
        result = subprocess.run(["msgfmt", "--statistics", "-o", "/dev/null", str(po)],
                                capture_output=True, text=True, check=False)
        print(f"{po.parts[-3]:6} {result.stderr.strip()}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("extract")
    init_parser = sub.add_parser("init")
    init_parser.add_argument("language")
    sub.add_parser("update")
    sub.add_parser("compile")
    sub.add_parser("status")
    args = parser.parse_args(argv)
    {"extract": extract, "update": update, "compile": compile_all, "status": status}.get(
        args.command, lambda: init(args.language))()
    return 0


if __name__ == "__main__":
    sys.exit(main())
