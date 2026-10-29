# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Guide d'aide centralise (version 3.5, decision utilisateur 2026-10-28 : « comme
omega-serv »). Tout est traduit A L'APPEL de guide_pages() (fiches et titres sont des
textes sources marques) : appele sous translating_as(), le guide sort dans la langue des
exports. Rassemble en un seul parcours les aides deja redigees — fiche de chaque
section et de chaque action (interfaces/cli/help_text.py, la meme que la touche `a`),
accueil, raccourcis clavier, reglages — dans l'ordre reel des menus
(section_registry.SECTIONS). Aucun texte d'aide n'est duplique ici : une fiche modifiee
dans help_text.py l'est partout (touche `a`, guide, export HTML)."""
from __future__ import annotations

from dataclasses import dataclass, field

from omega_fire.interfaces.cli.help_text import HelpEntry, get_help_entry
from omega_fire.interfaces.tui.section_registry import SECTIONS
from omega_fire.shared.i18n import _


@dataclass(frozen=True)
class GuidePage:
    page_id: str            # "home", "shortcuts", "settings", "1", "1.1"…
    section: str            # titre de la section (colonne du menu du guide)
    title: str
    entry: HelpEntry | None = None
    text: str = ""          # repli quand aucune fiche n'est redigee
    lines: tuple[tuple[str, str], ...] = field(default_factory=tuple)   # raccourcis


def shortcuts() -> tuple[tuple[str, str], ...]:
    return (
        (_("Haut / Bas"), _("Naviguer entre les éléments d'un écran")),
        (_("Tab / Maj+Tab"), _("Naviguer entre les champs d'un formulaire")),
        (_("Échap"), _("Retour à l'écran précédent (confirmation de sortie sur l'accueil)")),
        ("t", _("Thème suivant (appliqué immédiatement, sans confirmation)")),
        ("r", _("Rafraîchir la détection du terminal")),
        ("a", _("Aide de l'écran courant (fiche de la section ou de l'action)")),
        ("s", _("Réglages")),
        ("q", _("Quitter (avec confirmation)")),
    )


def guide_pages() -> list[GuidePage]:
    general = _("Général")
    pages = [
        GuidePage("home", general, _("Menu principal"), text=_(
            "Choisissez une section (1-8), Réglages (9) ou ce guide (10). Dans chaque section, "
            "la touche `a` affiche la fiche de toutes ses actions ; dans un écran d'action, "
            "la fiche de cette action. Ce guide rassemble toutes ces fiches au même endroit.")),
        GuidePage("shortcuts", general, _("Raccourcis clavier"), lines=shortcuts()),
    ]
    for section_id, (section_title, items) in SECTIONS.items():
        section_name = _(section_title)   # titre source marque (N_), traduit dans la langue active
        pages.append(GuidePage(section_id, section_name, _("{id}. Vue d'ensemble").format(id=section_id),
                               entry=get_help_entry(section_id)))
        for item in items:
            pages.append(GuidePage(
                item.action_id, section_name, f"{item.action_id} {_(item.label)}",
                entry=get_help_entry(item.action_id), text=item.description,
            ))
    pages.append(GuidePage("settings", _("RÉGLAGES"), _("9. Réglages"), text=_(
        "Langue de l'interface et des exports, thème, profil d'affichage, dossiers des exports "
        "et des captures d'écran, et leur purge. Accessible aussi par la touche `s` depuis "
        "n'importe quel écran.")))
    return pages


def page_by_id(page_id: str, pages: list[GuidePage] | None = None) -> GuidePage | None:
    return next((page for page in (pages or guide_pages()) if page.page_id == page_id), None)
