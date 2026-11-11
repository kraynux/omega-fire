# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 8.6 — Visualiser les logs serveurs avec lnav. Meme selection de
source qu'action_8_6_lnav_analysis (epingles/historique/saisie manuelle,
multi-selection par NUMEROS separes par des virgules — meme convention
que le CLI, voir plus bas), lancement via `App.suspend()` (Phase 5 de la
feuille de route) — mais l'ENCAPSULATION elle-meme reste celle du CLI
(interfaces/cli/renderers/lnav_live.py::render_lnav_live(), PTY+pyte,
header/footer Omega-Fire persistants, Ctrl-Q pour revenir), pas un
`subprocess.run()` brut. Un essai precedent de cet ecran appelait lnav
directement (sans passer par render_lnav_live) : retour utilisateur
reel, ca affichait lnav "en mode brut" sans le header/footer/raccourcis
Omega-Fire, avec les propres raccourcis de lnav telescopant ceux
d'Omega-Fire, et SURTOUT plus aucun moyen de revenir a l'appli sans
Ctrl-C + quitter tout le processus — exactement le probleme que
render_lnav_live() (deja ecrit, deja valide empiriquement, voir son
propre docstring) resout depuis le depart. `App.suspend()` reste
necessaire (rend la main du terminal a render_lnav_live(), qui gere
elle-meme le mode raw et le retour), mais c'est un changement de
mecanisme de handoff, pas un remplacement de l'encapsulation.

Reconception (selection/epinglage, independante de ce qui precede) suite
a un autre retour utilisateur reel : la premiere version
accumulait les CHEMINS COMPLETS directement dans le champ source au clic
sur une ligne, le MEME champ servant aussi a l'epinglage — ambigu ("ca
melange les epingles et les saisies") et incapable de distinguer "je
veux fusionner ces 2 fichiers pour CETTE session" de "je veux epingler
CE fichier sous un nom" (le modele de donnees d'une epingle est name->UN
SEUL chemin, ManageLiveTailPinsCommand.add_pinned(name, path) ; vouloir
epingler 2 chemins sous un seul nom n'a jamais ete supporte, la version
precedente le laissait croire a tort — "il enregistre pas deux chemins
sur une meme epingle").

Nouvelle repartition, calquee sur le CLI (qui tapait deja des NUMEROS
separes par des virgules referencant le tableau affiche, cf.
action_8_6_lnav_analysis) :
- Un champ "Sources a fusionner" recoit des NUMEROS de ligne (courts,
  jamais de confusion de virgules dans un chemin) et/ou des chemins
  manuels, pour LANCER lnav sur plusieurs fichiers a la fois.
- Cliquer une ligne (RowHighlighted, cursor_type="row" — voir on_mount)
  ajoute juste SON NUMERO a ce champ, et retient la ligne comme "en
  surbrillance" pour Epingler/Retirer.
