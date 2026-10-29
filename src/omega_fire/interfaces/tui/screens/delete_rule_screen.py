# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 3.2 — Supprimer une regle de pare-feu. Patron #4 (liste + CRUD)
avec un mode de nettoyage en masse des regles inactives. Logique
identique a interfaces/cli/actions.py::action_3_2_delete_rule.

Simplification assumee : la detection de regles soeurs sur d'autres
backends reste identique (informative, jamais automatique), mais le
choix "supprimer aussi les soeurs" est fait UNE FOIS pour tout le lot
(Select global) plutot qu'un dialogue distinct par regle ciblee — chaque
sous-dialogue supplementaire reintroduirait la sequence de prompts que
la migration en formulaire cherche justement a eviter."""
from __future__ import annotations

from typing import TYPE_CHECKING

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, DataTable, Footer, Header, Input, Select, Static

from omega_fire.application.commands.delete_rule import DeleteRuleCommand, DeleteRuleRequest
from omega_fire.application.queries.find_equivalent_rules import (
    FindEquivalentRulesQuery,
    FindEquivalentRulesRequest,
)
from omega_fire.application.commands.reconcile_rules import (
    KNOWN_BACKENDS,
    ReconcilePlan,
    ReconcileRulesCommand,
)
from omega_fire.application.queries.list_persisted_rules import ListPersistedRulesQuery
from omega_fire.domain.rules.ownership import rule_owner
from omega_fire.infrastructure.config.paths import BACKUPS_DIR
from omega_fire.infrastructure.probe.command_probe import is_command_available
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.screens.confirm import ConfirmScreen
from omega_fire.interfaces.tui.support.action_audit import log_action_result
from omega_fire.shared.i18n import _

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ACTION_TITLE = "3.2 Supprimer une règle"

_FILTER_OMEGA = "omega"
_FILTER_SYSTEM = "system"
_FILTER_ALL = "all"
_FILTER_INACTIVE = "inactive"
_FILTER_RECONCILE = "reconcile"


class DeleteRuleScreen(OmegaScreen):
    """Suppression d'une ou plusieurs regles, par ID ou nettoyage en masse."""

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container
        self._domain_rules_by_id: dict[int, object] = {}
        self._omega_rules: list[dict] = []
        self._system_rules: list[dict] = []
        self._inactive_rules: list[dict] = []
        self._reconcile_plan: ReconcilePlan | None = None
        self._load_rules()

    def _load_rules(self) -> None:
        rule_repository = getattr(self._container, "rule_repository", None)
        if rule_repository is None:
            return
        result = ListPersistedRulesQuery(rule_repository).execute()
        if not result.success:
            return
        domain_rules = result.rules
        self._domain_rules_by_id = {
            getattr(r, "rule_id", None): r for r in domain_rules if getattr(r, "rule_id", None) is not None
        }
        for r in domain_rules:
            r_id = getattr(r, "rule_id", None) or getattr(r, "id", None)
            is_system = getattr(r, "origin", "imported") == "imported"
            item = {
                "id": r_id,
                "name": r.comment or _("Règle #{r_id}").format(r_id=r_id),
                "chain": str(getattr(r, "chain", "INPUT")).upper(),
                "action": str(getattr(r, "action", "ACCEPT")).upper(),
                "port": str(r.port_start) if r.port_start else "ANY",
                "backend": getattr(r, "backend", "nftables"),
                "is_system": is_system,
                "enabled": bool(getattr(r, "enabled", True)),
                "owner": rule_owner(r),
            }
            (self._system_rules if is_system else self._omega_rules).append(item)
        self._inactive_rules = [r for r in (self._omega_rules + self._system_rules) if not r["enabled"]]

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(classes="omega-panel"):
            yield Static(_("SUPPRIMER UNE RÈGLE"), classes="omega-title")

            if not (self._omega_rules or self._system_rules):
                yield Static(_("Aucune règle enregistrée en base de données."), classes="omega-hint")
                with Horizontal(classes="omega-actions"), Container(classes="omega-btn-frame"):
                    yield Button(_("Retour"), id="back")
                yield Footer()
                return

            yield Static(_("Filtre d'affichage"), classes="omega-subtitle")
            options = [
                (_("Règles Omega-Fire ({count})").format(count=len(self._omega_rules)), _FILTER_OMEGA),
                (_("Règles Système importées ({count})").format(count=len(self._system_rules)), _FILTER_SYSTEM),
                (_("Toutes les règles ({value})").format(value=len(self._omega_rules) + len(self._system_rules)), _FILTER_ALL),
            ]
            if self._inactive_rules:
                options.append((_("Nettoyer les règles INACTIVES ({count})").format(count=len(self._inactive_rules)), _FILTER_INACTIVE))
            options.append((_("Nettoyer et resynchroniser la base (pare-feu non modifié)"), _FILTER_RECONCILE))
            yield Select(options, value=_FILTER_OMEGA, id="filter-select")
            yield Static("", id="reconcile-summary", classes="omega-hint omega-hidden")

            yield DataTable(id="rules-table")

            yield Static(_("ID(s) à supprimer, séparés par virgule"), id="ids-label", classes="omega-subtitle")
            yield Input(placeholder=_("ex. 12,15,18"), id="ids-input")

            yield Static(_("Règles jumelles sur d'autres backends"), id="sibling-label", classes="omega-subtitle")
            yield Select(
                [(_("Supprimer aussi sur les backends jumeaux (recommandé, cohérence)"), "with_siblings"),
                 (_("Ne retirer que la/les règle(s) précisée(s) (diagnostic)"), "target_only")],
                value="with_siblings",
                id="sibling-select",
            )

            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Supprimer"), id="launch", variant="error")
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Retour"), id="back")
        yield Footer()

    def on_mount(self) -> None:
        if self._omega_rules or self._system_rules:
            table = self.query_one("#rules-table", DataTable)
            table.add_columns(_("ID BDD"), _("Origine"), _("Nom"), _("Chaîne"), _("Action"), _("Port"), _("État"))
            self._refresh_table(_FILTER_OMEGA)

    def _rules_for_filter(self, filter_key: str) -> list[dict]:
        if filter_key == _FILTER_OMEGA:
            return self._omega_rules
        if filter_key == _FILTER_SYSTEM:
            return self._system_rules
        if filter_key == _FILTER_INACTIVE:
            return self._inactive_rules
        return self._omega_rules + self._system_rules

    def _refresh_table(self, filter_key: str) -> None:
        table = self.query_one("#rules-table", DataTable)
        table.clear()
        for r in self._rules_for_filter(filter_key):
            origin = (Text(r["owner"]) if r["owner"]
                      else Text("SYSTEME") if r["is_system"] else Text("OMEGA"))
            status = Text(_("ACTIF")) if r["enabled"] else Text(_("INACTIF"))
            table.add_row(str(r["id"]), origin, r["name"], r["chain"], r["action"], r["port"], status, key=str(r["id"]))

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id != "filter-select":
            return
        filter_key = str(event.value)
        is_inactive_mode = filter_key in (_FILTER_INACTIVE, _FILTER_RECONCILE)
        if filter_key == _FILTER_RECONCILE:
            self._show_reconcile_plan()
        else:
            self._refresh_table(filter_key)
        self.query_one("#reconcile-summary", Static).set_class(filter_key != _FILTER_RECONCILE, "omega-hidden")
        self.query_one("#ids-label", Static).set_class(is_inactive_mode, "omega-hidden")
        self.query_one("#ids-input", Input).set_class(is_inactive_mode, "omega-hidden")
        self.query_one("#sibling-label", Static).set_class(is_inactive_mode, "omega-hidden")
        self.query_one("#sibling-select", Select).set_class(is_inactive_mode, "omega-hidden")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss()
            return
        if event.button.id != "launch":
            return

        filter_key = str(self.query_one("#filter-select", Select).value)
        if filter_key == _FILTER_INACTIVE:
            self._launch_bulk_inactive()
        elif filter_key == _FILTER_RECONCILE:
            self._launch_reconcile()
        else:
            self._launch_by_ids()

    # --- Nettoyer et resynchroniser la base (retour utilisateur 2026-10-28) ---

    def _reconcile_backends(self) -> dict[str, object]:
        """Backend absent de la machine (binaire introuvable) -> None : ses lignes seront
        retirees. Present : son adapter, lu par la commande (lecture en echec = lignes
        gardees)."""
        backends: dict[str, object] = {}
        for name in KNOWN_BACKENDS:
            if not is_command_available("nft" if name == "nftables" else name):
                backends[name] = None
                continue
            try:
                backends[name] = self._container.get_firewall_port(name)
            except Exception:
                backends[name] = None
        return backends

    def _show_reconcile_plan(self) -> None:
        plan = ReconcileRulesCommand(self._container.rule_repository, BACKUPS_DIR / "db").plan(
            self._reconcile_backends()
        )
        self._reconcile_plan = plan
        lines = [
            _("Aperçu — seule la base change, aucune règle du pare-feu n'est ajoutée ni retirée."),
            _("Noyau : {value}").format(value=", ".join(f"{k}={v}" for k, v in plan.live_counts.items()) or "—"),
            _("À garder : {count}").format(count=len(plan.keep)),
            _("Doublons à retirer : {count}").format(count=len(plan.duplicates)),
            _("Absentes du noyau, à retirer : {count}").format(count=len(plan.stale)),
            _("Backend absent de la machine, à retirer : {count}").format(count=len(plan.unavailable)),
            _("Règles du noyau à importer : {count}").format(count=len(plan.to_import)),
        ]
        for name, error in plan.unreadable.items():
            lines.append(_("Backend {backend} illisible, ses lignes ne sont pas touchées : {e}").format(backend=name, e=error))
        self.query_one("#reconcile-summary", Static).update("\n".join(lines))

        table = self.query_one("#rules-table", DataTable)
        table.clear()
        for r in plan.to_remove:
            owner = rule_owner(r)
            origin = Text(owner) if owner else Text("SYSTEME") if r.origin == "imported" else Text("OMEGA")
            status = Text(_("ACTIF")) if r.enabled else Text(_("INACTIF"))
            chain = getattr(r.chain, "value", r.chain)
            action = getattr(r.action, "value", r.action)
            table.add_row(
                str(r.rule_id), origin, r.comment or _("Règle #{r_id}").format(r_id=r.rule_id),
                str(chain).upper(), str(action).upper(), str(r.port_start) if r.port_start else "ANY",
                status, key=str(r.rule_id),
            )

    def _launch_reconcile(self) -> None:
        plan = self._reconcile_plan
        if plan is None:
            return
        if not plan.has_changes:
            self.app.notify(_("La base est déjà propre : rien à changer."))
            return
        message = _(
            "Retirer {removed} ligne(s) de la base et importer {imported} règle(s) du noyau ?\n"
            "Le pare-feu n'est pas modifié. La base est sauvegardée avant, dans {path}."
        ).format(removed=len(plan.to_remove), imported=len(plan.to_import), path=BACKUPS_DIR / "db")
        self.app.push_screen(
            ConfirmScreen(title=_("Nettoyer et resynchroniser la base"), message=message),
            self._reconcile_if_confirmed,
        )

    def _reconcile_if_confirmed(self, confirmed: bool | None) -> None:
        if not confirmed or self._reconcile_plan is None:
            return
        result = ReconcileRulesCommand(self._container.rule_repository, BACKUPS_DIR / "db").apply(
            self._reconcile_plan
        )
        self.app.notify(result.message, severity="information" if result.success else "error", timeout=10)
        log_action_result(
            self._container, _ACTION_TITLE,
            status="success" if result.success else "failure",
            error=None if result.success else result.message,
        )
        self.dismiss()

    def _launch_bulk_inactive(self) -> None:
        if not self._inactive_rules:
            self.app.notify(_("Aucune règle inactive."), severity="warning")
            return
        by_origin = {"OMEGA": 0, "SYSTEME": 0}
        by_backend: dict[str, int] = {}
        for r in self._inactive_rules:
            by_origin["SYSTEME" if r["is_system"] else "OMEGA"] += 1
            by_backend[r["backend"]] = by_backend.get(r["backend"], 0) + 1
        message = (
            _("{count} règle(s) inactive(s) : {OMEGA} Omega-Fire, {SYSTEME} système importées.\nBackend : ").format(count=len(self._inactive_rules), OMEGA=by_origin['OMEGA'], SYSTEME=by_origin['SYSTEME'])
            + ", ".join(f"{k}={v}" for k, v in by_backend.items())
        )
        self.app.push_screen(
            ConfirmScreen(title=_("CONFIRMER LE NETTOYAGE"), message=message),
            self._bulk_delete_if_confirmed,
        )

    def _bulk_delete_if_confirmed(self, confirmed: bool | None) -> None:
        if not confirmed:
            return
        rule_repository = self._container.rule_repository
        success_count = 0
        failure_count = 0
        for r in self._inactive_rules:
            result = DeleteRuleCommand(rule_repository, firewall_adapter=None).execute(
                DeleteRuleRequest(rule_id=r["id"])
            )
            if result.success:
                success_count += 1
            else:
                failure_count += 1
        self.app.notify(_("Nettoyage terminé : {success_count} règle(s) supprimée(s), {failure_count} échec(s).").format(success_count=success_count, failure_count=failure_count))
        log_action_result(self._container, _ACTION_TITLE, status="success" if success_count else "failure")
        self.dismiss()

    def _launch_by_ids(self) -> None:
        raw = self.query_one("#ids-input", Input).value.strip()
        if not raw:
            self.app.notify(_("Saisissez au moins un ID."), severity="warning")
            return
        raw_ids = [part.strip() for part in raw.split(",") if part.strip()]
        target_ids: list[int] = []
        invalid: list[str] = []
        for raw_id in raw_ids:
            try:
                target_ids.append(int(raw_id))
            except ValueError:
                invalid.append(raw_id)
        if invalid:
            self.app.notify(_("ID(s) invalide(s) ignore(s) : {value}.").format(value=', '.join(invalid)), severity="warning")
        if not target_ids:
            self.app.notify(_("Aucun ID valide fourni."), severity="error")
            return

        with_siblings = str(self.query_one("#sibling-select", Select).value) == "with_siblings"
        rule_repository = self._container.rule_repository

        ids_to_delete: list[int] = []
        already_considered: set[int] = set()
        sibling_notes: list[str] = []

        for target_id in target_ids:
            if target_id in already_considered:
                continue
            already_considered.add(target_id)
            ids_to_delete.append(target_id)

            domain_rule = self._domain_rules_by_id.get(target_id)
            if domain_rule is None:
                continue
            protocol_str = domain_rule.protocol.value if domain_rule.protocol else "ALL"
            equiv_result = FindEquivalentRulesQuery(rule_repository).execute(
                FindEquivalentRulesRequest(
                    exclude_backend=domain_rule.backend, chain=domain_rule.chain.value,
                    action=domain_rule.action.value, protocol=protocol_str,
                    port_start=domain_rule.port_start, source_cidr=domain_rule.source_cidr,
                )
            )
            if not equiv_result.success or not equiv_result.rules:
                continue
            siblings = [s for s in equiv_result.rules if s.rule_id not in already_considered and s.rule_id not in target_ids]
            if not siblings:
                continue
            for sibling in siblings:
                already_considered.add(sibling.rule_id)
                if rule_owner(sibling):
                    # Jamais une regle d'un autre outil (UFW...) comme « jumelle » :
                    # la comparaison porte sur des champs reduits.
                    continue
                sibling_notes.append(f"#{target_id} ({domain_rule.backend}) <-> #{sibling.rule_id} ({sibling.backend})")
                if with_siblings:
                    ids_to_delete.append(sibling.rule_id)

        # Regle d'un autre outil : se gere avec cet outil (ufw, tailscale...), jamais
        # depuis Omega-Fire (l'outil la recree, ou son jeu de regles devient incoherent).
        foreign = {
            i: rule_owner(self._domain_rules_by_id[i]) for i in ids_to_delete
            if i in self._domain_rules_by_id and rule_owner(self._domain_rules_by_id[i])
        }
        if foreign:
            ids_to_delete = [i for i in ids_to_delete if i not in foreign]
            self.app.notify(
                _("Règle(s) {ids} gérée(s) par {tools} : non supprimée(s) ici, à gérer avec l'outil concerné.").format(
                    ids=", ".join(f"#{i}" for i in foreign), tools=", ".join(sorted(set(foreign.values()))),
                ),
                severity="warning", timeout=10,
            )
            if not ids_to_delete:
                return

        message = _("Supprimer {count} règle(s) (ID : {value}) ?").format(count=len(ids_to_delete), value=', '.join(str(i) for i in ids_to_delete))
        if sibling_notes:
            message += _("\nRègles jumelles détectées :\n") + "\n".join(f"  - {n}" for n in sibling_notes[:5])

        self.app.push_screen(
            ConfirmScreen(title=_("CONFIRMER LA SUPPRESSION"), message=message),
            lambda confirmed: self._delete_if_confirmed(confirmed, ids_to_delete),
        )

    def _delete_if_confirmed(self, confirmed: bool | None, ids_to_delete: list[int]) -> None:
        if not confirmed:
            return
        rule_repository = self._container.rule_repository
        success_count = 0
        failure_count = 0
        for delete_id in ids_to_delete:
            domain_rule = self._domain_rules_by_id.get(delete_id)
            firewall_adapter = None
            if domain_rule is not None:
                try:
                    firewall_adapter = self._container.get_firewall_port(domain_rule.backend)
                except Exception:
                    firewall_adapter = None
            result = DeleteRuleCommand(rule_repository, firewall_adapter).execute(DeleteRuleRequest(rule_id=delete_id))
            if result.success:
                success_count += 1
                self.app.notify(result.message, severity="information")
            else:
                failure_count += 1
                self.app.notify(result.message, severity="error")

        log_action_result(self._container, _ACTION_TITLE, status="success" if success_count else "failure")
        self.dismiss()
