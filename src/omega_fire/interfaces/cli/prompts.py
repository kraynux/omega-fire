# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""User prompts.

Provides user interaction functions for the CLI interface: text input,
confirmations, list selections. Uses rich.prompt for a consistent interface.

This module performs no business logic — only user interaction.
"""
from __future__ import annotations

from typing import Callable, Optional

from rich.console import Console
from rich.prompt import Prompt
from rich.text import Text

from omega_fire.interfaces.cli.themes.registry import theme_registry
from omega_fire.interfaces.exceptions import UserInputError


# ----------------------------------------------------------------------
# Universal cancellation semantics
# ----------------------------------------------------------------------
# Même jeu de mots-clés que les ~10 copies locales de _is_cancel() dans
# interfaces/cli/actions.py — source unique, à terme appelée par elles au
# lieu d'être redéfinie à chaque fonction.
CANCEL_WORDS = ("0", "q", "quit", "annuler", "cancel")


def is_cancel_word(value: str) -> bool:
    """Check whether a raw user input is one of the project's universal
    cancellation keywords (0/q/quit/annuler/cancel, insensible à la casse
    et aux espaces)."""
    return value.strip().lower() in CANCEL_WORDS


# ----------------------------------------------------------------------
# Semantic à deux niveaux (écrans multi-étapes avec boucle)
# ----------------------------------------------------------------------
# Certains écrans (1.5, 7.2, 7.3, 8.2 dans actions.py) distinguent
# volontairement deux sorties : quitter l'écran entièrement (q/quit) vs
# annuler seulement l'étape/le sous-menu en cours et rester dans la
# boucle (0/annuler). CANCEL_WORDS/is_cancel_word() ci-dessus fusionnent
# les deux — inadapté ici sans casser cette distinction. Même source
# unique que ci-dessus, pour ces 4 copies locales identiques.
QUIT_WORDS = ("q", "quit")
STEP_CANCEL_WORDS = ("0", "annuler")


def is_quit_word(value: str) -> bool:
    """Check whether a raw user input requests leaving the current
    multi-step screen entirely (q/quit, insensible à la casse et aux
    espaces)."""
    return value.strip().lower() in QUIT_WORDS


def is_step_cancel_word(value: str) -> bool:
    """Check whether a raw user input requests cancelling only the
    current step of a multi-step screen (0/annuler), without leaving it
    — insensible à la casse et aux espaces."""
    return value.strip().lower() in STEP_CANCEL_WORDS


def _ask_raw(prompt_cls, message, default, console):
    """Exécute un Prompt/IntPrompt Rich sans son ": " automatique.

    Les messages de ce projet incluent déjà leur propre ponctuation
    finale (ex: _info("Choix : "), construits par les helpers _info()/
    _muted() de interfaces/cli/actions.py) — le prompt_suffix par défaut
    de Rich (": ") le dupliquerait sinon ("Choix : : ")."""
    p = prompt_cls(message, console=console)
    p.prompt_suffix = ""
    return p(default=default)


class PromptCancelled(UserInputError):
    """Raised when the user explicitly cancels a prompt (0/q/quit/annuler).

    Distincte d'une UserInputError générique : une annulation n'est pas une
    erreur de saisie, c'est un choix délibéré — les appelants l'attrapent
    séparément pour sortir proprement (return), sans afficher de message
    d'erreur."""

    def __init__(self, prompt_name: str):
        super().__init__(prompt_name=prompt_name, reason="Annulé par l'utilisateur.")


