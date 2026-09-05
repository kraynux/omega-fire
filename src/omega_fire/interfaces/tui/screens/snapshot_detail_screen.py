# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 7.2 (detail) — actions sur un snapshot choisi : restaurer,
modifier la description, supprimer. Logique identique a
_snapshot_submenu()/_do_restore()/_do_edit_description()/_do_delete_single()
de interfaces/cli/actions.py::action_7_2_restore_state."""
from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Input, Static

from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.screens.confirm import ConfirmScreen
from omega_fire.interfaces.tui.support.action_audit import log_action_result

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ACTION_TITLE = "7.2 Restaurer un etat"

_RESTORE_WARNING = (
    "Les regles firewall actuellement gerees par Omega-Fire seront RETIREES puis "
    "REMPLACEES par celles du snapshot. Les IPs bannies du snapshot seront AJOUTEES "
    "(rien n'est retire). Les jails fail2ban ne sont PAS restaurees automatiquement "
    "(info seulement). Les regles/IPs d'autres outils (UFW, etc.) ne sont jamais touchees."
)


class SnapshotDetailScreen(OmegaScreen):
    """Actions disponibles sur un snapshot d'etat."""

    def __init__(self, *, container: DependencyContainer, snapshot) -> None:
        super().__init__()
        self._container = container
        self._snapshot = snapshot

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="omega-form-panel"):
            yield Static(f"SNAPSHOT : {self._snapshot.id}", classes="omega-title")
            yield Static(f"Description actuelle : {self._snapshot.description or '(aucune)'}", classes="omega-hint")

            yield Static("Nouvelle description", classes="omega-subtitle")
            yield Input(id="description-input")
            with Horizontal(classes="omega-actions"), Container(classes="omega-btn-frame"):
                yield Button("Modifier", id="edit-description")

            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button("Restaurer cet etat", id="restore", variant="error")
                with Container(classes="omega-btn-frame"):
                    yield Button("Supprimer ce snapshot", id="delete", variant="error")
                with Container(classes="omega-btn-frame"):
                    yield Button("Retour", id="back")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss()
            return
        if event.button.id == "edit-description":
            self._edit_description()
            return
        if event.button.id == "restore":
            self.app.push_screen(
                ConfirmScreen(
                    title="CONFIRMER LA RESTAURATION",
                    message=f"{_RESTORE_WARNING}\n\nRestaurer '{self._snapshot.id}' ?",
                ),
                self._restore_if_confirmed,
            )
            return
        if event.button.id == "delete":
            self.app.push_screen(
                ConfirmScreen(title="CONFIRMER LA SUPPRESSION", message=f"Supprimer definitivement '{self._snapshot.id}' ?"),
                self._delete_if_confirmed,
            )

    def _edit_description(self) -> None:
        new_desc = self.query_one("#description-input", Input).value.strip()
        if not new_desc:
            self.app.notify("Saisissez une nouvelle description.", severity="warning")
            return
        try:
            persistence_port = self._container.get_persistence_port()
            updated = persistence_port.update_snapshot_description(self._snapshot.id, new_desc)
        except Exception as e:
            self.app.notify(f"Erreur lors de la modification : {e}", severity="error")
            return
        if updated:
            self.app.notify("Description mise a jour.")
            self.query_one("#description-input", Input).value = ""
        else:
            self.app.notify("Snapshot introuvable (a-t-il ete supprime entre-temps ?).", severity="error")

    def _restore_if_confirmed(self, confirmed: bool | None) -> None:
        if not confirmed:
            return

        def _execute():
            from omega_fire.application.commands.restore_state import RestoreStateCommand, RestoreStateRequest

            persistence_port = self._container.get_persistence_port()
            adapters = {
                "nftables": self._container.get_firewall_port("nftables"),
                "iptables": self._container.get_firewall_port("iptables"),
                "ip6tables": self._container.get_firewall_port("ip6tables"),
            }
            try:
                adapters["fail2ban"] = self._container.get_fail2ban_port()
            except Exception:
                adapters["fail2ban"] = None

            return RestoreStateCommand(
                persistence_port=persistence_port, adapters=adapters, rule_repository=self._container.rule_repository,
            ).execute(RestoreStateRequest(snapshot_id=self._snapshot.id))

        def _on_done(result) -> None:
            if not result.success:
                self.app.notify(f"Echec de la restauration : {result.message}", severity="error")
                log_action_result(self._container, _ACTION_TITLE, status="failure", error=result.message)
                return

            self.app.notify(
                f"Restauration reussie : {result.rules_applied} regle(s) appliquee(s), "
                f"{result.ips_added} IP(s) ajoutee(s), {len(result.errors)} erreur(s)."
            )
            log_action_result(self._container, _ACTION_TITLE, status="success")
            self.dismiss()

        def _on_error(error: Exception) -> None:
            self.app.notify(f"Echec de la restauration : {error}", severity="error")
            log_action_result(self._container, _ACTION_TITLE, status="failure", error=str(error))

        self.run_blocking(_execute, _on_done, busy_message="Restauration en cours...", on_error=_on_error)

    def _delete_if_confirmed(self, confirmed: bool | None) -> None:
        if not confirmed:
            return
        try:
            persistence_port = self._container.get_persistence_port()
            persistence_port.delete_snapshot(self._snapshot.id)
        except Exception as e:
            self.app.notify(f"Erreur lors de la suppression : {e}", severity="error")
            return
        self.app.notify(f"Snapshot '{self._snapshot.id}' supprime.")
        self.dismiss("__deleted__")
