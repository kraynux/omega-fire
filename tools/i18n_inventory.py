#!/usr/bin/env python3
# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Inventaire des textes de l'interface (OMEGA-FIRE_PLAN-DETAILLE_I18N.md §4, lot 1).

Repris de omega-serv/tools/i18n_inventory.py (meme methode, memes categories), adapte a
omega-fire : contrats machine du pare-feu, ancienne interface --legacy-cli exclue (Q1).

Outil de developpement, jamais livre dans l'archive (build-release.sh exclut tools/).
LECTURE SEULE sur le code : analyse syntaxique (ast), aucun module du projet importe,
aucun fichier source modifie.

Releve chaque chaine et f-string de src/omega_fire/ et d'omega-lib, avec son contexte
d'appel, et la pre-classe :
  TRADUIRE           texte destine a l'utilisateur (contexte reconnu sans ambiguite)
  TRADUIRE-PROBABLE  texte qui a l'air humain dans un ecran, contexte non reconnu
  NE-PAS-TRADUIRE    identifiant, cle, valeur, chemin, motif, CSS, journal, contrat machine
  A-DECIDER          tout le reste (messages du domaine, stderr, exceptions...)

Decisions de l'utilisateur, jamais ecrasees par une regeneration :
  - par REGLE : I18N_DECISIONS.md (colonne "Decision" : TRADUIRE / NE-PAS-TRADUIRE / vide),
    relu a chaque passage et completee avec les nouvelles regles ;
  - par LIGNE : colonnes decision_utilisateur / note du CSV, reprises par identifiant.
Priorite : ligne > regle > pre-classement automatique.

