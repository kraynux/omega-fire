# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 4.5 — Supprimer un jail Fail2ban (arret, fichiers .conf/.local,
filtre associe, rechargement — tout gere par Fail2banPort.delete_jail()).
Patron #2 + confirmation destructive. Logique identique a
interfaces/cli/actions.py::action_4_5_delete_jail.

La collecte (list_configured_jail_files()/get_jail_status()) et la
suppression (delete_jail(), qui recharge le service) s'executent en
arriere-plan (run_blocking, voir _base.py) — synchrones dans __init__/le
handler de confirmation, elles gelaient TOUTE l'app (retour utilisateur
reel, mode degrade)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Select, Static

from omega_fire.application.queries.jail_status import get_jail_status
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.screens.confirm import ConfirmScreen
from omega_fire.interfaces.tui.support.action_audit import log_action_result

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ACTION_TITLE = "4.5 Suppression et Desactivation de Jail Fail2ban"


class DeleteJailScreen(OmegaScreen):
    """Suppression complete (arret + config + filtre) d'un jail configure."""

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container
        self._fail2ban_port = None
        self._jail_files: dict[str, str] = {}

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="omega-form-panel"):
            yield Static("SUPPRIMER UN JAIL", classes="omega-title")
            yield Static("Chargement des jails...", id="status-hint", classes="omega-hint")
            yield Static("Jail", id="jail-label", classes="omega-subtitle omega-hidden")
            yield Select([], id="jail-select", classes="omega-hidden")
            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button("Supprimer", id="launch", variant="error", disabled=True)
                with Container(classes="omega-btn-frame"):
                    yield Button("Retour", id="back")
        yield Footer()

    def on_mount(self) -> None:
        self.run_blocking(self._collect_jail_files, self._on_loaded, busy_message="Chargement des jails...")

    def _collect_jail_files(self) -> tuple:
        try:
            fail2ban_port = self._container.get_fail2ban_port()
        except Exception:
            fail2ban_port = None

        jail_files: dict[str, str] = {}
        if fail2ban_port is not None:
            try:
                jail_files = dict(fail2ban_port.list_configured_jail_files())
            except Exception:
                jail_files = {}
        status_result = get_jail_status(fail2ban_port=fail2ban_port)
        for j in status_result.jails:
            if j.name not in jail_files:
                jail_files[j.name] = f"/etc/fail2ban/jail.d/{j.name}.conf"
        return fail2ban_port, jail_files

    def _on_loaded(self, result) -> None:
        fail2ban_port, jail_files = result
        self._fail2ban_port = fail2ban_port
        self._jail_files = jail_files

        if not jail_files:
            self.query_one("#status-hint", Static).update(
                "Aucun jail personnalise ou actif n'a ete trouve dans '/etc/fail2ban/jail.d/'."
            )
            return

        self.query_one("#status-hint", Static).set_class(True, "omega-hidden")
        self.query_one("#jail-label", Static).set_class(False, "omega-hidden")
        jail_select = self.query_one("#jail-select", Select)
        jail_select.set_class(False, "omega-hidden")
        jail_select.set_options([(f"{name} ({path})", name) for name, path in sorted(jail_files.items())])
        jail_select.value = sorted(jail_files)[0]
        self.query_one("#launch", Button).disabled = False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss()
            return
        if event.button.id != "launch" or not self._jail_files:
            return

        jail_name = str(self.query_one("#jail-select", Select).value)
        conf_file = self._jail_files.get(jail_name, "")
        self.app.push_screen(
            ConfirmScreen(
                title="CONFIRMER LA SUPPRESSION",
                message=f"Supprimer definitivement le jail '{jail_name}' ?\nFichier impacte : {conf_file}",
            ),
            lambda confirmed: self._delete_if_confirmed(confirmed, jail_name),
        )

    def _delete_if_confirmed(self, confirmed: bool | None, jail_name: str) -> None:
        if not confirmed:
            return

        def _execute() -> None:
            if self._fail2ban_port is None:
                raise RuntimeError("Port Fail2ban indisponible (conteneur non initialise).")
            self._fail2ban_port.delete_jail(jail_name)

        def _on_done(_result: None) -> None:
            self.app.notify(f"Jail '{jail_name}' arrete et supprime. Service Fail2ban recharge.")
            log_action_result(self._container, _ACTION_TITLE, status="success")
            self.dismiss()

        def _on_error(error: Exception) -> None:
            self.app.notify(f"Erreur lors de la suppression du jail : {error}", severity="error")
            log_action_result(self._container, _ACTION_TITLE, status="failure", error=str(error))

        self.run_blocking(_execute, _on_done, busy_message=f"Suppression du jail '{jail_name}'...", on_error=_on_error)
