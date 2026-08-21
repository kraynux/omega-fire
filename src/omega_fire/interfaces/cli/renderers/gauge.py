# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Jauge animée pour les actions à latence — remplace console.status().

Le spinner "dots" intégré de Rich (utilisé partout ce soir avant ce
fichier) est trop discret pour signaler clairement qu'un scan réel est
en cours. Cette jauge va-et-vient (effet « scanner »/KITT), enveloppée
dans une boîte de dialogue compacte et centrée — même style que le
dialogue de confirmation de sortie (action_quit) — est plus visible
qu'une simple ligne collée en haut de l'écran. Couleurs entièrement
pilotées par theme_registry.

Conforme à la charte Omega-Fire :
- Rendu pur, aucune logique métier.
- Toutes les couleurs passent par theme_registry.get_style(...).
- Pas de dépendance vers domain/, application/, infrastructure/.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from rich import box
from rich.align import Align
from rich.console import Console, ConsoleOptions, Group, RenderResult
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from omega_fire.interfaces.cli.renderers.pager import bypass_pagination
from omega_fire.interfaces.cli.renderers.styles import get_terminal_width
from omega_fire.interfaces.cli.themes.registry import theme_registry

DEFAULT_FILL_WIDTH = 6
DEFAULT_SPEED = 18.0  # positions par seconde — ~2s pour un aller-retour complet
DIALOG_WIDTH = 46
PATIENCE_LABEL = "Veuillez patienter..."


class AnimatedGauge:
    """Renderable Rich : boîte de dialogue avec jauge indéterminée qui
    va-et-vient, sur le modèle du dialogue de confirmation de sortie
    (action_quit) — message en haut, jauge au centre, "Veuillez
    patienter..." en dessous, le tout dans un Panel arrondi centré.

    Même mécanisme que rich.spinner.Spinner (une seule instance,
    réutilisée à chaque frame — __rich_console__ recalcule la position
    à partir de console.get_time(), pas d'état mutable partagé entre
    threads à gérer soi-même) : le thread de rafraîchissement de
    Live() ré-appelle __rich_console__ à chaque tick, qui recalcule
    simplement une nouvelle position à partir du temps écoulé.
    """

    def __init__(
        self,
        message: str,
        fill_width: int = DEFAULT_FILL_WIDTH,
        speed: float = DEFAULT_SPEED,
        dialog_width: int = DIALOG_WIDTH,
    ):
        self.message = message
        self.fill_width = fill_width
        self.speed = speed
        self.dialog_width = dialog_width
        self._start_time: float | None = None

    def _bar_width(self) -> int:
        # Largeur intérieure du panel (bordures + padding) moins une
        # petite marge, pour que la jauge ne touche jamais les bords.
        return max(self.dialog_width - 8, self.fill_width + 4)

    def _position(self, elapsed: float, span: int) -> int:
        span = max(span, 1)
        cycle = span * 2
        t = (elapsed * self.speed) % cycle
        return int(t) if t <= span else int(cycle - t)

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        if self._start_time is None:
            self._start_time = console.get_time()
        elapsed = console.get_time() - self._start_time

        bar_width = self._bar_width()
        span = bar_width - self.fill_width
        pos = self._position(elapsed, span)

        track_style = theme_registry.get_style("border.default")
        fill_style = theme_registry.get_style("border.accent")
        heading_style = theme_registry.get_style("text.heading")
        muted_style = theme_registry.get_style("text.muted")

        bar = Text()
        for i in range(bar_width):
            if pos <= i < pos + self.fill_width:
                bar.append("▓", style=fill_style)
            else:
                bar.append("░", style=track_style)

        panel_width = min(self.dialog_width, max(get_terminal_width() - 10, 30))

        content = Group(
            Align.center(Text(self.message, style=heading_style)),
            Text(""),
            Align.center(bar),
            Text(""),
            Align.center(Text(PATIENCE_LABEL, style=muted_style)),
        )

        panel = Panel(
            content,
            border_style=fill_style,
            box=box.ROUNDED,
            padding=(1, 2),
            width=panel_width,
        )

        # Un seul renderable cédé, hauteur constante d'une frame à
        # l'autre — Live() en a besoin pour effacer proprement la zone
        # transitoire à la sortie. Le décalage vertical par rapport au
        # haut de l'écran est géré hors de Live() (cf. gauge_status),
        # pas ici : un second yield pour une simple ligne vide rendait
        # ce calcul de hauteur incohérent et laissait la bordure basse
        # du panel incrustée à l'écran après la fin de l'animation.
        yield Align.center(panel)