Usage : tools/i18n_inventory.py [--csv FICHIER] [--md FICHIER] [--decisions FICHIER]
"""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
SOURCES = (
    ("omega-fire", PROJECT / "src" / "omega_fire"),
    ("omega-lib", Path(os.environ.get("OMEGA_LIB_SRC", Path.home() / "DEV/LIB/omega-lib/src/omega_lib"))),
)

TRADUIRE = "TRADUIRE"
PROBABLE = "TRADUIRE-PROBABLE"
NE_PAS = "NE-PAS-TRADUIRE"
A_DECIDER = "A-DECIDER"
CATEGORIES = (TRADUIRE, PROBABLE, NE_PAS, A_DECIDER)

# §4.3 : formats lus par une machine (nft, fail2ban, l'application elle-meme) - jamais traduits.
MACHINE_CONTRACTS = (
    ("Allow ", "commentaire de regle de pare-feu (politiques par defaut), ecrit dans nft/iptables"),
    ("Drop all", "commentaire de regle de pare-feu (politiques par defaut), ecrit dans nft/iptables"),
    ("Currently banned", "sortie de fail2ban-client analysee"),
    ("Banned IP list", "sortie de fail2ban-client analysee"),
    ("Jail list", "sortie de fail2ban-client analysee"),
    ("failregex", "filtre fail2ban"),
    ("Version mismatch", "erreur relue par plan_restore (`\"Version mismatch\" in err`)"),
)

# Q1 (plan omega-fire, ACTE 2026-10-27) : l'ancienne interface Rich (--legacy-cli) reste en
# francais. Seuls les modules de interfaces/cli/ importes par la TUI sont inventories.
_CLI_PREFIX = "omega_fire.interfaces.cli"


def _cli_imports(path: Path) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith(_CLI_PREFIX):
            found.add(node.module)
            found.update(f"{node.module}.{alias.name}" for alias in node.names)
        elif isinstance(node, ast.Import):
            found.update(a.name for a in node.names if a.name.startswith(_CLI_PREFIX))
    return found


def _module_file(root: Path, module: str) -> Path | None:
    base = root.parent.joinpath(*module.split("."))
    if base.with_suffix(".py").is_file():
        return base.with_suffix(".py")
    if (base / "__init__.py").is_file():
        return base / "__init__.py"
    return None


def tui_used_cli_files(root: Path) -> set[str]:
    """Fichiers de interfaces/cli/ atteints (imports transitifs) depuis tout le code hors
    interfaces/cli/ et hors app/bootstrap.py (qui lance l'ancienne interface) : c'est ce que la
    TUI affiche reellement. Recalcule a chaque passage : un nouvel import entre automatiquement."""
    todo = [p for p in root.rglob("*.py") if "__pycache__" not in p.parts
            and not p.relative_to(root).as_posix().startswith("interfaces/cli/")
            and p.relative_to(root).as_posix() != "app/bootstrap.py"]
    seen: set[Path] = set()
    while todo:
        for module in _cli_imports(todo.pop()):
            target = _module_file(root, module)
            if target is not None and target not in seen:
                seen.add(target)
                todo.append(target)
    return {p.relative_to(root).as_posix() for p in seen}


_LOGO_TARGET = re.compile(r"LOGO")
# Identifiant technique : minuscules / chiffres relies par - ou _ (avec champ {x} possible),
# ex. `_widget_id()` -> "action-{x}" (le traduire changerait l'id du bouton).
_TECH_IDENTIFIER = re.compile(r"^[a-z0-9{}]+(?:[-_][a-z0-9{}]+)+$")
PRODUCT_NAME_TARGETS = {"APP_NAME"}
LOG_LEVEL_NAMES = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
# Ligne "cle = valeur" d'un fichier de configuration (jail fail2ban : `port = {port}\n`).
_CONFIG_LINE = re.compile(r"^[a-z_]+ = \{[^}]*\}\n?$")
# Titres d'action ecrits dans l'historique d'audit (log_action_result) : l'historique est relu
# (`e.action.strip() == _AUDIT_EXPORT_ACTION_TITLE`) - toujours le texte source, quelle que soit
# la langue. Les libelles de menu (SectionItem) passent par N_() et sont traduits a l'affichage.
AUDIT_TITLE_TARGETS = {"_ACTION_TITLE", "_AUDIT_EXPORT_ACTION_TITLE"}
# Champs de donnees (pas des libelles) : live_tail_screen.py remplit "user_agent" avec une valeur
# par defaut puis le teste (`"bot" in user_agent`) - jamais traduit.
# Meme regle pour les valeurs des exports JSON ("source", "type"), l'etat d'une regle passe au
# modele HTML ("state", compare dans ruleset.html.j2) et la raison ecrite dans les metadonnees
# d'une sauvegarde ("reason", donnee enregistree).
DATA_FIELD_KEYS = {"user_agent", "source", "type", "state", "reason"}
DATA_SEED_TARGETS = frozenset({"DEFAULT_JAIL_PRESETS"})
"""Lot 4 a trancher : modeles de jail par defaut, recopies dans var/runtime/jail_presets.json
puis modifiables par l'utilisateur - donnees, pas texte d'interface."""

COMMAND_BINARIES = frozenset({
    "nft", "iptables", "ip6tables", "iptables-save", "ip6tables-save", "iptables-restore",
    "ip6tables-restore", "fail2ban-client", "fail2ban-regex", "systemctl", "rc-service", "rc-update",
    "sv", "conntrack", "sudo", "lnav", "journalctl", "ss", "ip", "modprobe", "lsmod",
})
COMMAND_VARIABLES = frozenset({"cmd", "command", "args", "argv", "cmd_args", "base_cmd", "full_cmd"})

_TUI_USED: set[str] = set()


def is_legacy_cli(rel: str) -> bool:
    return rel.startswith("interfaces/cli/") and rel not in _TUI_USED


LEGACY_CLI_SCOPES = {"app/bootstrap.py": ("bootstrap", "check_terminal_size")}


UI_TEXT_CALLS = {
    "Button", "Static", "Label", "Checkbox", "RadioButton", "Switch", "Collapsible",
    "TabPane", "Tab", "Option", "Header", "Markdown", "Link", "ListItem", "notify",
    "add_column", "add_columns", "Tooltip", "update", "set_status", "ConfirmScreen",
}
PROTOCOL_TARGETS = {"_REASON_PHRASES", "REASON_PHRASES"}
SEARCH_TARGETS = {"needle", "marker", "pattern", "prefix", "suffix", "separator", "sep", "token"}
"""Lot 4 : `needle = f"options.{x} ("` puis `if needle in message` - un fragment CHERCHE dans un
autre texte ne se traduit jamais (traduits separement, les deux ne correspondraient plus)."""
MARK_CALLS = {"_", "N_", "ngettext", "P_"}
"""Lot 4 : texte deja passe par la traduction (core/i18n.py)."""
GUIDE_CALLS = {"HelpEntry"}
GUIDE_MACHINE_KW = {"screen_class_name", "screen_class", "target", "screen"}
UI_TEXT_KW = {
    "placeholder", "tooltip", "title", "label", "prompt", "description", "help",
    "epilog", "border_title", "border_subtitle", "message", "subtitle", "sub_title",
    "question", "answer",
}
UI_TEXT_ATTRS = {"border_title", "border_subtitle", "label", "tooltip", "title",
                 "sub_title", "placeholder", "TITLE", "SUB_TITLE"}
MACHINE_KW = {
    "id", "classes", "name", "variant", "key", "mode", "encoding", "errors", "newline",
    "severity", "group", "dest", "metavar", "choices", "type", "default", "format",
    "sep", "end", "suffix", "prefix", "key_display", "action", "value", "markup",
    "language", "theme", "split", "layout", "dock", "align", "content_type", "cwd",
    "env", "user", "shell", "executable", "argv", "path", "file", "scope", "pattern",
    "anchor", "match", "kind", "source", "status", "field", "column", "sort_key", "style",
    "comment", "jail", "table", "chain", "set_name", "family", "action_name",
}
MACHINE_CALLS = {
    "query_one", "query", "get", "set", "pop", "setdefault", "startswith", "endswith",
    "split", "rsplit", "partition", "rpartition", "join", "replace", "strip", "lstrip",
    "rstrip", "removeprefix", "removesuffix", "compile", "match", "search", "fullmatch",
    "sub", "subn", "findall", "finditer", "escape", "Path", "PurePath", "open",
    "getenv", "putenv", "getattr", "hasattr", "setattr", "delattr", "add_class",
    "remove_class", "has_class", "set_class", "toggle_class", "run_action", "add_parser",
    "set_defaults", "strftime", "strptime", "fromisoformat", "encode", "decode",
    "isinstance", "fnmatch", "glob", "rglob", "with_suffix", "with_name", "joinpath",
    "mkdir", "exists", "which", "run", "Popen", "check_output", "check_call", "call",
    "int", "float", "bool", "bytes", "bytearray", "datetime", "timedelta", "pack",
    "unpack", "new", "sha256", "md5", "lower", "upper", "count", "index", "find", "rfind",
    "ip_network", "ip_address", "ip_interface", "urlsplit", "urlparse", "quote",
    "unquote", "dumps", "loads", "load", "dump", "getLogger", "header", "headers",
    "get_header", "add_header", "set_header", "with_header", "remove_header",
    "has_header", "HttpHeaders", "from_pairs", "LuaRuntime", "execute", "executemany", "eval",
    "eval_lua", "globals", "require", "lookup", "getpwnam", "getgrnam", "chmod",
    "chown", "environ", "update_settings", "setting", "option", "options", "Binding",
    "cast", "TypeVar", "NewType", "import_module",
}
LOG_CALLS = {"append_line", "write_line", "log_event", "log_ban", "log_unban", "log_rule_change",
             "log_sync", "log_export", "log_backup", "log_restore", "log_action",
             "log_line", "debug", "info", "warning", "error", "critical", "exception"}
CSS_TARGETS = {"DEFAULT_CSS", "CSS"}

_IDENTIFIER = re.compile(r"^[a-z0-9_\-./:#*%@+=?&,;!~|^$\\\[\]{}()<>'\"]*$")
_CONSTANT = re.compile(r"^[A-Z0-9_\-./:#*%@+=]+$")
_REGEX_HINT = re.compile(r"(\\[dswbAZSWDnrt.]|\(\?[:=!<P]|^\^|\$$|\[\^?[a-z0-9]\-[a-z0-9]\])")
_DRAWING = re.compile(r"[█▓▒░▀▄▌▐■□▪▫◆◇○●╔╗╚╝║═╠╣╦╩╬┌┐└┘│─├┤┬┴┼]")
_LETTER = re.compile(r"[^\W\d_]")
_WORD = re.compile(r"[^\W\d_]{3,}")
_CAMEL = re.compile(r"^_?[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]*)+$")
# Lot 3 (2026-10-21) : un schema SQL classe "texte humain" a vu sa colonne `detail` accentuee
# -> base Active Defense cassee. SQL et valeurs d'en-tete HTTP ne sont JAMAIS du texte affiche.
_SQL = re.compile(r"\b(CREATE\s+(TABLE|INDEX)|SELECT\s.+\sFROM|INSERT\s+INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM|PRAGMA\s)", re.IGNORECASE | re.DOTALL)
HEADER_VALUE_TARGETS = ("CACHE_CONTROL",)
_ANY_TAG = re.compile(r"<!?/?[a-zA-Z][a-zA-Z0-9-]*(?:\s[^<>]*)?/?>")
_HTML = re.compile(r"<!DOCTYPE|<html|</[a-z]+>|<(?:div|p|span|table|h[1-6]|body|head)\b", re.IGNORECASE)
_SQL_FRAGMENT = re.compile(r"^\s*(AND|OR|WHERE|ORDER\s+BY|GROUP\s+BY|LIMIT|OFFSET|JOIN|LEFT\s+JOIN|VALUES|SET)\b")
_MARKER_TARGET = re.compile(r"(MARKERS?|PATTERNS?|INDICATORS?|NEEDLES?|KEYWORDS?)$")
_DEBUG_REPR = re.compile(r"^[A-Z]\w*\(")
_RICH_STYLE = re.compile(r"^(?:(?:not\s+)?(?:bold|dim|italic|reverse|underline|blink|strike|on|default|"
                         r"(?:bright_)?(?:black|red|green|yellow|blue|magenta|cyan|white)|grey\d*|gray\d*|"
                         r"#[0-9a-fA-F]{3,6}|color\(\d+\)|rgb\([\d, ]+\))\s*)+$")
_ACCENT = re.compile(r"[àâäçéèêëîïôöûùüÿœæ]", re.IGNORECASE)
# Mots francais isoles reellement affiches tels quels (releves au 1er passage) : sans eux,
# la regle "identifiant minuscule sans espace" les classerait a tort en NE-PAS-TRADUIRE.
FRENCH_WORDS = {
    "oui", "non", "actif", "actifs", "active", "inactif", "inactive", "permanent", "permanente",
    "expire", "expiree", "expirees", "toutes", "tous", "tout", "aucun", "aucune", "arrete",
    "arretee", "enregistre", "erreur", "erreurs", "avertissement", "illimite", "illimitee",
    "inconnu", "inconnue", "desactive", "desactivee", "disponible", "indisponible", "degrade",
    "manquant", "manquante", "disqualifie", "absent", "absente", "valide", "invalide",
    "refuse", "refusee", "accepte", "bloque", "bloquee", "autorise", "termine", "ouvert",
    "ouverte", "ferme", "fermee", "jamais", "vide", "defaut", "succes", "echec", "chargee",
    "charge", "masque", "visible", "modifie", "inchange", "present", "presente", "requis",
    "facultatif", "secondes", "minutes", "heures", "jours", "octets", "entrees", "regles",
}
# Q7/D18 : journaux (app.log, audit.log relus par l'application) et journalctl
# reste en francais, quelle que soit la langue de l'interface.
SERVER_PROCESS_SCOPES: tuple[str, ...] = ()  # omega-fire n'a pas de processus serveur
SERVER_PROCESS_FILES: tuple[str, ...] = ("infrastructure/logging/app_logger.py", "infrastructure/logging/audit_logger.py")
BUILD_TOOL_FILES: tuple[str, ...] = ()
# Formats d'echange normalises (STIX 2.1, MISP) : contenu en anglais et en valeurs du standard,
# jamais traduit (aucun dans omega-fire pour l'instant).
EXCHANGE_FORMAT_FILES: tuple[str, ...] = ()
# Plan i18n §5.3 : libelle bilingue du selecteur et noms de langues (chacune dans SA langue),
# jamais traduits - c'est ce qui permet de revenir au francais depuis n'importe quelle langue.
NEVER_TRANSLATED_TEXTS = frozenset({
    "Langue / Language", "{LANGUAGE_LABEL} : {self._native_name}", "Français", "English", "Español",
    "Русский", "简体中文", "हिन्दी", "العربية", "Português (Brasil)", "Italiano", "Deutsch",
    "Nederlands", "Polski", "Tiếng Việt", "ไทย", "Bahasa Indonesia", "日本語", "한국어",
    "Test ⟦…⟧ (développement)",
})
SEVERITY_WORDS = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"}


@dataclass
class Entry:
    source: str
    zone: str
    file: str
    line: int
    scope: str
    context: str
    category: str
    reason: str
    text: str
    auto: str = ""
    rule_decision: str = ""
    line_decision: str = ""
    note: str = ""

    @property
    def ident(self) -> str:
        return hashlib.sha1(f"{self.file}\0{self.text}".encode()).hexdigest()[:10]


def zone_of(source: str, rel: str) -> str:
    if source == "omega-lib":
        return "omega-lib"
    for prefix, zone in (
        ("interfaces/cli/help_text.py", "guide"),
        ("interfaces/tui/screens/", "ecrans"),
        ("interfaces/tui/widgets/", "widgets"),
        ("interfaces/tui/", "tui-autre"),
        ("interfaces/cli/", "cli-tui"),
        ("application/", "application"),
        ("domain/", "domaine"),
        ("infrastructure/", "infrastructure"),
    ):
        if rel.startswith(prefix):
            return zone
    return "socle"


def call_name(call: ast.Call) -> str:
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def is_stderr_print(call: ast.Call) -> bool:
    if call_name(call) != "print":
        return False
    return any(kw.arg == "file" and "stderr" in ast.unparse(kw.value) for kw in call.keywords)


def render_fstring(node: ast.JoinedStr) -> str:
    parts: list[str] = []
    for value in node.values:
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            parts.append(value.value)
        elif isinstance(value, ast.FormattedValue):
            parts.append("{" + ast.unparse(value.value) + "}")
    return "".join(parts)


def human_like(text: str) -> bool:
    stripped = text.strip()
    if not _LETTER.search(stripped):
        return False
    return " " in stripped or stripped[:1].isupper()


class FileScanner:
    def __init__(self, source: str, root: Path, path: Path) -> None:
        self.source = source
        self.rel = path.relative_to(root).as_posix()
        self.zone = zone_of(source, self.rel)
        self.tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        self.parents: dict[int, ast.AST] = {}
        for parent in ast.walk(self.tree):
            for child in ast.iter_child_nodes(parent):
                self.parents[id(child)] = parent
        self.docstrings = self._docstrings()
        self.skipped_no_letter = 0

    def _docstrings(self) -> set[int]:
        found: set[int] = set()
        for node in ast.walk(self.tree):
            body = getattr(node, "body", None)
            if not isinstance(body, list):
                continue
            for stmt in body:
                # docstring de module/classe/fonction ET chaines "commentaire" isolees
                # (documentation d'attribut apres un champ) : jamais affichees
                value = stmt.value if isinstance(stmt, ast.Expr) else None
                if isinstance(value, ast.JoinedStr) or (isinstance(value, ast.Constant) and isinstance(value.value, str)):
                    found.add(id(value))
        return found

    def parent(self, node: ast.AST) -> ast.AST | None:
        return self.parents.get(id(node))

    def scope_of(self, node: ast.AST) -> str:
        names: list[str] = []
        current = self.parent(node)
        while current is not None:
            if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.append(current.name)
            current = self.parent(current)
        return ".".join(reversed(names))

    def entries(self) -> list[Entry]:
        result: list[Entry] = []
        for node in ast.walk(self.tree):
            if isinstance(node, ast.JoinedStr):
                if self._inside_fstring(node):
                    continue
                text = render_fstring(node)
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                if self._inside_fstring(node):
                    continue
                text = node.value
            else:
                continue
            if id(node) in self.docstrings:
                continue
            if not _LETTER.search(text):
                self.skipped_no_letter += 1
                continue
            context, category, reason = self.classify(node, text)
            result.append(Entry(self.source, self.zone, self.rel, node.lineno,
                                self.scope_of(node), context, category, reason, text))
        return result

    def _inside_fstring(self, node: ast.AST) -> bool:
        current = self.parent(node)
        while current is not None:
            if isinstance(current, ast.JoinedStr):
                return True
            if isinstance(current, (ast.stmt,)):
                return False
            current = self.parent(current)
        return False

    # ------------------------------------------------------------------ contexte

    def context_chain(self, node: ast.AST) -> dict:
        info: dict = {"tuple_index": None, "tuple_len": None, "concat": False}
        child: ast.AST = node
        current = self.parent(node)
        while current is not None:
            if isinstance(current, ast.Call):
                if child in current.args:
                    info["call"] = current
                    info["arg_index"] = current.args.index(child)
                elif child is current.func:
                    info["method_of_string"] = call_name(current)
                    info["call"] = current
                if isinstance(self.parent(current), ast.Raise):
                    info["raise"] = True
                return info
            if isinstance(current, ast.keyword):
                info["keyword"] = current.arg
                call = self.parent(current)
                if isinstance(call, ast.Call):
                    info["call"] = call
                return info
            if isinstance(current, (ast.Tuple, ast.List, ast.Set)):
                if info["tuple_index"] is None:
                    info["tuple_index"] = current.elts.index(child) if child in current.elts else None
                    info["tuple_len"] = len(current.elts)
            elif isinstance(current, ast.Dict):
                if child in current.keys:
                    info["dict"] = "cle"
                    return info
                index = current.values.index(child) if child in current.values else -1
                key = current.keys[index] if index >= 0 else None
                info["dict"] = "valeur"
                if isinstance(key, ast.Constant):
                    info["dict_key"] = str(key.value)
            elif isinstance(current, ast.Compare):
                info["compare"] = True
                return info
            elif isinstance(current, ast.Subscript):
                if child is current.slice:
                    info["subscript"] = True
                    return info
            elif isinstance(current, (ast.BinOp,)):
                info["concat"] = True
            elif isinstance(current, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                targets = current.targets if isinstance(current, ast.Assign) else [current.target]
                for target in targets:
                    if isinstance(target, ast.Name):
                        info["assign"] = target.id
                    elif isinstance(target, ast.Attribute):
                        info["assign_attr"] = target.attr
                return info
            elif isinstance(current, ast.Return):
                info["return"] = True
                return info
            elif isinstance(current, ast.Raise):
                info["raise"] = True
                return info
            elif isinstance(current, (ast.stmt,)):
                return info
            child = current
            current = self.parent(current)
        return info

    def describe(self, info: dict) -> str:
        parts: list[str] = []
        call = info.get("call")
        if call is not None and "method_of_string" not in info:
            name = call_name(call)
            if "keyword" in info:
                parts.append(f"{name}({info['keyword']}=)")
            else:
                parts.append(f"{name}(arg{info.get('arg_index', '?')})")
        if "method_of_string" in info:
            parts.append(f'"...".{info["method_of_string"]}()')
        if info.get("tuple_index") is not None:
            parts.append(f"tuple[{info['tuple_index']}/{info['tuple_len']}]")
        if "dict" in info:
            parts.append("dict:cle" if info["dict"] == "cle" else f"dict[{info.get('dict_key', '?')}]")
        for flag, label in (("compare", "comparaison"), ("subscript", "index"),
                            ("return", "return"), ("raise", "raise")):
            if info.get(flag):
                parts.append(label)
        if "assign" in info:
            parts.append(f"{info['assign']} =")
        if "assign_attr" in info:
            parts.append(f".{info['assign_attr']} =")
        if info.get("concat"):
            parts.append("concatenation")
        return " ".join(parts) or "expression"

    # ---------------------------------------------------------------- classement

    def _command_argument(self, node: ast.AST) -> bool:
        """Element d'une liste de commande : `["nft", "add", ...]` (premier element = binaire
        systeme) ou `cmd.extend([...])` / `cmd.append(...)` / `cmd += [...]`. Traduire un
        argument casserait la commande executee (incident evite au lot 3 d'omega-fire :
        `{ type filter hook ... policy accept; }`, `ESTABLISHED,RELATED`)."""
        container = self.parent(node)
        if isinstance(container, (ast.List, ast.Tuple)):
            first = container.elts[0] if container.elts else None
            if isinstance(first, ast.Constant) and first.value in COMMAND_BINARIES:
                return True
            holder = self.parent(container)
        else:
            holder = container
        if isinstance(holder, ast.Call) and isinstance(holder.func, ast.Attribute) \
                and holder.func.attr in {"extend", "append", "insert"} \
                and isinstance(holder.func.value, ast.Name) and holder.func.value.id in COMMAND_VARIABLES:
            return True
        if isinstance(holder, ast.AugAssign) and isinstance(holder.target, ast.Name) \
                and holder.target.id in COMMAND_VARIABLES:
            return True
        return False

    def _iterated_by_comprehension(self, node: ast.AST) -> bool:
        """Element d'une liste/tuple litterale servant d'iterable a une comprehension ou un
        generateur (omega-fire : `any(ind in line_lower for ind in ['failed password', ...])`
        dans domain/logs/parser.py) - des motifs cherches dans un journal, jamais du texte."""
        container = self.parent(node)
        if not isinstance(container, (ast.List, ast.Tuple, ast.Set)):
            return False
        holder = self.parent(container)
        return isinstance(holder, ast.comprehension) and holder.iter is container

    def _in_annotation(self, node: ast.AST) -> bool:
        child, current = node, self.parents.get(id(node))
        while current is not None and not isinstance(current, ast.stmt) or isinstance(current, ast.AnnAssign):
            if isinstance(current, ast.arg) and child is current.annotation:
                return True
            if isinstance(current, ast.AnnAssign):
                return child is current.annotation
            child, current = current, self.parents.get(id(current))
        return isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)) and child is current.returns

    @staticmethod
    def _fixed_parts(node: ast.AST, text: str) -> str:
        """Texte d'une f-string avec chaque champ ramene a {x} (seules les parties fixes comptent)."""
        if not isinstance(node, ast.JoinedStr):
            return text
        return "".join(v.value if isinstance(v, ast.Constant) else "{x}" for v in node.values)

    def _data_field_value(self, node: ast.AST) -> bool:
        """Texte place (meme imbrique : `str(x or "Web")`) sous une cle de DATA_FIELD_KEYS."""
        child, current = node, self.parents.get(id(node))
        while current is not None and not isinstance(current, (ast.stmt,)):
            if isinstance(current, ast.Dict) and child in current.values:
                key = current.keys[current.values.index(child)]
                return isinstance(key, ast.Constant) and key.value in DATA_FIELD_KEYS
            child, current = current, self.parents.get(id(current))
        return False

    def _ascii_fallback(self, node: ast.AST) -> bool:
        """Branche ASCII d'un `a if not use_emoji else b` : elle doit rester en ASCII pur."""
        parent = self.parents.get(id(node))
        if not isinstance(parent, ast.IfExp) or not isinstance(node, ast.Constant):
            return False
        test = ast.unparse(parent.test)
        return bool(re.search(r"emoji|ascii|unicode", test, re.I)) and str(node.value).isascii()

    def classify(self, node: ast.AST, text: str) -> tuple[str, str, str]:
        info = self.context_chain(node)
        context = self.describe(info)
        call = info.get("call")
        name = call_name(call) if call is not None else ""
        keyword = info.get("keyword")
        stripped = text.strip()

        if _LOGO_TARGET.search(info.get("assign") or ""):
            return context, NE_PAS, "ligne du logo ASCII (jamais traduit, comme omega-serv)"
        if info.get("assign") in DATA_SEED_TARGETS:
            return context, NE_PAS, "donnees par defaut enregistrees dans un fichier de l'utilisateur (var/runtime/jail_presets.json) : texte source garde, N_() + traduit a l'affichage (comme les profils omega-serv)"
        if text.startswith("Auto — avant application du profil") or text == "Sauvegarde manuelle (menu 5.4)":
            return context, NE_PAS, "description du snapshot automatique, enregistree avec le snapshot"
        if "%(" in text and ")s" in text:
            return context, NE_PAS, "format de journal Python (`%(asctime)s ...`)"
        if text in LOG_LEVEL_NAMES:
            return context, NE_PAS, "nom de niveau de journal passe a logging"
        if text.startswith("{{") or ' comment "' in text:
            return context, NE_PAS, "syntaxe nft (element `{ ip comment \"...\" }`)"
        if _CONFIG_LINE.match(text):
            return context, NE_PAS, "ligne de fichier de configuration ecrite (`port = ...`)"
        if keyword == "command":
            return context, NE_PAS, "commande (champ technique d'une erreur)"
        if "comment" in (info.get("assign") or "").lower():
            return context, NE_PAS, "commentaire ecrit dans le backend (ban / regle) : donnee relue"
        if self._in_annotation(node):
            return context, NE_PAS, "annotation de type (`environ: \"MutableMapping[str, str]\"`)"
        if _TECH_IDENTIFIER.match(self._fixed_parts(node, text)):
            return context, NE_PAS, "identifiant technique (id de widget, nom de fichier : `action-{x}`)"
        if info.get("assign") in AUDIT_TITLE_TARGETS or name == "log_action_result":
            return context, NE_PAS, "titre / texte ecrit dans l'historique d'audit, relu ensuite (report_builder.py) : texte source"
        if info.get("assign") in PRODUCT_NAME_TARGETS:
            return context, NE_PAS, "nom du produit (jamais traduit)"
        if self._data_field_value(node):
            return context, NE_PAS, "valeur de donnee analysee ensuite par le code (cle 'user_agent'...)"
        if keyword == "stderr":
            return context, NE_PAS, "faux stderr d'une commande, relu par l'adaptateur (`\"not found\" in stderr`)"
        if self._ascii_fallback(node):
            return context, NE_PAS, "variante ASCII pour terminal sans Unicode (`... if not use_emoji else ...`)"
        if self._command_argument(node):
            return context, NE_PAS, "argument d'une commande systeme (nft, iptables, fail2ban-client...)"
        if text.lstrip("\n").startswith("#"):
            return context, NE_PAS, "contenu d'un fichier ecrit (en-tete de blocklist, configuration de jail fail2ban)"
        if _SQL_FRAGMENT.match(text):
            return context, NE_PAS, "morceau de requete SQL (`query += \" AND x = ?\"`)"
        if _MARKER_TARGET.search(info.get("assign") or ""):
            return context, NE_PAS, "motif cherche dans une sortie / une erreur (constante *_MARKERS, *_PATTERNS...)"
        if self.scope_of(node).split(".")[-1] in {"__repr__", "__str__"} and _DEBUG_REPR.match(text):
            return context, NE_PAS, "representation de debogage (`Classe(champ=...)`)"
        if self._iterated_by_comprehension(node):
            return context, NE_PAS, "motif d'une liste parcourue pour une recherche (`x in ligne for x in [...]`)"
        legacy_scopes = LEGACY_CLI_SCOPES.get(self.rel, ())
        if legacy_scopes and self.scope_of(node).split(".")[0] in legacy_scopes:
            return context, NE_PAS, "ancienne interface --legacy-cli (Q1) : reste en francais"
        if name in MARK_CALLS and "method_of_string" not in info:
            for marker, _why in MACHINE_CONTRACTS:
                if marker in text:
                    return context, TRADUIRE, f"texte d'aide citant le marqueur '{marker.strip()}' : le garder TEL QUEL dans la traduction"
            return context, TRADUIRE, "marque pour traduction (_ / N_ / ngettext)"
        if text in NEVER_TRANSLATED_TEXTS:
            return context, NE_PAS, "selecteur de langue : libelle bilingue / nom de langue, jamais traduit (plan §5.3)"
        if self.rel in EXCHANGE_FORMAT_FILES:
            return context, NE_PAS, "format d'echange normalise (STIX 2.1 / MISP), en anglais, jamais traduit"
        for marker, why in MACHINE_CONTRACTS:
            if marker in text:
                if self.zone == "guide" or name in UI_TEXT_CALLS or keyword in UI_TEXT_KW:
                    return context, TRADUIRE, f"texte d'aide citant le marqueur '{marker.strip()}' : le garder TEL QUEL dans la traduction"
                return context, NE_PAS, f"contrat machine : {why}"
        if _RICH_STYLE.match(stripped):
            return context, NE_PAS, "style Rich (couleurs / attributs)"
        if self.rel.startswith("interfaces/cli/themes/"):
            return context, NE_PAS, "theme : nom propre du theme ou definition de style"
        if _DRAWING.search(text) and len(_LETTER.findall(text)) < len(text) * 0.3:
            if _WORD.search(text):
                return context, PROBABLE, "titre decore (cadre + mots)"
            return context, NE_PAS, "logo / dessin ASCII"
        if _SQL.search(text):
            return context, NE_PAS, "requete / schema SQL"
        if any(t in (info.get("assign") or "") for t in HEADER_VALUE_TARGETS):
            return context, NE_PAS, "valeur d'en-tete HTTP"
        if (_HTML.search(text) or _ANY_TAG.search(text)) and "(?P<" not in text:
            without_style = re.sub(r"<style>.*?</style>", " ", text, flags=re.DOTALL)
            visible = _ANY_TAG.sub(" ", re.sub(r"\{[^{}]*\}", " ", without_style))
            if not _WORD.search(visible.replace("OMEGA-FIRE", "")):
                return context, NE_PAS, "gabarit HTML sans texte (textes visiteurs passes par P_)"
            return context, A_DECIDER, "fragment HTML (export / rapport ?)"
        if _CAMEL.match(stripped):
            return context, NE_PAS, "nom de classe / type"
        if info.get("assign") in SEARCH_TARGETS:
            return context, NE_PAS, "fragment cherche dans un autre texte (needle/marker...)"
        if info.get("assign") in PROTOCOL_TARGETS:
            return context, NE_PAS, "phrase de statut HTTP (protocole, RFC 9110)"
        if info.get("assign") in CSS_TARGETS or (text.count("{") and text.count(";") >= 2 and text.count(":") >= 2):
            return context, NE_PAS, "CSS"
        if "method_of_string" in info and info["method_of_string"] not in {"format"}:
            return context, NE_PAS, f'chaine utilisee comme valeur ("...".{info["method_of_string"]}())'

        # Contextes d'interface reconnus sans ambiguite
        if name in GUIDE_CALLS:
            if keyword in GUIDE_MACHINE_KW or (name == "ScreenGuide" and info.get("arg_index") == 0 and keyword is None):
                return context, NE_PAS, "cle du guide (nom de classe d'ecran)"
            return context, TRADUIRE, f"fiche du guide ({name})"
        if self.zone == "guide" and human_like(text) and not info.get("compare") and not info.get("subscript") and info.get("dict") != "cle":
            return context, TRADUIRE, "texte du guide"
        if name == "Binding" or (info.get("assign") == "BINDINGS"):
            position = info.get("arg_index") if name == "Binding" else info.get("tuple_index")
            if keyword == "description" or position == 2:
                return context, TRADUIRE, "description de raccourci (pied de page)"
            if keyword == "tooltip":
                return context, TRADUIRE, "infobulle de raccourci"
            return context, NE_PAS, "touche / action de raccourci"
        if keyword in MACHINE_KW and keyword not in UI_TEXT_KW:
            return context, NE_PAS, f"argument technique ({keyword}=)"
        if info.get("dict") == "cle":
            return context, NE_PAS, "cle de dictionnaire"
        if info.get("subscript"):
            return context, NE_PAS, "index / cle d'acces"
        if info.get("compare"):
            return context, NE_PAS, "valeur comparee"
        if name in LOG_CALLS:
            return context, NE_PAS, "ligne de journal (identique quelle que soit la langue)"
        if name in UI_TEXT_CALLS or keyword in UI_TEXT_KW or info.get("assign_attr") in UI_TEXT_ATTRS or info.get("assign") in UI_TEXT_ATTRS:
            if not human_like(text) and _IDENTIFIER.match(stripped):
                return context, NE_PAS, "identifiant passe a un widget"
            if self.zone == "cli" and keyword in {"help", "description", "epilog"}:
                return context, TRADUIRE, "aide de la CLI"
            return context, TRADUIRE, "texte de widget / notification"
        if name == "add_argument":
            if keyword in {"help"}:
                return context, TRADUIRE, "aide de la CLI"
            return context, NE_PAS, "option de la CLI (nom de commande / drapeau)"
        if name in MACHINE_CALLS:
            return context, NE_PAS, f"argument technique ({name}())"

        # Mots francais isoles affiches (oui/non/actif, statuts en majuscules)
        if " " not in stripped and (stripped.lower() in FRENCH_WORDS or _ACCENT.search(stripped)) \
                and keyword is None and info.get("dict") != "cle":
            return context, PROBABLE, "mot francais isole (affiche tel quel ?)"
        if stripped in SEVERITY_WORDS:
            return context, A_DECIDER, "niveau de gravite affiche tel quel (anglais technique)"

        # Formes techniques
        if stripped.startswith("-") and _IDENTIFIER.match(stripped):
            return context, NE_PAS, "drapeau / option"
        if _IDENTIFIER.match(stripped) and " " not in stripped:
            return context, NE_PAS, "identifiant / valeur technique"
        if _CONSTANT.match(stripped):
            return context, NE_PAS, "constante technique (MAJUSCULES)"
        if _REGEX_HINT.search(text) and " " not in stripped:
            return context, NE_PAS, "motif / expression reguliere"
        if re.match(r"^[a-z]+://", stripped) or stripped.startswith(("/", "./", "~/")) and " " not in stripped:
            return context, NE_PAS, "URL / chemin"

        # Selecteur d'options (libelle, valeur)
        if info.get("tuple_len") == 2 and info.get("tuple_index") == 0 and human_like(text):
            return context, TRADUIRE, "libelle d'option (couple libelle/valeur)"
        if self.zone in {"ecrans", "widgets", "tui-autre"} and info.get("tuple_len") in (2, 3, 4) \
                and info.get("tuple_index") not in (None, 0) and human_like(text) and " " in text.strip():
            return context, TRADUIRE, "libelle dans un tableau de definition (menu / formulaire)"

        # Messages : stderr, CLI, exceptions
        scope = self.scope_of(node)
        if (call is not None and (is_stderr_print(call) or name == "print")) or info.get("raise"):
            if self.rel in BUILD_TOOL_FILES:
                return context, NE_PAS, "message de l'outil de construction (build-release.sh), jamais vu dans l'interface"
            if self.rel in SERVER_PROCESS_FILES or scope.split(".")[0] in SERVER_PROCESS_SCOPES:
                return context, NE_PAS, "message du journal de l'application (app.log / audit.log) - Q7 : reste en francais"
        if call is not None and is_stderr_print(call):
            return context, A_DECIDER, "message stderr (terminal)"
        if name == "print":
            if self.zone == "cli":
                return context, TRADUIRE, "sortie CLI pour l'humain (verifier : jamais lue par un script ?)"
            return context, A_DECIDER, "print hors CLI"
        if info.get("raise"):
            return context, A_DECIDER, "message d'exception (affiche a l'ecran ?)"

        if not _WORD.search(re.sub(r"\{[^{}]*\}", "", text)):
            return context, NE_PAS, "gabarit sans texte (seulement des {variables})"
        if not human_like(text):
            return context, NE_PAS, "mot technique sans espace"
        if self.zone in {"ecrans", "widgets", "tui-autre", "cli-tui"}:
            return context, PROBABLE, "texte humain dans l'interface, contexte non reconnu"
        if self.zone == "cli":
            return context, PROBABLE, "texte humain dans la CLI, contexte non reconnu"
        return context, A_DECIDER, f"texte humain dans {self.zone}"


