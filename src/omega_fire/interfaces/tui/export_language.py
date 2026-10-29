# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Langue des exports (OMEGA-FIRE_PLAN-DETAILLE_I18N.md, lot N, Q3) cote ecrans.

Un ecran qui exporte appelle `export_translation()` sur le fil de l'interface (lecture du
reglage, chargement du catalogue, avertissement eventuel), puis produit son fichier dans
`with translating_as(etat):` - dans le thread de `run_blocking()` si l'export y tourne.
Tout ce qui est traduit dans ce bloc (textes calcules en Python ET modeles .j2) sort dans
la langue des exports ; les notifications de l'ecran, hors du bloc, restent dans celle de
l'interface. Meme reglage qu'omega-serv, mais sans processus enfant : omega-fire produit
ses exports dans son propre processus."""
from __future__ import annotations

from typing import TYPE_CHECKING

from omega_lib.i18n.policies import language_for
from omega_lib.i18n.service import TranslationState

from omega_fire.application.commands.select_language import export_language_override, load_export_language
from omega_fire.ports.language_catalog import LanguageCatalogError
from omega_fire.shared.i18n import STATE, _

if TYPE_CHECKING:
    from textual.screen import Screen

    from omega_fire.app.dependency_container import DependencyContainer


def export_translation(screen: Screen, container: DependencyContainer) -> TranslationState | None:
    """Langue des exports a appliquer, ou None si l'export suit la langue de l'interface.
    Catalogue illisible : export dans la langue de l'interface, signale a l'ecran."""
    code = export_language_override(container.settings_store, STATE.language.code)
    if code is None:
        return None
    try:
        return load_export_language(container.language_catalog, code)
    except LanguageCatalogError as exc:
        screen.app.notify(
            _("Export dans la langue « {name} » impossible : {error}").format(
                name=language_for(code).native_name, error=exc),
            severity="warning", timeout=10,
        )
        return None
