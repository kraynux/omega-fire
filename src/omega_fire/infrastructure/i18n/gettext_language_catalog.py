# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Catalogues gettext livres avec omega-fire (src/omega_fire/locale/), lus via omega-lib."""
from __future__ import annotations

import gettext
from pathlib import Path

from omega_lib.i18n.models import LanguageStatus
from omega_lib.infrastructure.i18n.gettext_catalogs import (
    SHARED_DOMAIN,
    SHARED_LOCALE_DIR,
    CatalogError,
    discover_catalogs,
    load_translations,
)

from omega_fire.ports.language_catalog import LanguageCatalogError
from omega_fire.shared.i18n import DOMAIN

DEFAULT_LOCALE_DIR = Path(__file__).resolve().parents[2] / "locale"


class GettextLanguageCatalog:
    """Implemente ports/language_catalog.py::LanguageCatalogPort."""

    def __init__(self, locale_dir: Path = DEFAULT_LOCALE_DIR, domain: str = DOMAIN) -> None:
        self._locale_dir = locale_dir
        self._domain = domain

    def available(self) -> dict[str, LanguageStatus]:
        return discover_catalogs(self._locale_dir, self._domain)

    def load(self, code: str) -> gettext.NullTranslations | None:
        """Catalogue d'omega-fire, chaine au catalogue partage omega-lib s'il existe (2026-11-09 :
        phrases des ecrans partages, ex. Contact et support). Le catalogue d'omega-fire reste
        OBLIGATOIRE (langue absente ou illisible : refusee, comme avant) et l'emporte toujours."""
        try:
            translations = load_translations(self._locale_dir, self._domain, code)
        except CatalogError as e:
            raise LanguageCatalogError(str(e)) from e
        if translations is not None:
            try:
                shared = load_translations(SHARED_LOCALE_DIR, SHARED_DOMAIN, code)
            except CatalogError:
                shared = None  # catalogue partage absent ou illisible : omega-fire seul, comme avant
            if shared is not None:
                translations.add_fallback(shared)
        return translations

    def translated_phrases(self, code: str) -> dict[str, str]:
        """Phrases source -> traduction d'un catalogue (sans pluriels ni en-tete) ; {} si le
        catalogue est absent ou illisible. Sert a reconnaitre un texte deja traduit (titres
        d'action ecrits dans l'historique dans une autre langue, avant 2026-10-28)."""
        try:
            translations = self.load(code)
        except LanguageCatalogError:
            return {}
        phrases = getattr(translations, "_catalog", {}) or {}
        return {k: v for k, v in phrases.items() if isinstance(k, str) and k and v}