_J2_BLOCK = re.compile(r"\{\{.*?\}\}|\{%.*?%\}|\{#.*?#\}", re.DOTALL)
_J2_TEXT = re.compile(r">([^<>]+)<")
_J2_ATTR = re.compile(r"\b(title|alt|placeholder|aria-label)=\"([^\"]+)\"")


def scan_templates(source: str, root: Path) -> list[Entry]:
    """Modeles Jinja2 d'export HTML (retour utilisateur 2026-10-21 : les exports doivent
    suivre la langue de l'interface). Texte entre balises et attributs lisibles ; les
    expressions {{ }} / {% %} sont des donnees, deja relevees cote Python."""
    entries: list[Entry] = []
    for path in sorted(root.rglob("*.j2")):
        rel = path.relative_to(root).as_posix()
        lines = path.read_text(encoding="utf-8").splitlines()
        for number, line in enumerate(lines, 1):
            masked = _J2_BLOCK.sub(lambda m: " " * len(m.group(0)), line)
            if "<style" in masked or masked.strip().startswith(("{", "}", ".", "@")) and not _LETTER.search(masked.split("{")[0]):
                pass
            for match in _J2_TEXT.finditer(masked):
                text = match.group(1).strip()
                if _WORD.search(text.replace("OMEGA-FIRE", "")) and not text.startswith(("{", ".", "#")) and ";" not in text:
                    entries.append(Entry(source, "exports-html", rel, number, "", "texte de modele HTML",
                                         TRADUIRE, "texte d'un modele d'export HTML (Jinja2)", text))
            for attr in _J2_ATTR.finditer(masked):
                entries.append(Entry(source, "exports-html", rel, number, "", f"attribut {attr.group(1)}=",
                                     TRADUIRE, "attribut lisible d'un modele d'export HTML", attr.group(2)))
            if 'lang="' in line:
                entries.append(Entry(source, "exports-html", rel, number, "", "attribut lang=", NE_PAS,
                                     "langue de la page : a rendre DYNAMIQUE (langue active), pas a traduire",
                                     line.strip()))
    return entries


