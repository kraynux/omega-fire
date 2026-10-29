# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 3.5 — Gestion des tables (retour utilisateur 2026-09-24, suite a
l'incident reel : perte totale de reseau apres application repetee de
profils, `nft flush ruleset` global necessaire pour recuperer l'acces
faute d'un equivalent controle dans Omega-Fire). Logique identique a
interfaces/cli/actions.py::action_3_5_table_management, meme 5 actions
(+ suppression complete de table en variante "avancee" du flush cible) :
diagnostic en lecture seule toujours affiche en premier
(application/commands/manage_tables.py::GetTablesStatusQuery), puis un
choix d'action (Select) qui revele/masque le choix de backend cible
(patron deja etabli par delete_rule_screen.py::on_select_changed)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, DataTable, Footer, Header, Select, Static

from omega_fire.application.commands.manage_tables import (
    DeleteTableCommand,
    FlushAllTablesSyncCommand,
    FlushBackendTableCommand,
    GetTablesStatusQuery,
    InitializeTablesCommand,
    ResetChainPoliciesCommand,
)
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.application.queries.policy_divergence import describe_policies
from omega_fire.application.queries.foreign_rules import (
    describe_foreign_rules,
    foreign_rules_by_backend,
)
from omega_fire.interfaces.tui.screens.choice import ChoiceScreen
from omega_fire.interfaces.tui.screens.confirm import ConfirmScreen
from omega_fire.interfaces.tui.support.action_audit import log_action_result
from omega_fire.shared.i18n import _

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ACTION_TITLE = "3.5 Gestion des tables"

_ACTION_INIT = "init"
_ACTION_RESET = "reset"
_ACTION_FLUSH_ONE = "flush_one"
_ACTION_FLUSH_ALL = "flush_all"
_ACTION_DELETE_TABLE = "delete_table"

# Actions qui ont besoin d'un backend cible explicite (Select revele) —
# init/flush_all agissent sur TOUS les backends detectes d'un coup,
# delete_table est nftables-only et n'a donc rien a choisir non plus.
_NEEDS_BACKEND_CHOICE = (_ACTION_RESET, _ACTION_FLUSH_ONE)


