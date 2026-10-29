# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Catalogues de traduction de l'interface (OMEGA-FIRE_PLAN-DETAILLE_I18N.md §5)."""
from __future__ import annotations

import gettext
from typing import Protocol

from omega_lib.i18n.models import LanguageStatus


class LanguageCatalogError(Exception):
    """Catalogue present mais illisible, ou absent."""


class LanguageCatalogPort(Protocol):
    def available(self) -> dict[str, LanguageStatus]:
        """Langues dont le catalogue est present (sans le francais, toujours disponible)."""
        ...

    def load(self, code: str) -> gettext.NullTranslations | None:
        """None pour le francais ; LanguageCatalogError si le catalogue manque ou est illisible."""
        ...