_J2_TEST = re.compile(r"\{%-?\s*(?:el)?if\s+(.*?)-?%\}", re.S)
_J2_LITERAL = re.compile(r"""["']([^"']+)["']""")


def template_compared_texts(root: Path) -> set[str]:
    """Textes compares dans les modeles HTML (`{% if group.state == "ACTIF" %}`) : la valeur
    Python passee au modele ne doit pas etre traduite, sinon le test du modele echoue."""
    found: set[str] = set()
    for path in root.rglob("*.j2"):
        for test in _J2_TEST.finditer(path.read_text(encoding="utf-8")):
            found.update(_J2_LITERAL.findall(test.group(1)))
    return found


legacy: list[str] = []


def scan() -> tuple[list[Entry], int, list[str]]:
    entries: list[Entry] = []
    skipped = 0
    missing: list[str] = []
    legacy.clear()
    _TUI_USED.clear()
    _TUI_USED.update(tui_used_cli_files(SOURCES[0][1]))
    for source, root in SOURCES:
        if not root.is_dir():
            missing.append(f"{source} : {root} introuvable")
            continue
        for path in sorted(root.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            if source == "omega-fire" and is_legacy_cli(path.relative_to(root).as_posix()):
                legacy.append(path.relative_to(root).as_posix())
                continue
            scanner = FileScanner(source, root, path)
            entries.extend(scanner.entries())
            skipped += scanner.skipped_no_letter
    templates = SOURCES[0][1]
    if templates.is_dir():
        entries.extend(scan_templates("omega-fire", templates))
    # Garde-fou omega-fire : un texte affiche qui sert AUSSI de valeur comparee / de cle ailleurs
    # (ex. "INACTIF" affiche puis teste par `if statut == "INACTIF"`) casserait la logique si on
    # le traduisait sans precaution -> revue ligne par ligne.
    as_value = {e.text for e in entries if e.reason in {"valeur comparee", "cle de dictionnaire", "index / cle d'acces"}}
    as_value |= template_compared_texts(SOURCES[0][1])
    for e in entries:
        if e.category in (TRADUIRE, PROBABLE) and e.text in as_value and e.reason != "fiche du guide (HelpEntry)":
            e.category, e.reason = A_DECIDER, "texte affiche ET utilise ailleurs comme valeur comparee / cle : verifier avant de traduire"
    entries.sort(key=lambda e: (e.source, e.zone, e.file, e.line))
    return entries, skipped, missing


# ---------------------------------------------------------------------- sorties

_PIPE_SPLIT = re.compile(r"(?<!\\)\|")


def normalize_decision(raw: str) -> tuple[str, str]:
    """'TRADUIRE et renommer...' -> ('TRADUIRE', 'et renommer...') ; vide -> ('', '')."""
    cleaned = raw.strip()
    for category in sorted(CATEGORIES, key=len, reverse=True):
        if cleaned.upper().startswith(category):
            return category, cleaned[len(category):].strip(" :-")
    return "", cleaned


def read_md_table(path: Path) -> list[list[str]]:
    rows: list[list[str]] = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or set(stripped) <= set("|-: "):
            continue
        cells = [re.sub(r"\\(.)", r"\1", c.strip()) for c in _PIPE_SPLIT.split(stripped.strip("|"))]
        rows.append(cells)
    return rows  # en-tetes compris : load_rule_decisions repere les colonnes par leur nom


def load_rule_decisions(path: Path) -> dict[tuple[str, str], tuple[str, str]]:
    """Colonnes reperees par leur EN-TETE (jamais par leur position) : l'ordre des colonnes
    peut changer sans perdre une decision. Accepte l'ancienne disposition
    (Categorie automatique | Raison | Nombre | Decision | Note)."""
    decisions: dict[tuple[str, str], tuple[str, str]] = {}
    columns: dict[str, int] | None = None
    for cells in read_md_table(path):
        lowered = [c.lower() for c in cells]
        if "raison" in lowered:
            columns = {}
            for index, header in enumerate(lowered):
                if header.startswith(("décision", "decision")):
                    columns["decision"] = index
                elif header == "raison":
                    columns["reason"] = index
                elif "origine" in header or "automatique" in header:
                    columns["auto"] = index
                elif header == "note":
                    columns["note"] = index
            continue
        if columns is None or not {"decision", "reason", "auto"} <= set(columns) or len(cells) <= max(columns.values()):
            continue
        auto = cells[columns["auto"]].strip("`")
        decision, rest = normalize_decision(cells[columns["decision"]])
        note = cells[columns["note"]] if "note" in columns else ""
        decisions[(auto, cells[columns["reason"]])] = (decision, " ".join(x for x in (rest, note) if x))
    return decisions


def load_line_decisions(path: Path) -> dict[str, tuple[str, str]]:
    decisions: dict[str, tuple[str, str]] = {}
    if not path.is_file():
        return decisions
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            decision, rest = normalize_decision(row.get("decision_utilisateur", ""))
            note = " ".join(x for x in (rest, row.get("note", "")) if x)
            if decision or note:
                decisions[row["id"]] = (decision, note)
    return decisions


def apply_decisions(entries: list[Entry], rules: dict, lines: dict) -> None:
    for e in entries:
        e.auto = e.category
        rule_decision, rule_note = rules.get((e.auto, e.reason), ("", ""))
        line_decision, line_note = lines.get(e.ident, ("", ""))
        e.rule_decision, e.line_decision = rule_decision, line_decision
        e.note = " ".join(x for x in (line_note, rule_note) if x)
        e.category = line_decision or rule_decision or e.auto


def write_rule_decisions(entries: list[Entry], rules: dict, path: Path) -> None:
    groups: Counter = Counter((e.auto, e.reason) for e in entries)
    lines = [
        "# Inventaire i18n — décisions par règle",
        "",
        ("> Fichier **édité par toi**, relu à chaque génération de l'inventaire "
         "(`omega-fire/tools/i18n_inventory.py`), jamais écrasé : les règles nouvelles sont "
         "ajoutées, tes décisions restent."),
        ("> Colonne **Décision** : `TRADUIRE`, `NE-PAS-TRADUIRE`, ou vide (= garder le "
         "pré-classement d'origine, affiché à droite pour information). Colonne **Note** : libre."),
        "> Une décision ligne par ligne (colonne `decision_utilisateur` du CSV) passe avant celle-ci.",
        "",
        "| Décision | Raison | Nombre | Pré-classement d'origine | Note |",
        "|---|---|---:|---|---|",
    ]
    for (auto, reason), count in sorted(groups.items(), key=lambda kv: (CATEGORIES.index(kv[0][0]), -kv[1])):
        decision, note = rules.get((auto, reason), ("", ""))
        lines.append(f"| {decision} | {_md_text(reason)} | {count} | `{auto}` | {_md_text(note)} |")
    orphans = [key for key in rules if key not in groups and rules[key][0]]
    if orphans:
        lines += ["", "## Décisions dont la règle n'existe plus (gardées pour mémoire)", "",
                  "| Décision | Raison | Nombre | Pré-classement d'origine | Note |", "|---|---|---:|---|---|"]
        for auto, reason in orphans:
            decision, note = rules[(auto, reason)]
            lines.append(f"| {decision} | {_md_text(reason)} | 0 | `{auto}` | {_md_text(note)} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_csv(entries: list[Entry], path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["id", "zone", "fichier", "ligne", "portee", "contexte", "categorie",
                         "categorie_auto", "raison", "decision_regle", "texte",
                         "decision_utilisateur", "note"])
        for e in entries:
            writer.writerow([e.ident, e.zone, f"{e.source}/{e.file}", e.line, e.scope, e.context,
                             e.category, e.auto, e.reason, e.rule_decision, e.text,
                             e.line_decision, e.note])