- Epingler/Retirer n'operent JAMAIS sur la fusion multiple : toujours
  UN SEUL chemin (celui de la ligne en surbrillance, ou le 1er token du
  champ de fusion s'il s'agit d'un chemin manuel), avec un nom separe."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, DataTable, Footer, Header, Input, Static

from omega_fire.application.commands.manage_live_tail_pins import ManageLiveTailPinsCommand
from omega_fire.infrastructure.config.paths import LOGS_DIR, RUNTIME_DIR
from omega_fire.infrastructure.storage.files.json_store import JsonStore
from omega_fire.interfaces.cli.renderers.lnav_live import render_lnav_live
from omega_fire.interfaces.cli.themes import initialize_theme, theme_registry
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.support.action_audit import log_action_result
from omega_fire.interfaces.tui.support.terminal_handoff import suspended_terminal
from omega_fire.interfaces.tui.screens._log_sources import library_paths
from omega_fire.shared.i18n import _

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ACTION_TITLE = "8.6 Visualiser les logs serveurs (lnav)"

# Plus d'epingles par defaut codees en dur (retour utilisateur 2026-10-28), comme le Live Tail.
_DEFAULT_LNAV_PINS: dict[str, str] = {}


class LnavScreen(OmegaScreen):
    """8.6 — selection multi-fichiers (par numeros) puis analyse via lnav (App.suspend())."""

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container
        self._command = ManageLiveTailPinsCommand(
            JsonStore(RUNTIME_DIR),
            defaults=_DEFAULT_LNAV_PINS,
            custom_relative_path="lnav_custom_pins.json",
            disabled_relative_path="lnav_disabled_pins.json",
            history_relative_path="lnav_history.json",
        )
        self._display_items: dict[str, dict] = {}
        self._highlighted_key: str | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="omega-panel"):
            yield Static(_("VISUALISER LES LOGS SERVEURS AVEC LNAV"), classes="omega-title")
            yield Static(
                _("Cliquez une ligne pour ajouter son numéro au champ de fusion "
                "ci-dessous (lnav fusionne automatiquement plusieurs fichiers)."),
                classes="omega-hint",
            )
            yield DataTable(id="sources-table")

            yield Static(_("Sources à fusionner (numéros ci-dessus et/ou chemins manuels, séparés par des virgules)"), classes="omega-subtitle")
            yield Input(placeholder=_("ex: 1,3 ou /chemin/manuel.log"), id="merge-input")

            yield Static(_("Épingler (toujours UNE seule source : la ligne en surbrillance, ou le 1er élément ci-dessus)"), classes="omega-subtitle")
            yield Input(placeholder=_("Nom de l'épingle"), id="pin-name-input")

            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Lancer lnav"), id="launch", variant="primary")
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Épingler"), id="pin")
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Retirer (ligne en surbrillance)"), id="unpin", variant="error")
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Purger tout"), id="purge", variant="error")
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Retour"), id="back")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#sources-table", DataTable)
        # cursor_type par defaut = "cell" : DataTable.RowHighlighted (ecoute
        # par on_data_table_row_highlighted plus bas) n'est POSTE que si
        # cursor_type == "row" — sans ceci, le curseur bouge visuellement
        # au clic mais l'evenement n'est jamais emis (retour utilisateur
        # reel : rien ne se selectionnait jamais).
        table.cursor_type = "row"
        table.add_columns("#", _("Type"), _("Nom"), _("Chemin"))
        self._refresh_sources_table()

    def _refresh_sources_table(self) -> None:
        table = self.query_one("#sources-table", DataTable)
        table.clear()
        self._display_items = {}
        idx = 1

        # Logs de la Bibliotheque (5.1) en tete (2026-11-09 : « 8.5 et 8.6 doivent aussi etre alimentes par la
        # Bibliotheque ») ; les epingles et l'historique (raccourcis manuels d'origine) suivent.
        pinned_paths = set(self._command.list_active_pinned().values())
        for lib_path in library_paths():
            if lib_path in pinned_paths:
                continue
            key = str(idx)
            self._display_items[key] = {"type": "library", "name": _("Bibliothèque"), "path": lib_path}
            table.add_row(key, _("Bibliothèque"), Path(lib_path).name, lib_path, key=key)
            idx += 1

        for name, path in self._command.list_active_pinned().items():
            key = str(idx)
            self._display_items[key] = {"type": "pinned", "name": name, "path": path}
            sub_paths = [p.strip() for p in path.split(",") if p.strip()]
            display_name = name if len(sub_paths) <= 1 else _("{name} ({count} fichiers)").format(name=name, count=len(sub_paths))
            table.add_row(key, _("Épingle"), display_name, path, key=key)
            idx += 1

        for h_path in self._command.list_history()[:5]:
            key = str(idx)
            self._display_items[key] = {"type": "history", "name": _("Historique récent"), "path": h_path}
            table.add_row(key, _("Historique"), _("Historique récent"), h_path, key=key)
            idx += 1

        # Le curseur du tableau demarre automatiquement sur la 1ere ligne
        # (deja "en surbrillance") : cliquer PRECISEMENT cette ligne ne
        # declenche aucun RowHighlighted (la coordonnee ne change pas).
        # Synchronise le champ de fusion et la cible Epingler/Retirer avec
        # cette 1ere ligne des l'ouverture, pour rester coherent avec ce
        # que la surbrillance affiche deja.
        if self._display_items and not self.query_one("#merge-input", Input).value.strip():
            first_key = next(iter(self._display_items))
            self._highlighted_key = first_key
            self.query_one("#merge-input", Input).value = first_key

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.data_table.id != "sources-table":
            return
        key = str(event.row_key.value)
        if key not in self._display_items:
            return
        self._highlighted_key = key
        merge_input = self.query_one("#merge-input", Input)
        existing = [t.strip() for t in merge_input.value.split(",") if t.strip()]
        if key not in existing:
            existing.append(key)
        merge_input.value = ", ".join(existing)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "back":
            self.dismiss()
            return
        if button_id == "launch":
            self._launch()
            return
        if button_id == "pin":
            self._pin()
            return
        if button_id == "unpin":
            self._unpin()
            return
        if button_id == "purge":
            self._purge()

    def _resolve_token(self, token: str) -> list[str]:
        """Un token du champ de fusion est soit un NUMERO de ligne
        (reference vers _display_items — dont le chemin peut lui-meme
        contenir plusieurs fichiers si epingle en tant que groupe, voir
        _pin() plus bas), soit directement un chemin/URL manuel — jamais
        ambigu, un numero de ligne ne ressemble a aucun chemin
        plausible."""
        item = self._display_items.get(token)
        raw_path = item["path"] if item is not None else token
        return [p.strip() for p in raw_path.split(",") if p.strip()]

    def _current_merge_paths(self) -> list[str]:
        """Chemins reels actuellement selectionnes pour la fusion
        (dedupliques, ordre de saisie), toutes origines confondues
        (numeros de ligne et/ou chemins manuels)."""
        raw = self.query_one("#merge-input", Input).value.strip()
        tokens = [t.strip() for t in raw.split(",") if t.strip()]
        paths: list[str] = []
        for t in tokens:
            for p in self._resolve_token(t):
                if p not in paths:
                    paths.append(p)
        return paths

    def _pin(self) -> None:
        name = self.query_one("#pin-name-input", Input).value.strip()
        if not name:
            self.app.notify(_("Saisissez un nom pour l'épingle."), severity="warning")
            return

        # Epingle la selection COMPLETE actuellement dans le champ de
        # fusion (1 ou plusieurs fichiers), pas seulement la ligne en
        # surbrillance ou le 1er element — retour utilisateur reel :
        # une epingle doit pouvoir sauvegarder plusieurs chemins
        # ensemble ("il enregistre pas deux chemins sur une meme
        # epingle"). Le chemin persiste est une chaine jointe par
        # virgules (add_pinned() ne fait aucune hypothese sur son
        # contenu), re-eclatee par _resolve_token() a la relecture.
        paths = self._current_merge_paths()
        if not paths:
            self.app.notify(_("Aucune source à épingler (sélectionnez une ligne ou saisissez un chemin)."), severity="warning")
            return

        result = self._command.add_pinned(name, ", ".join(paths))
        if result.success:
            self.app.notify(_("{message} ({count} fichier(s))").format(message=result.message, count=len(paths)))
            self.query_one("#pin-name-input", Input).value = ""
            self._refresh_sources_table()
        else:
            self.app.notify(result.message, severity="error")

    def _unpin(self) -> None:
        if self._highlighted_key is None:
            self.app.notify(_("Aucune ligne en surbrillance."), severity="warning")
            return
        item = self._display_items.get(self._highlighted_key)
        if item is None:
            self.app.notify(_("Aucune ligne en surbrillance."), severity="warning")
            return
        if item["type"] == "library":
            self.app.notify(_("Ce log vient de la Bibliothèque : retirez-le depuis 5.1 Bibliothèque."), severity="warning")
            return
        if item["type"] == "pinned":
            result = self._command.remove_pinned(item["name"])
        else:
            result = self._command.remove_history_entry(item["path"])
        if result.success:
            self.app.notify(result.message)
            self._highlighted_key = None
            self._refresh_sources_table()
        else:
            self.app.notify(result.message, severity="error")

    def _purge(self) -> None:
        self._command.purge_all()
        self._highlighted_key = None
        self.query_one("#merge-input", Input).value = ""
        self.app.notify(_("Historique et épingles lnav purges avec succès."))
        self._refresh_sources_table()

    def _launch(self) -> None:
        resolved_paths = self._current_merge_paths()
        if not resolved_paths:
            self.app.notify(_("Aucune source valide sélectionnée."), severity="warning")
            return

        valid_paths: list[str] = []
        missing_paths: list[str] = []
        for p in resolved_paths:
            if p.startswith(("http://", "https://")):
                valid_paths.append(p)
                continue
            resolved = self._resolve_existing_path(p)
            if resolved is not None:
                valid_paths.append(str(resolved))
            else:
                missing_paths.append(p)

        if missing_paths:
            self.app.notify(_("Fichier(s) introuvable(s), ignore(s) : {value}").format(value=', '.join(missing_paths)), severity="warning")

        if not valid_paths:
            self.app.notify(_("Aucun fichier valide au final. Opération annulée."), severity="warning")
            return

        known_paths = self._command.list_all_known_paths()
        for p in valid_paths:
            if p not in known_paths:
                self._command.record_history(p)

        try:
            self._run_lnav(valid_paths)
        except FileNotFoundError:
            self.app.notify(
                _("L'exécutable 'lnav' est introuvable (non installé ou absent du PATH). "
                "Sur Arch/EndeavourOS : sudo pacman -S lnav"),
                severity="error",
            )
            log_action_result(self._container, _ACTION_TITLE, status="failure", error="lnav introuvable")
            return
        except Exception as e:
            self.app.notify(_("Échec du lancement de lnav : {e}").format(e=e), severity="error")
            log_action_result(self._container, _ACTION_TITLE, status="failure", error=str(e))
            return

        log_action_result(self._container, _ACTION_TITLE, status="success")

    @staticmethod
    def _resolve_existing_path(p: str) -> Path | None:
        """Un chemin saisi/epingle relatif (ex. "var/logs/access.log")
        depend du repertoire courant du PROCESSUS au moment de l'appel —
        pas garanti d'etre la racine du projet selon comment omega-fire a
        ete lance (retour utilisateur reel : "aucun fichier valide" alors
        que le fichier existait bel et bien sous var/logs/). On essaie
        donc aussi une resolution relative a la racine du projet (deduite
        de LOGS_DIR, deja calculee depuis __file__ et non le cwd — voir
        infrastructure/config/paths.py) avant d'abandonner."""
        direct = Path(p)
        if direct.is_file():
            return direct.resolve()
        if not direct.is_absolute():
            project_root = LOGS_DIR.parent.parent
            candidate = project_root / p
            if candidate.is_file():
                return candidate
        return None

    def _run_lnav(self, paths: list[str]) -> None:
        """Isole depuis _launch() pour etre substituable en test (lnav
        exige un vrai terminal interactif, non disponible sous Pilot).

        render_lnav_live() (CLI, deja valide empiriquement) gere tout
        l'encapsulage PTY+pyte, le header/footer Omega-Fire et
        l'interception clavier (Ctrl-Q pour revenir sans tuer l'appli,
        Ctrl-C pour marquer+copier, [t] pour son propre cycle de theme
        CLI) — App.suspend() se contente de rendre la main du terminal
        le temps de l'appel, exactement comme pour un subprocess normal."""
        run_lnav(self.app, paths)