class TableManagementScreen(OmegaScreen):
    """Diagnostic + 5 actions de gestion des tables firewall."""

    CSS = """
    /* Trois lignes (une par backend) : hauteur naturelle. Le 1fr commun aux
       DataTable l'ecrasait a une ligne en 80x24 des que le reste debordait. */
    TableManagementScreen #status-table {
        height: auto;
    }

    TableManagementScreen #tables-actions {
        width: 100%;
        height: auto;
        align: center middle;
        margin: 0;
    }
    """

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container
        self._adapters: dict[str, object] = {}
        self._available_backends: list[str] = []
        self._detect_backends()

    def _detect_backends(self) -> None:
        for name in ("nftables", "iptables", "ip6tables"):
            try:
                self._adapters[name] = self._container.get_firewall_port(name)
            except Exception:
                self._adapters[name] = None
        self._available_backends = [n for n, a in self._adapters.items() if a is not None]

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="omega-panel"):
            yield Static(_("GESTION DES TABLES"), classes="omega-title")

            if not self._available_backends:
                yield Static(
                    _("Aucun backend firewall disponible (nftables, iptables et ip6tables non détectés)."),
                    classes="omega-hint",
                )
                with Horizontal(classes="omega-actions"), Container(classes="omega-btn-frame"):
                    yield Button(_("Retour"), id="back")
                yield Footer()
                return

            yield DataTable(id="status-table")
            yield Static("", id="divergence-hint", classes="omega-hint")

            yield Static(_("Action"), classes="omega-subtitle")
            action_options = [
                (_("Initialiser les tables (nftables, première utilisation)"), _ACTION_INIT),
                (_("Réinitialiser les politiques à ACCEPT sur un backend"), _ACTION_RESET),
                (_("Vider un backend spécifique"), _ACTION_FLUSH_ONE),
                (_("Vider TOUS les backends détectés (synchronisé)"), _ACTION_FLUSH_ALL),
                (_("[AVANCÉ] Supprimer complètement la table nftables"), _ACTION_DELETE_TABLE),
            ]
            yield Select(action_options, value=_ACTION_INIT, id="action-select", allow_blank=False)

            yield Static(_("Backend cible"), id="backend-label", classes="omega-subtitle omega-hidden")
            backend_options = [(name, name) for name in self._available_backends]
            yield Select(
                backend_options,
                value=self._available_backends[0],
                id="backend-select",
                classes="omega-hidden",
                allow_blank=False,
            )

        # Hors de la zone qui defile : toujours visible en 80x24, meme avec
        # l'explication des politiques (meme principe que les Reglages).
        with Horizontal(classes="omega-actions", id="tables-actions"):
            with Container(classes="omega-btn-frame"):
                yield Button(_("Exécuter"), id="launch", variant="error")
            with Container(classes="omega-btn-frame"):
                yield Button(_("Rafraîchir"), id="refresh")
            with Container(classes="omega-btn-frame"):
                yield Button(_("Retour"), id="back")
        yield Footer()

    def on_mount(self) -> None:
        if not self._available_backends:
            return
        table = self.query_one("#status-table", DataTable)
        table.add_columns(_("Backend"), _("Table"), "INPUT", "OUTPUT", "FORWARD", _("Règles"))
        self._refresh_status()
        # Le focus initial (tableau) fait defiler la zone : titre masque en 80x24.
        self.call_after_refresh(lambda: self.query_one(".omega-panel").scroll_home(animate=False))

    def _policy_cell(self, policies: dict, chain: str) -> Text:
        policy = policies.get(chain) or policies.get(chain.upper())
        if policy is None:
            return Text("—", style="dim")
        return Text(policy.upper(), style="green" if policy.lower() == "accept" else "red")

    def _refresh_status(self) -> None:
        table = self.query_one("#status-table", DataTable)
        table.clear()
        result = GetTablesStatusQuery(self._adapters).execute()
        for entry in result.entries:
            if not entry.available:
                table.add_row(entry.backend, "—", "—", "—", "—", "—")
                continue
            if entry.error:
                table.add_row(entry.backend, Text(_("erreur : {error}").format(error=entry.error), style="red"), "—", "—", "—", "—")
                continue
            table_cell = Text(_("présente"), style="green") if entry.table_exists else Text(_("absente"), style="yellow")
            table.add_row(
                entry.backend, table_cell,
                self._policy_cell(entry.policies, "input"),
                self._policy_cell(entry.policies, "output"),
                self._policy_cell(entry.policies, "forward"),
                str(entry.rule_count),
            )

        # Effet reel, cause et remede (retour utilisateur 2026-10-28) ; jaune seulement
        # pour une politique DROP orpheline, le seul cas qui bloque a tort.
        hint = self.query_one("#divergence-hint", Static)
        analysis = result.policy_analysis
        lines = describe_policies(analysis) if analysis is not None else []
        hint.update(Text("\n".join(lines), style="yellow" if analysis is not None and analysis.has_alert else ""))

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id != "action-select":
            return
        needs_backend = str(event.value) in _NEEDS_BACKEND_CHOICE
        self.query_one("#backend-label", Static).set_class(not needs_backend, "omega-hidden")
        self.query_one("#backend-select", Select).set_class(not needs_backend, "omega-hidden")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss()
            return
        if event.button.id == "refresh":
            self._refresh_status()
            return
        if event.button.id != "launch" or not self._available_backends:
            return

        action = str(self.query_one("#action-select", Select).value)

        if action == _ACTION_INIT:
            if self._adapters.get("nftables") is None:
                self.app.notify(_("nftables n'est pas disponible — rien à initialiser."), severity="error")
                return
            self._run(lambda: InitializeTablesCommand(self._adapters["nftables"]).execute())
            return

        if action == _ACTION_DELETE_TABLE:
            if self._adapters.get("nftables") is None:
                self.app.notify(_("nftables n'est pas disponible — rien à supprimer."), severity="error")
                return
            self.app.push_screen(
                ConfirmScreen(
                    title=_("[AVANCÉ] SUPPRIMER LA TABLE"),
                    message=(
                        _("Supprime la table nftables ENTIÈRE (chaînes et hooks compris, pas "
                        "seulement les règles). Plus aucun filtrage actif sur ce backend tant "
                        "qu'elle n'est pas réinitialisée ensuite. Continuer ?")
                    ),
                ),
                lambda confirmed: self._run_if_confirmed(
                    confirmed, lambda: DeleteTableCommand(self._adapters["nftables"]).execute()
                ),
            )
            return

        if action == _ACTION_FLUSH_ALL:
            # Garde-fou (2026-10-28) : iptables / ip6tables portent aussi les regles
            # d'autres outils (UFW...) ; l'utilisateur choisit, en le sachant.
            foreign = foreign_rules_by_backend(self._adapters)
            if foreign:
                choices = [(_("Tous les backends — efface ces règles"), "all", "error")]
                if self._adapters.get("nftables") is not None:
                    choices.append((_("Seulement nftables — garde ces règles"), "nftables", "warning"))
                self.app.push_screen(
                    ChoiceScreen(
                        title=_("RÈGLES D'AUTRES OUTILS DÉTECTÉES"),
                        message=_(
                            "Vider : {targets}.\nRègles d'autres outils trouvées : {detail}.\n\n"
                            "Sur iptables / ip6tables, vider = toute la table filter (iptables -F) : "
                            "ces règles sont effacées, leurs chaînes restent vides et la politique par "
                            "défaut est inchangée (si elle est DROP, seul ce qui reste autorisé passe). "
                            "L'outil ne les repose qu'à son prochain rechargement (ex. « ufw reload »).\n"
                            "Sur nftables, seule la table d'Omega-Fire est vidée. Détails : touche « a »."
                        ).format(targets=", ".join(self._available_backends), detail=describe_foreign_rules(foreign)),
                        choices=choices,
                        help_node="3.5",
                    ),
                    self._flush_all_choice,
                )
                return
            self.app.push_screen(
                ConfirmScreen(
                    title=_("CONFIRMER LE VIDAGE GLOBAL"),
                    message=(
                        _("Va vider TOUTES les règles sur TOUS les backends détectés ({value}). Continuer ?").format(value=', '.join(self._available_backends))
                    ),
                ),
                lambda confirmed: self._run_if_confirmed(
                    confirmed, lambda: FlushAllTablesSyncCommand(self._adapters).execute()
                ),
            )
            return

        # RESET / FLUSH_ONE : besoin du backend choisi
        backend = str(self.query_one("#backend-select", Select).value)
        adapter = self._adapters.get(backend)
        if adapter is None:
            self.app.notify(_("{backend} n'est pas disponible.").format(backend=backend), severity="error")
            return

        foreign = foreign_rules_by_backend({backend: adapter})
        foreign_note = ""
        if foreign:
            foreign_note = "\n\n" + _("Règles d'autres outils sur ce backend : {detail}.").format(detail=describe_foreign_rules(foreign))

        if action == _ACTION_RESET:
            message = _("Remettre input/output/forward à ACCEPT sur {backend} ?").format(backend=backend)
            if foreign:
                message += foreign_note + "\n" + _(
                    "Ces outils comptent souvent sur une politique DROP (UFW met INPUT en DROP) : "
                    "à ACCEPT, tout paquet qu'aucune règle ne bloque explicitement est accepté. "
                    "Détails : touche « a »."
                )
            self.app.push_screen(
                ConfirmScreen(
                    title=_("CONFIRMER LA RÉINITIALISATION"),
                    message=message,
                    help_node="3.5",
                ),
                lambda confirmed: self._run_if_confirmed(
                    confirmed, lambda: ResetChainPoliciesCommand(adapter, backend).execute()
                ),
            )
            return

        if action == _ACTION_FLUSH_ONE:
            self.app.push_screen(
                ConfirmScreen(
                    title=_("CONFIRMER LE VIDAGE"),
                    help_node="3.5",
                    message=_("Vider (flush) toutes les règles de {backend} ?").format(backend=backend) + (
                        foreign_note + "\n" + _(
                            "Elles seront effacées avec celles d'Omega-Fire (iptables -F vide toute la "
                            "table filter) ; l'outil ne les repose qu'à son prochain rechargement "
                            "(ex. « ufw reload »). Détails : touche « a »."
                        ) if foreign else ""
                    ),
                ),
                lambda confirmed: self._run_if_confirmed(
                    confirmed, lambda: FlushBackendTableCommand(adapter, backend).execute()
                ),
            )
            return

    def _flush_all_choice(self, choice: str | None) -> None:
        if choice == "all":
            self._run(lambda: FlushAllTablesSyncCommand(self._adapters).execute())
        elif choice == "nftables":
            self._run(lambda: FlushAllTablesSyncCommand({"nftables": self._adapters.get("nftables")}).execute())

    def _run_if_confirmed(self, confirmed: bool | None, execute) -> None:
        if not confirmed:
            return
        self._run(execute)

    def _run(self, execute) -> None:
        result = execute()
        self.app.notify(result.message, severity="information" if result.success else "error")
        log_action_result(self._container, _ACTION_TITLE, status="success" if result.success else "failure")
        self._refresh_status()


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Equivalent TUI de interfaces/cli/actions.py::action_3_5_table_management —
#   diagnostic (GetTablesStatusQuery) toujours affiché, puis 5 actions
#   (application/commands/manage_tables.py, retour utilisateur 2026-09-24).
#
# Pourquoi dans interfaces/tui/ (charte) :
# - Aucune logique metier ici — délègue entièrement aux commandes de
#   application/commands/manage_tables.py, comme tous les autres écrans.
#
# Points clés :
# - _NEEDS_BACKEND_CHOICE : seules "reset" et "flush_one" ont besoin d'un
#   Select backend explicite — "init"/"flush_all"/"delete_table" agissent
#   soit sur nftables uniquement (init/delete_table), soit sur tous les
#   backends détectés d'un coup (flush_all), jamais un choix à faire.
# - init et delete_table sont nftables-only (voir manage_tables.py) —
#   grisés via message d'erreur direct si nftables absent, jamais un
#   Select vide.
#---------------------------------------------------------------------->