def _md_code(text: str, limit: int = 110) -> str:
    """Texte du code dans un bloc de code Markdown : HTML, *, _, [ ] neutralises, texte exact
    (y compris les accents graves, entoures d'une cloture plus longue)."""
    one_line = " ".join(text.split())
    if len(one_line) > limit:
        one_line = one_line[: limit - 1] + "…"
    one_line = one_line.replace("|", "\\|")
    longest = max((len(m) for m in re.findall(r"`+", one_line)), default=0)
    fence = "`" * (longest + 1)
    if longest or one_line.startswith(" ") or one_line.endswith(" "):
        return f"{fence} {one_line} {fence}"
    return f"{fence}{one_line}{fence}"


def _md_text(text: str) -> str:
    """Texte libre (raisons, notes) : echappe ce qui casserait un tableau Markdown."""
    escaped = " ".join(text.split()).replace("\\", "\\\\")
    for char in "|*_[]<>`":
        escaped = escaped.replace(char, "\\" + char)
    return escaped


ZONE_ORDER = ("ecrans", "widgets", "tui-autre", "guide", "cli", "exports-html", "application", "domaine",
              "infrastructure", "socle", "omega-lib")

TEXTUAL_BUILTINS = (
    ("`Select` sans libelle d'invite", "\"Select\"", "affiche si une liste deroulante autorise le vide sans `prompt=`", "remplacable : passer `prompt=` traduit"),
    ("Ctrl+C dans l'application", "\"Press ctrl+q to quit the app\" / \"Do you want to quit?\"", "notification de Textual (`action_help_quit`)", "remplacable : surcharger l'action (a verifier : deja surchargee par le correctif SIGINT ?)"),
    ("Icone de l'en-tete (`Header`)", "infobulle \"Open the command palette\"", "79 ecrans utilisent `Header`", "remplacable ou retirable (palette neutralisee)"),
    ("Pied de page (`Footer`)", "libelle \"palette\"", "affiche si la palette de commandes est active", "a verifier : la palette est neutralisee (check_action)"),
    ("Raccourci Ctrl+Q de Textual", "\"Quit\" / \"Quit the app and return to the command prompt.\"", "`show=False` : visible seulement dans l'aide des touches", "remplacable : redefinir la liaison"),
    ("Capture d'ecran Textual", "\"Saved screenshot\" / \"Screenshot\"", "notification de `action_screenshot`", "a verifier : utilise par omega-fire ?"),
    ("Raccourcis Tab / Maj+Tab", "\"Focus Next\" / \"Focus Previous\"", "`show=False`", "invisibles, laisses tels quels"),
)
OUTSIDE_TEXTS = (
    ("Sorties d'outils externes affichees telles quelles", "openssl, certbot, systemctl, journalctl, lnav, fail2ban-client", "jamais traduites (texte de l'outil, souvent deja dans la langue du systeme)"),
    ("Messages d'exception Python / OSError", "`[Errno 13] Permission denied`…", "affiches tels quels apres notre texte traduit"),
    ("Contenu des fichiers de l'utilisateur", "listes de chemins, config, journaux affiches dans l'editeur ou lnav", "jamais traduits"),
    ("Logo ASCII du splash", "art ASCII", "jamais traduit ; la phrase \"Appuyez sur une touche pour continuer...\" l'est"),
)


