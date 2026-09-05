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
from omega_fire.application.queries.list_persisted_rules import ListPersistedRulesQuery
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.screens.confirm import ConfirmScreen
from omega_fire.interfaces.tui.support.action_audit import log_action_result

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ACTION_TITLE = "3.2 Supprimer une regle"

_FILTER_OMEGA = "omega"
_FILTER_SYSTEM = "system"
_FILTER_ALL = "all"
_FILTER_INACTIVE = "inactive"


class DeleteRuleScreen(OmegaScreen):
    """Suppression d'une ou plusieurs regles, par ID ou nettoyage en masse."""

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container
        self._domain_rules_by_id: dict[int, object] = {}
        self._omega_rules: list[dict] = []
        self._system_rules: list[dict] = []
        self._inactive_rules: list[dict] = []
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
                "name": r.comment or f"Regle #{r_id}",
                "chain": str(getattr(r, "chain", "INPUT")).upper(),
                "action": str(getattr(r, "action", "ACCEPT")).upper(),
                "port": str(r.port_start) if r.port_start else "ANY",
                "backend": getattr(r, "backend", "nftables"),
                "is_system": is_system,
                "enabled": bool(getattr(r, "enabled", True)),
            }
            (self._system_rules if is_system else self._omega_rules).append(item)
        self._inactive_rules = [r for r in (self._omega_rules + self._system_rules) if not r["enabled"]]

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(classes="omega-panel"):
            yield Static("SUPPRIMER UNE REGLE", classes="omega-title")

            if not (self._omega_rules or self._system_rules):
                yield Static("Aucune regle enregistree en base de donnees.", classes="omega-hint")
                with Horizontal(classes="omega-actions"), Container(classes="omega-btn-frame"):
                    yield Button("Retour", id="back")
                yield Footer()
                return

            yield Static("Filtre d'affichage", classes="omega-subtitle")
            options = [
                (f"Regles Omega-Fire ({len(self._omega_rules)})", _FILTER_OMEGA),
                (f"Regles Systeme importees ({len(self._system_rules)})", _FILTER_SYSTEM),
                (f"Toutes les regles ({len(self._omega_rules) + len(self._system_rules)})", _FILTER_ALL),
            ]
            if self._inactive_rules:
                options.append((f"Nettoyer les regles INACTIVES ({len(self._inactive_rules)})", _FILTER_INACTIVE))
            yield Select(options, value=_FILTER_OMEGA, id="filter-select")

            yield DataTable(id="rules-table")

            yield Static("ID(s) a supprimer, separes par virgule", id="ids-label", classes="omega-subtitle")
            yield Input(placeholder="ex. 12,15,18", id="ids-input")

            yield Static("Regles jumelles sur d'autres backends", id="sibling-label", classes="omega-subtitle")
            yield Select(
                [("Supprimer aussi sur les backends jumeaux (recommande, coherence)", "with_siblings"),
                 ("Ne retirer que la/les regle(s) precisee(s) (diagnostic)", "target_only")],
                value="with_siblings",
                id="sibling-select",
            )

            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button("Supprimer", id="launch", variant="error")
                with Container(classes="omega-btn-frame"):
                    yield Button("Retour", id="back")
        yield Footer()

    def on_mount(self) -> None:
        if self._omega_rules or self._system_rules:
            table = self.query_one("#rules-table", DataTable)
            table.add_columns("ID BDD", "Origine", "Nom", "Chaine", "Action", "Port", "Etat")
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
            origin = Text("SYSTEME") if r["is_system"] else Text("OMEGA")
            status = Text("ACTIF") if r["enabled"] else Text("INACTIF")
            table.add_row(str(r["id"]), origin, r["name"], r["chain"], r["action"], r["port"], status, key=str(r["id"]))

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id != "filter-select":
            return
        filter_key = str(event.value)
        is_inactive_mode = filter_key == _FILTER_INACTIVE
        self._refresh_table(filter_key)
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
        else:
            self._launch_by_ids()

    def _launch_bulk_inactive(self) -> None:
        if not self._inactive_rules:
            self.app.notify("Aucune regle inactive.", severity="warning")
            return
        by_origin = {"OMEGA": 0, "SYSTEME": 0}
        by_backend: dict[str, int] = {}
        for r in self._inactive_rules:
            by_origin["SYSTEME" if r["is_system"] else "OMEGA"] += 1
            by_backend[r["backend"]] = by_backend.get(r["backend"], 0) + 1
        message = (
            f"{len(self._inactive_rules)} regle(s) inactive(s) : {by_origin['OMEGA']} Omega-Fire, "
            f"{by_origin['SYSTEME']} systeme importees.\nBackend : "
            + ", ".join(f"{k}={v}" for k, v in by_backend.items())
        )
        self.app.push_screen(
            ConfirmScreen(title="CONFIRMER LE NETTOYAGE", message=message),
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
        self.app.notify(f"Nettoyage termine : {success_count} regle(s) supprimee(s), {failure_count} echec(s).")
        log_action_result(self._container, _ACTION_TITLE, status="success" if success_count else "failure")
        self.dismiss()

    def _launch_by_ids(self) -> None:
        raw = self.query_one("#ids-input", Input).value.strip()
        if not raw:
            self.app.notify("Saisissez au moins un ID.", severity="warning")
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
            self.app.notify(f"ID(s) invalide(s) ignore(s) : {', '.join(invalid)}.", severity="warning")
        if not target_ids:
            self.app.notify("Aucun ID valide fourni.", severity="error")
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
                sibling_notes.append(f"#{target_id} ({domain_rule.backend}) <-> #{sibling.rule_id} ({sibling.backend})")
                if with_siblings:
                    ids_to_delete.append(sibling.rule_id)

        message = f"Supprimer {len(ids_to_delete)} regle(s) (ID : {', '.join(str(i) for i in ids_to_delete)}) ?"
        if sibling_notes:
            message += "\nRegles jumelles detectees :\n" + "\n".join(f"  - {n}" for n in sibling_notes[:5])

        self.app.push_screen(
            ConfirmScreen(title="CONFIRMER LA SUPPRESSION", message=message),
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
