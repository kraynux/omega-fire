# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Traduction de l'interface (OMEGA-FIRE_PLAN-DETAILLE_I18N.md §5) - seul point d'acces
aux phrases traduites pour tout le code d'omega-fire (meme module que omega_serv/core/i18n.py).

    from omega_fire.shared.i18n import _, N_, ngettext

- `_("Texte")` : phrase traduite dans la langue active (francais par defaut : texte tel quel).
- `ngettext("{n} regle", "{n} regles", n)` : pluriels (3 formes en russe).
- `N_("Texte")` : marque une constante definie au chargement d'un module, traduite plus
  tard a l'affichage avec `_()`.

La langue est installee UNE fois, au demarrage de la TUI, avant la construction de
l'interface (app/early_language.py). Changer de langue redemarre l'interface (os.execv) ;
le pare-feu, fail2ban et les services ne sont jamais touches. L'ancienne interface
(--legacy-cli) n'installe jamais de langue (Q1) : elle reste en francais.

Langue des exports (lot N, Q3) : un export se produit dans ce meme processus. Pendant sa
generation, `translating_as(etat)` fait repondre `_()` dans la langue des exports, pour le
seul fil d'execution (ou la seule tache asyncio) qui produit l'export : l'interface,
qui continue de s'afficher a cote, reste dans sa langue."""
from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from omega_lib.i18n.policies import text_direction
from omega_lib.i18n.service import TranslationState, mark

DOMAIN = "omega-fire"
"""Nom des catalogues : locale/<langue>/LC_MESSAGES/omega-fire.mo."""

STATE = TranslationState()

N_ = mark

_EXPORT_STATE: ContextVar[TranslationState | None] = ContextVar("omega_fire_export_language", default=None)


def active_state() -> TranslationState:
    """Langue des exports pendant un export qui en a une autre, sinon celle de l'interface."""
    return _EXPORT_STATE.get() or STATE


@contextmanager
def translating_as(state: TranslationState | None) -> Iterator[None]:
    """Traduit dans `state` le temps du bloc (None : langue de l'interface, rien ne change)."""
    token = _EXPORT_STATE.set(state)
    try:
        yield
    finally:
        _EXPORT_STATE.reset(token)


def _(message: str) -> str:
    return active_state().gettext(message)


class LazyText(str):
    """Texte traduit dans la langue active au moment ou il est cree, qui garde sa source
    (msgid marque N_) et ses valeurs pour etre recompose dans une autre langue : motifs des
    capacites, rediges au scan puis relus par les exports (retour utilisateur 2026-10-28 :
    rapport d'audit en allemand avec les motifs restes en francais)."""

    msgid: str
    params: dict

    def __new__(cls, msgid: str, **params: object) -> "LazyText":
        text = _(msgid)
        obj = super().__new__(cls, text.format(**params) if params else text)
        obj.msgid = msgid
        obj.params = params
        return obj


def lazy(msgid: str, **params: object) -> str:
    """`lazy(N_("Port {port} ouvert"), port=22)` : comme `_(...).format(...)`, recomposable."""
    return LazyText(msgid, **params)


def retranslate(value: object) -> object:
    """Recompose un LazyText dans la langue active (celle de l'export sous translating_as) ;
    toute autre valeur est rendue telle quelle."""
    if isinstance(value, LazyText):
        params = {key: retranslate(param) for key, param in value.params.items()}
        text = _(value.msgid)
        return text.format(**params) if params else text
    return value


def ngettext(singular: str, plural: str, n: int) -> str:
    return active_state().ngettext(singular, plural, n)


def html_lang() -> str:
    """Attribut lang= des exports HTML, dans la langue de l'export en cours (BCP 47 :
    zh_CN -> zh-CN ; la langue de controle reste annoncee comme du francais)."""
    code = active_state().language.code
    return "fr" if code.startswith("x-") else code.replace("_", "-")


def html_dir() -> str:
    """Attribut dir= des exports HTML : "rtl" en arabe, "ltr" sinon."""
    return text_direction(active_state().language.code)


_action_title_translator: Callable[[str], str] | None = None


def set_action_title_translator(translator: Callable[[str], str] | None) -> None:
    """Installe par l'interface (interfaces/tui/support/action_titles.py) : elle seule connait
    les libelles des menus. Sans lui (ancienne CLI, tests) : titres affiches tels quels."""
    global _action_title_translator
    _action_title_translator = translator


def action_title(stored: str) -> str:
    """Titre d'action lu dans l'historique d'audit, affiche dans la langue active (celle de
    l'export pendant un export). L'historique garde, lui, le titre tel qu'il a ete ecrit."""
    return stored if _action_title_translator is None else _action_title_translator(stored)