def write_md(entries: list[Entry], skipped: int, missing: list[str], path: Path, csv_name: str,
             decisions_name: str) -> None:
    by_zone_cat: dict[str, Counter] = defaultdict(Counter)
    chars: dict[str, int] = Counter()
    for e in entries:
        by_zone_cat[e.zone][e.category] += 1
        if e.category in (TRADUIRE, PROBABLE):
            chars[e.zone] += len(e.text)
    totals = Counter(e.category for e in entries)
    lines: list[str] = []
    w = lines.append
    w("# Inventaire des textes de l'interface — OMEGA-FIRE")
    w("")
    w(f"> Généré le {datetime.now().astimezone().date().isoformat()} par `omega-fire/tools/i18n_inventory.py` "
      "(lecture seule sur le code). Plan : `OMEGA-FIRE_PLAN-DETAILLE_I18N.md` §4, lot 1.")
    w(f"> Ancienne interface `--legacy-cli` exclue (Q1) : {len(legacy)} fichiers non relevés "
      "(`actions.py`, `app.py`, `menu_builder.py`…), restent en français.")
    w(f"> Détail ligne par ligne : `{csv_name}` (une ligne par texte, colonnes "
      "`decision_utilisateur` et `note` à remplir pendant la revue).")
    w("")
    w("> **Ce fichier est régénéré à chaque passage : ne pas l'éditer.** Tes décisions vont dans "
      f"`{decisions_name}` (par règle) ou dans les colonnes `decision_utilisateur` / `note` du CSV "
      "(par ligne) ; elles sont relues et appliquées ici à chaque génération.")
    w("")
    w("**Statut : pré-classement automatique + tes décisions — à valider (§4.5).** Rien n'est "
      "marqué pour traduction tant que cet inventaire n'est pas validé.")
    w("")
    if missing:
        w("⚠️ Sources absentes : " + " ; ".join(missing))
        w("")
    w("## 1. Les catégories")
    w("")
    w("| Catégorie | Sens | Ce que tu dois faire |")
    w("|---|---|---|")
    w("| `TRADUIRE` | texte pour l'utilisateur, contexte reconnu sans ambiguïté (bouton, titre, notification, fiche du guide…) | survol |")
    w("| `TRADUIRE-PROBABLE` | a l'air humain, dans un écran, mais le contexte n'est pas reconnu | vérifier |")
    w("| `NE-PAS-TRADUIRE` | identifiant, clé, valeur, chemin, motif, CSS, journal, contrat machine | **vérifier les raisons** : une erreur ici = texte resté en français |")
    w("| `A-DECIDER` | messages du cœur, stderr, exceptions, sorties de commandes | **décider un par un** (ou par groupe) |")
    w("")
    w(f"Total : **{len(entries)} textes relevés** "
      f"({skipped} chaînes sans aucune lettre ignorées : ponctuation, séparateurs, nombres).")
    w("")
    w("## 2. Récapitulatif par zone")
    w("")
    w("| Zone | TRADUIRE | PROBABLE | NE PAS | À DÉCIDER | Total | Caractères à traduire* |")
    w("|---|---:|---:|---:|---:|---:|---:|")
    for zone in [z for z in ZONE_ORDER if z in by_zone_cat] + sorted(set(by_zone_cat) - set(ZONE_ORDER)):
        c = by_zone_cat[zone]
        w(f"| {zone} | {c[TRADUIRE]} | {c[PROBABLE]} | {c[NE_PAS]} | {c[A_DECIDER]} | {sum(c.values())} | {chars[zone]:,} |".replace(",", " "))
    w(f"| **Total** | **{totals[TRADUIRE]}** | **{totals[PROBABLE]}** | **{totals[NE_PAS]}** | **{totals[A_DECIDER]}** | **{len(entries)}** | **{sum(chars.values()):,}** |".replace(",", " "))
    w("")
    w("\\* TRADUIRE + PROBABLE, avant décision sur les « à décider ».")
    w("")
    w("## 3. Raisons du pré-classement (pour valider les règles d'un coup)")
    w("")
    w("Chaque règle s'applique à beaucoup de textes : valider ou corriger une **règle** est plus "
      "rapide que de relire chaque ligne. Exemples pris au hasard dans chaque groupe.")
    w("")
    by_reason: dict[tuple[str, str], list[Entry]] = defaultdict(list)
    for e in entries:
        by_reason[(e.auto, e.reason)].append(e)
    w("| Catégorie retenue | Raison | Nombre | Pré-classement d'origine | Exemples |")
    w("|---|---|---:|---|---|")
    for (category, reason), group in sorted(by_reason.items(), key=lambda kv: (CATEGORIES.index(kv[1][0].category), CATEGORIES.index(kv[0][0]), -len(kv[1]))):
        step = max(1, len(group) // 3)
        samples = " · ".join(_md_code(e.text, 40) for e in group[::step][:3])
        final = Counter(e.category for e in group)
        final_text = ", ".join(c if n == len(group) else f"{c} {n}" for c, n in final.most_common())
        decided = any(e.rule_decision or e.line_decision for e in group)
        origin = f"`{category}` (décidé)" if decided else f"`{category}`"
        w(f"| **{final_text}** | {_md_text(reason)} | {len(group)} | {origin} | {samples} |")
    w("")
    w("## 4. Écrans : volume par fichier")
    w("")
    w("| Écran (fichier) | TRADUIRE | PROBABLE | À DÉCIDER | NE PAS |")
    w("|---|---:|---:|---:|---:|")
    per_file: dict[str, Counter] = defaultdict(Counter)
    for e in entries:
        if e.zone in {"ecrans", "widgets", "tui-autre"}:
            per_file[e.file][e.category] += 1
    for file, c in sorted(per_file.items(), key=lambda kv: -(kv[1][TRADUIRE] + kv[1][PROBABLE])):
        w(f"| `{file}` | {c[TRADUIRE]} | {c[PROBABLE]} | {c[A_DECIDER]} | {c[NE_PAS]} |")
    w("")
    w("## 5. Contrats machine (§4.3) — jamais traduits")
    w("")
    w("| Marqueur | Pourquoi | Occurrences trouvées dans le code |")
    w("|---|---|---|")
    for marker, why in MACHINE_CONTRACTS:
        found = [f"`{e.file}:{e.line}`" for e in entries if marker in e.text]
        w(f"| `{marker.strip()}` | {why} | {', '.join(found[:6]) or '—'}{' …' if len(found) > 6 else ''} |")
    w("")
    w("Aussi jamais traduits : clés et valeurs de config, noms de commandes et options CLI, sortie "
      "de `nft`/`iptables`/`fail2ban-client`/`systemctl` analysée par l'application, format de `app.log` "
      "et `audit.log`, formats lnav, schéma SQLite, noms de jails/tables/chaînes/sets, "
      "noms de fichiers et identifiants de règles.")
    w("")
    w("## 6. Textes hors de notre code (§4.4)")
    w("")
    w("### 6.1 Textes anglais de Textual (8.2.8)")
    w("")
    w("| Où | Texte | Quand il apparaît | Traitement proposé |")
    w("|---|---|---|---|")
    for row in TEXTUAL_BUILTINS:
        w("| " + " | ".join(row) + " |")
    w("")
    w("### 6.2 Autres textes affichés tels quels")
    w("")
    w("| Quoi | Exemples | Traitement |")
    w("|---|---|---|")
    for row in OUTSIDE_TEXTS:
        w("| " + " | ".join(row) + " |")
    w("")
    w("## 7. Textes encore « À DÉCIDER » (après tes décisions), par fichier")
    w("")
    if not any(e.category == A_DECIDER for e in entries):
        w("Aucun : tous les groupes ont reçu une décision.")
        w("")
    undecided: dict[str, list[Entry]] = defaultdict(list)
    for e in entries:
        if e.category == A_DECIDER:
            undecided[f"{e.source}/{e.file}"].append(e)
    for file, group in sorted(undecided.items()):
        w(f"### `{file}` ({len(group)})")
        w("")
        w("| Ligne | Contexte | Raison | Texte |")
        w("|---:|---|---|---|")
        for e in group:
            w(f"| {e.line} | {_md_code(e.context, 40)} | {_md_text(e.reason)} | {_md_code(e.text)} |")
        w("")
    w("## 8. Revue (§4.5)")
    w("")
    w(f"1. Décider par **règle** dans `{decisions_name}` (colonne Décision), surtout les règles "
      "en `NE-PAS-TRADUIRE` : une erreur là = texte resté en français.")
    w("2. Trancher ce qui reste en section 7.")
    w("3. Toute correction ponctuelle : colonne `decision_utilisateur` du CSV "
      "(`TRADUIRE` / `NE-PAS-TRADUIRE`) + `note`.")
    w("4. Relancer `.venv/bin/python tools/i18n_inventory.py` : ce fichier se met à jour, "
      "tes décisions sont conservées.")
    w("5. Une fois validé : l'inventaire est figé et devient la référence du lot 4 (marquage) ; "
      "un test (§4.6) empêchera ensuite tout nouveau texte non classé.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--csv", type=Path, default=PROJECT.parent / "i18n_inventaire.csv")
    parser.add_argument("--md", type=Path, default=PROJECT.parent / "I18N_INVENTAIRE.md")
    parser.add_argument("--decisions", type=Path, default=PROJECT.parent / "I18N_DECISIONS.md")
    args = parser.parse_args(argv)
    entries, skipped, missing = scan()
    rules = load_rule_decisions(args.decisions)
    lines = load_line_decisions(args.csv)
    apply_decisions(entries, rules, lines)
    write_rule_decisions(entries, rules, args.decisions)
    write_csv(entries, args.csv)
    write_md(entries, skipped, missing, args.md, args.csv.name, args.decisions.name)
    totals = Counter(e.category for e in entries)
    print(f"{len(entries)} textes : " + ", ".join(f"{c} {totals[c]}" for c in CATEGORIES))
    print(f"-> {args.md}\n-> {args.csv}\n-> {args.decisions} (decisions : {sum(1 for d in rules.values() if d[0])} regles, {sum(1 for d in lines.values() if d[0])} lignes)")
    if missing:
        print("ATTENTION : " + " ; ".join(missing), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
