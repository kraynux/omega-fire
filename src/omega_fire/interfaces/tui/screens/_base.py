# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Classe de base partagee par tous les ecrans navigables (retour clavier).
Portee verbatim depuis omega-check (D-008), etendue de `run_blocking()`
(retour utilisateur reel post-migration, voir DECISIONS_ARCHITECTURE.md) :
tout appel synchrone lent (fail2ban-client, subprocess, I/O disque) execute
dans un handler Textual bloque l'INTEGRALITE de l'app (event loop unique),
pas seulement l'ecran courant — contrairement au CLI Rich (boucle bloquante
mono-ecran, un gel y etait juste une attente). `run_blocking()` deplace le
travail dans un thread (`Screen.run_worker(thread=True)`) et notifie
l'utilisateur pendant l'attente plutot que de laisser l'app paraitre figee."""
from __future__ import annotations

from typing import Callable, ClassVar, TypeVar

from textual.binding import Binding, BindingType
from textual.screen import Screen

from omega_fire.interfaces.cli.help_text import HelpEntry, get_help_entry

ResultT = TypeVar("ResultT")


def format_help_entry(entry: HelpEntry) -> str:
    """Rendu texte (markup Rich, consomme par Static) d'une HelpEntry —
    meme contenu que interfaces/cli/app.py::_build_help_body() pour le
    CLI, formate ici pour le TUI. Vit dans _base.py (pas dans
    help_text.py) : ce dernier ne contient explicitement aucun rendu
    Rich, seulement des donnees texte (voir son propre docstring)."""
    parts = [entry.summary]
    if entry.usage:
        parts.append("[b]Comment l'utiliser :[/b]\n" + "\n".join(f"  - {u}" for u in entry.usage))
    if entry.consequences:
        parts.append("[b]Consequences :[/b]\n" + "\n".join(f"  - {c}" for c in entry.consequences))
    if entry.warnings:
        parts.append("[b]A savoir :[/b]\n" + "\n".join(f"  - {w}" for w in entry.warnings))
    if entry.mechanism:
        parts.append(f"[dim]{entry.mechanism}[/dim]")
    if entry.see_also:
        parts.append(f"[dim]Voir aussi : {', '.join(entry.see_also)}[/dim]")
    return "\n\n".join(parts)


class OmegaScreen(Screen[None]):
    """Ecran navigable standard : ajoute `echap` -> retour, sans qu'aucun
    ecran n'ait a redeclarer son propre binding. `home.py` et
    `quit_confirm.py` n'en heritent pas (voir leurs propres fichiers)."""

    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("escape", "back", "Retour", show=True),
        Binding("up", "focus_previous_item", "Monter", show=False),
        Binding("down", "focus_next_item", "Descendre", show=False),
    ]

    # Identifiant de noeud de menu CLI (ex. "4.2") — jamais defini ici,
    # pose par SectionScreen juste apres avoir instancie l'ecran via
    # SectionItem.screen_factory (voir section_screen.py), pour que
    # help_content() ci-dessous puisse retrouver le contenu d'aide
    # DETAILLE deja redige pour le CLI (interfaces/cli/help_text.py,
    # 61 noeuds couverts) sans avoir a le reecrire ni a modifier
    # individuellement chacun des ~52 ecrans d'action. Retour
    # utilisateur reel : l'aide contextuelle (touche `a`) etait devenue
    # generique sur les ecrans d'action apres la migration Textual, alors
    # que le CLI avait une aide detaillee par sous-section (fonction,
    # utilite, mode d'emploi) — regression de contenu, pas seulement de
    # presentation.
    node_id: str | None = None

    def action_back(self) -> None:
        self.dismiss()

    def action_focus_previous_item(self) -> None:
        self.focus_previous()

    def action_focus_next_item(self) -> None:
        self.focus_next()

    def help_content(self) -> tuple[str, str] | None:
        """Contenu d'aide propre a cet ecran (titre, corps), affiche en
        tete de HelpScreen quand la touche `a` est pressee ICI. Par
        defaut, cherche une HelpEntry detaillee via `self.node_id` (voir
        plus haut) ; None si `node_id` n'est pas renseigne ou si aucune
        entree n'existe pour lui — HelpScreen affiche alors seulement la
        reference generique. Redefini par SectionScreen (aide de section
        + liste des actions) et HomeScreen (aide du menu principal)."""
        if self.node_id:
            entry = get_help_entry(self.node_id)
            if entry is not None:
                return f"Action {self.node_id}", format_help_entry(entry)
        return None

    def run_blocking(
        self,
        fn: Callable[[], ResultT],
        on_success: Callable[[ResultT], None],
        *,
        busy_message: str | None = "Operation en cours...",
        on_error: Callable[[Exception], None] | None = None,
    ) -> None:
        """Execute `fn()` dans un thread (jamais sur le thread UI), puis
        rappelle `on_success(resultat)` (ou `on_error(exception)`) sur le
        thread principal via `App.call_from_thread` — obligatoire, toute
        manipulation de widget doit rester sur le thread UI. Notifie
        `busy_message` immediatement pour que l'utilisateur sache que
        l'app travaille plutot que de la croire figee — `None` (ou chaine
        vide) desactive la notification, pour un rafraichissement
        periodique silencieux (ex. dashboard_screen.py::set_interval) ou
        une notification recurrente serait juste du bruit."""
        if busy_message:
            self.app.notify(busy_message, timeout=3)

        def _work() -> None:
            try:
                result = fn()
            except Exception as e:  # noqa: BLE001 - relaye a on_error/notify, jamais avale silencieusement
                self.app.call_from_thread(self._run_blocking_error, e, on_error)
                return
            self.app.call_from_thread(on_success, result)

        self.run_worker(_work, thread=True)

    def _run_blocking_error(self, error: Exception, on_error: Callable[[Exception], None] | None) -> None:
        if on_error is not None:
            on_error(error)
        else:
            self.app.notify(f"Erreur : {error}", severity="error")