# ----------------------------------------------------------------------
# Prompt Manager Class
# ----------------------------------------------------------------------
class PromptManager:
    """Manager for user prompts in the CLI interface.

    Provides methods for text input. Uses rich.prompt for a consistent
    and user-friendly interface.
    """

    def __init__(self, console: Optional[Console] = None):
        """Initialize the prompt manager.

        Args:
            console: Optional Rich console instance (creates one if None)
        """
        self._console = console or Console()

    def ask_text(
        self,
        message: str,
        default: Optional[str] = None,
        validator: Optional[Callable[[str], bool]] = None,
        error_message: str = "Invalid input",
        allow_cancel: bool = False,
    ) -> str:
        """Ask the user for text input.

        Si allow_cancel est True, une saisie correspondant à un mot-clé
        d'annulation universel (0/q/quit/annuler/cancel) lève
        PromptCancelled avant toute validation — l'appelant l'attrape pour
        sortir proprement, au lieu de traiter le mot-clé comme du texte.
        """
        # Rich traite default=None comme "la vraie valeur par défaut est
        # None" (une saisie vide renverrait alors None, pas ""), pas comme
        # "pas de valeur par défaut" — il faut son propre sentinel (...)
        # pour obtenir le comportement "aucun défaut" attendu ici.
        rich_default = default if default is not None else ...
        try:
            if validator:
                while True:
                    value = _ask_raw(Prompt, message, rich_default, self._console)
                    if allow_cancel and is_cancel_word(value):
                        raise PromptCancelled("text_input")
                    if validator(value):
                        return value
                    self._console.print(f"[red]{error_message}[/red]")
            else:
                value = _ask_raw(Prompt, message, rich_default, self._console)
                if allow_cancel and is_cancel_word(value):
                    raise PromptCancelled("text_input")
                return value
        except PromptCancelled:
            raise
        except Exception as e:
            raise UserInputError(
                prompt_name="text_input",
                reason=str(e),
            ) from e


# ----------------------------------------------------------------------
# Universal pause helper
# ----------------------------------------------------------------------
def pause_prompt(console: Console, message: str = "\n[Entrée] pour continuer...") -> None:
    """Attend un [Entrée] de l'utilisateur, sans rien en faire.

    Même texte que les 3 copies locales _pause() de interfaces/cli/actions.py
    (action_2_7_import_file, action_7_2_restore_state, action_7_3_action_history)
    — source unique, ces trois-là délèguent désormais ici."""
    console.input(Text(message, style=theme_registry.get_style("text.info")))


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Fournit les fonctions de prompt pour l'interface CLI : saisie de
#   texte, avec validation optionnelle et annulation universelle.
# - Ne fait AUCUNE logique métier — uniquement de l'interaction utilisateur.
#
# Pourquoi dans interfaces/cli/ (charte) :
# - C'est de l'interaction utilisateur pure
# - Le domaine ne doit pas connaître les prompts
# - L'application/ ne doit pas connaître les prompts
# - Seul interfaces/ manipule les interactions utilisateur
#
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier (pas de règles de blacklist, politiques)
# ❌ Pas d'appels système (pas de subprocess, pas de backend direct)
# ❌ Pas de dépendance vers domain/, application/ ou infrastructure/
#
# Points clés :
# - CANCEL_WORDS / is_cancel_word() : sémantique d'annulation universelle
#   (0/q/quit/annuler/cancel), même jeu de mots que les copies locales
#   _is_cancel() de interfaces/cli/actions.py — source unique, appelée
#   par 15 fonctions migrées (référentiel §32).
# - QUIT_WORDS / is_quit_word() + STEP_CANCEL_WORDS / is_step_cancel_word() :
#   variante à deux niveaux pour les écrans multi-étapes en boucle (1.5,
#   7.2, 7.3, 8.2) où « quitter l'écran » (q/quit) et « annuler l'étape
#   en cours » (0/annuler) sont volontairement distincts.
# - PromptCancelled(UserInputError) : levée par ask_text() quand
#   allow_cancel=True et que l'utilisateur annule ; à attraper
#   séparément d'UserInputError (annulation != erreur).
# - PromptManager.ask_text() : seule méthode réellement utilisée par le
#   projet (51 appels dans actions.py) — allow_cancel=True intercepte le
#   mot-clé d'annulation avant toute validation.
# - pause_prompt() : source unique pour les 3 copies locales _pause().
#
# Historique — ask_int()/ask_confirm()/ask_choice()/ask_ip()/ask_backend()/
# ask_format()/ask_log_path() et tout le cluster d'épinglage de chemins de
# logs (_get_pinned_log_paths, _manage_pinned_paths, _prompt_manual_path,
# prompt_log_path_selection, create_prompt_manager...) ont été supprimés
# le 2026-08-17 (référentiel §42) : zéro appelant réel confirmé par grep
# exhaustif pour chacun dans tout le projet. ask_log_path() décrivait un
# plan de sélection de log jamais réalisé — 5.1/5.2 utilisent en réalité
# un mécanisme entièrement différent et séparé (ManageLiveTailPinsCommand,
# référentiel §20).
#---------------------------------------------------------------------->
