# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Titres d'action de l'historique d'audit, affiches dans la langue active (retour
utilisateur 2026-10-28 : export d'audit en arabe montrant des titres en francais et en
polonais).

L'historique garde le titre tel qu'il a ete ecrit - en francais, et relu par le code
(report_builder compare les titres) : on ne le reecrit jamais. On le traduit a l'affichage :

1. le titre entier est une phrase traduisible (ex. « RAPPORT STATISTIQUE — 30 JOURS ») ;
2. sinon, titre numerote « 5.7 Nettoyage Avance » : le numero designe une action du menu,
   dont le libelle (deja traduit) remplace le texte enregistre. Pour un numero dont le sens a
   change (menu 5 renumerote en 3.5, retour utilisateur 2026-10-28), seulement si le texte
   enregistre correspond a ce libelle (sans accents ni casse) ; sinon le texte enregistre est
   reconnu parmi les libelles connus (actuels ou anciens) et garde son numero d'origine ;
3. sinon, titre deja traduit dans une autre langue (8.3/8.4 ecrivaient le titre traduit
   avant le 2026-10-28) : on retrouve la phrase source dans les catalogues ;
4. sinon : affiche tel quel."""
from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable, Iterable, Mapping

from omega_fire.shared.i18n import _

_NUMBERED = re.compile(r"^(\d+(?:\.\d+)*)\s+(.+)$", re.S)


def _normalized(text: str) -> str:
    """Comparaison de libelles : sans accents, casse ni espaces multiples (les titres ecrits
    avant la reecriture accentuee sont sans accents : « Nettoyage Avance »)."""
    decomposed = unicodedata.normalize("NFKD", text)
    plain = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(plain.casefold().split())


class ActionTitleTranslator:
    def __init__(
        self,
        menu_labels: Mapping[str, str],
        catalog_codes: Callable[[], Iterable[str]],
        catalog_phrases: Callable[[str], Mapping[str, str]],
        renumbered: Mapping[str, Iterable[str]] | None = None,
        aliases: Mapping[str, str] | None = None,
    ) -> None:
        """menu_labels : numero d'action -> libelle source (N_) ; renumbered : numeros dont le
        sens a change -> anciens libelles source (N_) ; les catalogues ne sont lus qu'au premier
        titre qui en a besoin. aliases : texte d'un titre enregistre (sans numero) -> libelle
        source, pour les titres courts ecrits par les ecrans ou par --legacy-cli
        (« Rotation & Backup Logs » -> « Rotation / Backup des logs »)."""
        self._menu_labels = dict(menu_labels)
        self._renumbered = {number: tuple(labels) for number, labels in (renumbered or {}).items()}
        known = list(self._menu_labels.values()) + [l for ls in self._renumbered.values() for l in ls]
        self._label_of = {_normalized(label): label for label in known}
        self._label_of.update({_normalized(alias): label for alias, label in (aliases or {}).items()})
        self._catalog_codes = catalog_codes
        self._catalog_phrases = catalog_phrases
        self._sources: set[str] | None = None
        self._source_of: dict[str, str] = {}

    def _load(self) -> None:
        sources: set[str] = set()
        source_of: dict[str, str] = {}
        for code in sorted(self._catalog_codes()):
            for source, translated in self._catalog_phrases(code).items():
                sources.add(source)
                if translated != source:
                    source_of.setdefault(translated, source)
        self._sources, self._source_of = sources, source_of

    def __call__(self, stored: str) -> str:
        if self._sources is None:
            self._load()
        assert self._sources is not None
        if stored in self._sources:
            return _(stored)
        numbered = _NUMBERED.match(stored)
        if numbered:
            number, text = numbered.group(1), numbered.group(2)
            current = self._menu_labels.get(number)
            if current is not None and (number not in self._renumbered
                                        or _normalized(text) == _normalized(current)):
                return f"{number} {_(current)}"
            label = self._label_of.get(_normalized(text))
            if label is not None:
                return f"{number} {_(label)}"
        source = self._source_of.get(stored)
        return _(source) if source is not None else stored


def menu_labels_by_action(sections: Mapping[str, tuple[str, Iterable]]) -> dict[str, str]:
    """Numero d'action -> libelle source, depuis section_registry.SECTIONS."""
    return {item.action_id: item.label for _title, items in sections.values() for item in items}