def run_lnav(app: Any, paths: list[str]) -> None:
    """Lance lnav (PTY + pyte, header/footer Omega-Fire) en rendant le terminal le temps de
    l'appel. A appeler depuis un gestionnaire de clic (8.6 « Lancer lnav », 5.2 / 5.3) :
    lance automatiquement a l'ouverture d'un ecran (call_after_refresh), l'interface se
    bloquait (retour utilisateur 2026-10-28, Textual ecrivant dans un terminal deja rendu)."""
    _sync_cli_theme(app)
    with suspended_terminal(app):
        render_lnav_live([Path(p) for p in paths])


def _sync_cli_theme(app: Any) -> None:
    """render_lnav_live() lit interfaces/cli/themes/registry.py
    (theme_registry), un registre COMPLETEMENT INDEPENDANT du theme
    Textual de l'appli (omega_lib.theme, voir app.py) — jamais
    active dans le processus TUI puisque rien d'autre ne l'utilise.
    Sans ceci, get_active() a l'interieur de render_lnav_live() leve
    immediatement ("No theme is currently active."). Tente de
    reprendre le nom du theme Textual courant (memes noms dans la
    plupart des cas, ex. "omega-mono") pour une transition visuelle
    coherente ; retombe sur la detection automatique du CLI sinon.
    Ne reinitialise PAS un theme deja actif (le cycle [t] interne a
    lnav, d'une session precedente, doit persister d'un appel a
    l'autre)."""
    try:
        theme_registry.get_active()
        return
    except Exception:
        pass
    app_theme = getattr(app, "theme", None)
    if app_theme:
        try:
            initialize_theme(app_theme)
            return
        except Exception:
            pass
    initialize_theme()