@contextmanager
def gauge_status(
    console: Console,
    message: str,
    fill_width: int = DEFAULT_FILL_WIDTH,
    speed: float = DEFAULT_SPEED,
    dialog_width: int = DIALOG_WIDTH,
) -> Iterator[None]:
    """Remplacement direct de `console.status(message, spinner="dots")`.

    Même usage : `with gauge_status(console, "Scan en cours...") : ...`.
    S'anime seule pendant tout appel bloquant à l'intérieur du `with`
    (Live() gère son propre thread de rafraîchissement en tâche de
    fond, exactement comme console.status() le fait déjà en interne).

    Le décalage vertical (marge avant la boîte) est imprimé ici, une
    fois, avant l'entrée dans Live() — donc hors de la zone que Live()
    efface à la sortie (transient=True).

    bypass_pagination() encadre tout le cycle de vie du Live (pas
    seulement pendant que console._live_stack est non vide) : la
    séquence d'arrêt de Live fait un dernier print + line() après avoir
    déjà vidé _live_stack, et paginated() (app.py) bufferisait ces
    derniers appels au lieu de les laisser atteindre le terminal — ce
    qui désynchronisait le calcul d'effacement de Live et laissait la
    bordure basse du panel incrustée à l'écran (cf. pager.py).
    """
    gauge = AnimatedGauge(message, fill_width=fill_width, speed=speed, dialog_width=dialog_width)
    console.print()
    with bypass_pagination(console):
        with Live(gauge, console=console, refresh_per_second=18, transient=True):
            yield


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Boîte de dialogue animée (jauge « va-et-vient », effet scanner) qui
#   remplace le spinner "dots" trop discret de Rich pour les actions à
#   latence perceptible.
# - gauge_status(console, message) : context manager, API identique à
#   console.status(message, spinner="dots") pour une substitution
#   directe partout où ce dernier est utilisé.
#
# Pourquoi dans interfaces/cli/renderers/ (charte) :
# - Rendu pur, aucune logique métier.
# - Couleurs via theme_registry (border.default/border.accent/
#   text.heading/text.muted).
# - Pas de dépendance vers domain/, application/, infrastructure/.
#
# Ce qu'il ne contient PAS :
# ❌ Pas de couleur codée en dur
# ❌ Pas d'appel subprocess
# ❌ Pas de thread/minuterie manuelle (Live() s'en charge, comme Spinner)
#
# Points clés :
# - AnimatedGauge : renderable Rich, __rich_console__ recalcule sa
#   position à partir de console.get_time() à chaque frame — même
#   mécanisme que rich.spinner.Spinner (confirmé par lecture de son
#   code source), pas une réinvention.
# - Boîte de dialogue compacte et centrée (Panel + box.ROUNDED), même
#   style que action_quit() (confirmation de sortie) — message en
#   haut, jauge au centre, "Veuillez patienter..." en dessous, léger
#   décalage vertical avant la boîte (jamais collée en haut d'écran).
# - DEFAULT_FILL_WIDTH=6, DEFAULT_SPEED=18 : un aller-retour complet
#   dure ~2s — assez rapide pour donner l'impression d'un scan réel
#   sans être distrayant.
#---------------------------------------------------------------------->
