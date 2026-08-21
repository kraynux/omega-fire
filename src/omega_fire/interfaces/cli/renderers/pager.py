# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Pagination centralisée pour les actions CLI.

Intercepte console.print()/console.input() le temps d'une action pour
accumuler leur sortie dans un buffer, et déclenche une pagination
interactive (barre Début/Précédent/Suivant/Fin/Quitter) uniquement si
le contenu accumulé dépasse la hauteur du terminal — sans que les
fonctions action_X_Y_... aient à en avoir connaissance.

Conforme à la charte Omega-Fire :
- Rendu pur, aucune logique métier.
- Toutes les couleurs passent par theme_registry.get_style(...).
- Pas de dépendance vers domain/, application/, infrastructure/.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator, List

from rich.console import Console, Group, RenderableType
from rich.segment import Segment, Segments
from rich.text import Text

from omega_fire.interfaces.cli import keybindings as kb
from omega_fire.interfaces.cli.renderers.styles import get_terminal_height
from omega_fire.interfaces.cli.themes.registry import theme_registry


class _PagerQuit(Exception):
    """Signal interne : [q] pressé pendant la pagination.

    Remonte jusqu'au context manager paginated() qui l'absorbe
    silencieusement — la suite du code de l'action est simplement
    jamais atteinte, comme un retour anticipé normal (cf. spec 2.3).
    """


_BYPASS_ATTR = "_omega_pager_bypass"


@contextmanager
def bypass_pagination(console: Console) -> Iterator[None]:
    """Suspend le buffering de paginated() pendant toute la durée de vie
    d'un Live() imbriqué (ex: gauge_status()), y compris sa séquence
    d'arrêt.

    console._live_stack ne suffit pas comme signal : Live.stop() appelle
    console.clear_live() (qui vide _live_stack) AVANT son tout dernier
    refresh() et son console.line() de positionnement — ces deux derniers
    appels passaient donc par buffered_print avec _live_stack déjà vide et
    se retrouvaient bufferisés au lieu d'atteindre le terminal. Rich
    restore_cursor() suppose que ce console.line() a bien déplacé le
    curseur d'une ligne ; s'il n'arrive jamais, l'effacement remonte d'une
    ligne de trop et laisse la bordure basse du panel incrustée à l'écran.
    """
    previous = getattr(console, _BYPASS_ATTR, False)
    setattr(console, _BYPASS_ATTR, True)
    try:
        yield
    finally:
        setattr(console, _BYPASS_ATTR, previous)


def _build_nav_bar(page: int, total_pages: int) -> Text:
    key_s = theme_registry.get_style("footer.key")
    label_s = theme_registry.get_style("footer.label")
    sep_s = theme_registry.get_style("footer.separator")

    bar = Text()
    bar.append(f"Page {page}/{total_pages}", style=label_s)

    def _entry(key: str, label: str) -> None:
        bar.append("  │  ", style=sep_s)
        bar.append(key, style=key_s)
        bar.append(f" {label}", style=label_s)

    _entry(kb.KEY_D, kb.LABEL_PAGE_START)
    _entry("◀", "Précédent")
    _entry("▶", "Suivant")
    _entry(kb.KEY_F, kb.LABEL_PAGE_END)
    _entry(kb.KEY_Q, kb.LABEL_QUIT)
    return bar


def _page_segments(lines: List[List[Segment]], start: int, end: int) -> Segments:
    segments: List[Segment] = []
    for line in lines[start:end]:
        segments.extend(line)
        segments.append(Segment.line())
    return Segments(segments)


