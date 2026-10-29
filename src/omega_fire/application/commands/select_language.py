# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Cas d'usage : langue de l'interface (OMEGA-FIRE_PLAN-DETAILLE_I18N.md §5, lot 2) - repris
d'omega_serv/application/terminal/select_language.py.

Ordre de priorite au demarrage :
  1. variable d'environnement OMEGA_FIRE_LANG (une fois, sans toucher au reglage) - voie de
     secours : `OMEGA_FIRE_LANG=fr ./omega-fire.sh` relance en francais ;
  2. reglage `language` du fichier de reglages (Reglages -> "Langue / Language") ;
  3. francais.
Langue indisponible ou catalogue illisible : francais, et le repli est memorise pour etre
signale une fois a l'ecran. Jamais d'erreur au demarrage.

Console TTY Linux (police limitee) avec une langue a ecriture large (chinois, japonais,
coreen, thai, vietnamien, hindi, arabe) : anglais pour CETTE session seulement, avec un
message - le reglage n'est pas modifie (meme regle qu'omega-serv, omega-lib)."""
from __future__ import annotations

from collections.abc import Mapping

from omega_lib.i18n.models import Language, LanguageChoice
from omega_lib.i18n.policies import (
    PSEUDO_LANGUAGE_CODE,
    SOURCE_LANGUAGE_CODE,
    console_fallback_language,
    language_for,
    normalize_language_code,
    ordered_languages,
    resolve_language,
)
from omega_lib.i18n.service import TranslationState

from omega_fire.application.exceptions import UnknownLanguageError
from omega_fire.ports.language_catalog import LanguageCatalogError, LanguageCatalogPort
from omega_fire.ports.settings_store import SettingsStore
from omega_fire.shared.i18n import STATE

LANGUAGE_KEY = "language"
EXPORT_LANGUAGE_KEY = "export_language"
"""Langue des exports HTML/TXT (lot N, Q3) : vide = comme l'interface (comme omega-serv)."""
LANGUAGE_ENV_VAR = "OMEGA_FIRE_LANG"
LANGUAGE_CHANGED_ENV_VAR = "OMEGA_FIRE_LANGUAGE_CHANGED"
"""Pose par app/bootstrap.py juste avant os.execv() : le nouveau processus affiche le splash
de confirmation dans la nouvelle langue."""

INCLUDE_PSEUDO_LANGUAGE = False
"""Langue de controle ⟦…⟧ (plan §4.7), proposee pendant les lots de traduction ; a masquer
(False) a la publication finale, comme omega-serv 2.0.0. Toujours accessible ensuite par
OMEGA_FIRE_LANG=x-test."""

_console_fallback_from: str | None = None


def console_fallback_from() -> str | None:
    """Langue choisie mais remplacee par l'anglais faute de pouvoir l'afficher dans ce terminal
    (signalee une fois a l'ecran), sinon None."""
    return _console_fallback_from


def available_languages(catalog: LanguageCatalogPort) -> list[Language]:
    return ordered_languages(catalog.available(), include_pseudo=INCLUDE_PSEUDO_LANGUAGE)


def select_language(*, settings_store: SettingsStore, catalog: LanguageCatalogPort, language_code: str) -> Language:
    """Enregistre la langue choisie ; appliquee au redemarrage de l'interface."""
    code = normalize_language_code(language_code)
    offered = {language.code: language for language in available_languages(catalog)}
    if code not in offered:
        raise UnknownLanguageError(language_code)
    settings_store.set(LANGUAGE_KEY, "" if code == SOURCE_LANGUAGE_CODE else code)
    return offered[code]


def install_interface_language(
    *, settings_store: SettingsStore, catalog: LanguageCatalogPort, environ: Mapping[str, str],
    state: TranslationState = STATE, terminal_family: str | None = None,
) -> LanguageChoice:
    global _console_fallback_from
    try:
        stored = settings_store.get(LANGUAGE_KEY, "") or ""
    except (OSError, ValueError):
        stored = ""  # reglages illisibles : francais, jamais d'erreur au demarrage
    requested = environ.get(LANGUAGE_ENV_VAR) or stored
    statuses = catalog.available()
    offered = list(statuses) + ([PSEUDO_LANGUAGE_CODE] if INCLUDE_PSEUDO_LANGUAGE else [])
    choice = resolve_language(requested, offered, statuses)
    if terminal_family is not None:
        _console_fallback_from = None
        replacement = console_fallback_language(choice.language.code, terminal_family)
        if replacement is not None and choice.fell_back_from is None:
            _console_fallback_from = choice.language.code
            choice = resolve_language(replacement, offered, statuses)
    return _install_choice(choice, catalog, state)


def _install_choice(choice: LanguageChoice, catalog: LanguageCatalogPort, state: TranslationState) -> LanguageChoice:
    if choice.fell_back_from is None and choice.language.code != SOURCE_LANGUAGE_CODE:
        try:
            translations = catalog.load(choice.language.code)
        except LanguageCatalogError:
            choice = LanguageChoice(language_for(SOURCE_LANGUAGE_CODE), fell_back_from=choice.language.code)
        else:
            state.install(choice.language, translations)
            return choice
    state.install(choice.language, None, fell_back_from=choice.fell_back_from)
    return choice


def select_export_language(*, settings_store: SettingsStore, catalog: LanguageCatalogPort, language_code: str) -> None:
    """Enregistre la langue des exports ; "" = comme l'interface. Effet immediat : chaque
    export lit le reglage au moment ou il est lance."""
    if not language_code:
        settings_store.set(EXPORT_LANGUAGE_KEY, "")
        return
    code = normalize_language_code(language_code)
    if code not in {language.code for language in available_languages(catalog)}:
        raise UnknownLanguageError(language_code)
    settings_store.set(EXPORT_LANGUAGE_KEY, code)


def export_language_override(settings_store: SettingsStore, interface_code: str) -> str | None:
    """Langue a utiliser pour un export, ou None s'il suit la langue de l'interface (reglage
    vide, illisible ou identique)."""
    try:
        code = normalize_language_code(settings_store.get(EXPORT_LANGUAGE_KEY, "") or "")
    except (OSError, ValueError):
        return None
    if not code or code == interface_code:
        return None
    return code


def load_export_language(catalog: LanguageCatalogPort, code: str) -> TranslationState:
    """Etat de traduction de la langue des exports, a passer a shared.i18n.translating_as().
    Leve LanguageCatalogError si le catalogue est absent ou illisible (l'appelant exporte
    alors dans la langue de l'interface et le signale)."""
    state = TranslationState()
    state.install(language_for(code), catalog.load(code))
    return state