def _run_pager(console: Console, raw_print: Any, lines: List[List[Segment]], height: int) -> bool:
    """Boucle de pagination interactive. Retourne False si l'utilisateur
    a quitté prématurément (touche [q]), True sinon."""
    page_height = max(height - 2, 1)
    total_pages = max((len(lines) + page_height - 1) // page_height, 1)
    page = 1

    while True:
        console.clear()
        start = (page - 1) * page_height
        end = min(start + page_height, len(lines))
        raw_print(_page_segments(lines, start, end))
        raw_print()
        raw_print(_build_nav_bar(page, total_pages))

        key = kb._getch()
        if kb.is_quit(key):
            return False
        elif kb.is_page_start(key):
            page = 1
        elif kb.is_page_end(key):
            page = total_pages
        elif kb.is_arrow_left(key) or kb.is_arrow_up(key):
            page = max(page - 1, 1)
        elif kb.is_arrow_right(key) or kb.is_arrow_down(key) or kb.is_enter(key) or key == " ":
            # Suivant sur la dernière page = sortie du pager, la suite
            # (input réel ou fin d'action) s'affiche normalement.
            if page >= total_pages:
                return True
            page += 1
        # touche non reconnue : on réaffiche simplement la page courante


def _display(console: Console, raw_print: Any, renderables: List[RenderableType]) -> tuple[bool, bool]:
    """Retourne (completed, was_paginated).

    completed=False signifie une sortie anticipée via [q].
    was_paginated=True signifie que la pagination interactive s'est
    réellement déclenchée (contenu > hauteur du terminal)."""
    content: RenderableType = renderables[0] if len(renderables) == 1 else Group(*renderables)
    height = get_terminal_height()

    lines = console.render_lines(content, console.options)
    if len(lines) <= height:
        raw_print(content)
        return True, False

    return _run_pager(console, raw_print, lines, height), True


@contextmanager
def paginated(console: Console) -> Iterator[Console]:
    """Encadre l'exécution d'une action : bufferise console.print()/
    console.input(), pagine automatiquement au flush si nécessaire.

    Restaure toujours console.print/console.input à la sortie, même en
    cas d'exception.
    """
    original_print = console.print
    original_input = console.input
    buffer: List[RenderableType] = []

    def _flush() -> bool:
        """Retourne True si la pagination interactive s'est réellement
        déclenchée et a été refermée normalement (pas via [q])."""
        if not buffer:
            return False
        pending = list(buffer)
        buffer.clear()
        completed, was_paginated = _display(console, original_print, pending)
        if not completed:
            raise _PagerQuit()
        return was_paginated

    def buffered_print(*objects: Any, **kwargs: Any) -> None:
        if console._live_stack or getattr(console, _BYPASS_ATTR, False):
            # Un Live/Status/Progress est actif sur cette console (ex:
            # ctx.console.status("...", spinner="dots"), gauge_status()) :
            # son thread de rafraîchissement appelle console.print(Control())
            # plusieurs fois par seconde pour s'auto-animer, et sa séquence
            # d'arrêt fait un dernier print+line() après avoir déjà vidé
            # _live_stack (cf. bypass_pagination ci-dessus). Bufferiser ces
            # appels les empêcherait de jamais s'afficher (le spinner
            # resterait invisible) et désynchroniserait l'effacement de
            # Live à la sortie. Ces rendus internes doivent toujours passer
            # en direct, jamais être capturés.
            original_print(*objects, **kwargs)
            return
        if not objects:
            buffer.append(Text(""))
        elif len(objects) == 1:
            buffer.append(objects[0])
        else:
            buffer.append(Group(*objects))

    def buffered_input(prompt: str = "", **kwargs: Any) -> str:
        was_paginated = _flush()
        if was_paginated and not prompt:
            # Seul appel du projet à console.input() sans invite (cf.
            # _execute_action_flow : "Appuyez sur [Entrée] pour revenir
            # au menu...", valeur de retour jamais utilisée). Si la
            # pagination vient d'afficher ce message et a déjà été
            # refermée via Suivant/Entrée/Espace, cet appui compte
            # aussi pour cette saisie — évite un second appui redondant.
            return ""
        if prompt:
            # original_input() est une méthode liée à `console` : son
            # corps fait self.print(prompt, ...), qui résout self.print
            # au moment de l'appel — donc TOUJOURS la version bufferisée
            # actuelle, jamais l'originale, même en passant par la
            # référence "original_input" capturée plus haut. Le prompt
            # se retrouvait donc lui-même piégé dans le buffer au lieu
            # de s'afficher, pendant que la lecture bloquante démarrait
            # déjà — curseur vide, aucune indication visible. On
            # l'affiche donc nous-mêmes via le vrai original_print, puis
            # on lit avec un prompt vide pour éviter un double affichage.
            original_print(prompt, end="")
        return original_input("", password=kwargs.get("password", False), stream=kwargs.get("stream"))

    console.print = buffered_print
    console.input = buffered_input
    try:
        yield console
    except _PagerQuit:
        pass
    finally:
        console.print = original_print
        console.input = original_input
        try:
            _flush()
        except _PagerQuit:
            pass


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Bufferise console.print()/console.input() le temps d'une action CLI
# - Déclenche une pagination interactive uniquement si le contenu
#   accumulé dépasse la hauteur réelle du terminal (comptage via
#   console.render_lines, pas une estimation par \n)
# - Barre de navigation : [d] Début, ◀ Précédent, ▶ Suivant, [f] Fin,
#   [q] Quitter — touches réutilisées de keybindings.py (kb.is_*)
# Pourquoi dans interfaces/cli/renderers/ (charte) :
# - Rendu pur, aucune logique métier
# - Couleurs via theme_registry.get_style (footer.key/label/separator)
# - Pas de dépendance vers domain/, application/, infrastructure/
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier
# ❌ Pas de couleur codée en dur
# ❌ Pas d'appel subprocess
# Points clés :
# - paginated(console) : context manager, point d'entrée unique
# - _PagerQuit : exception interne, absorbée par paginated(), jamais
#   propagée à l'appelant — un [q] en pagination = sortie anticipée
#   silencieuse de l'action, pas une erreur
# - _display() : imprime tel quel si ça tient, pagine sinon
# - _run_pager() : boucle interactive, utilise kb._getch()
# Intégration prévue :
# - interfaces/cli/app.py encadrera child.action(ctx) avec
#   `with paginated(console): child.action(ctx)`, sauf pour les
#   actions à rafraîchissement continu (5.1, 8.1 — exclues explicitement)
#---------------------------------------------------------------------->
