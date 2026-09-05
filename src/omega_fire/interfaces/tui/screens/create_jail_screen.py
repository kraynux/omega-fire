# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 4.4 — Creer un jail Fail2ban. Le wizard le plus profond du CLI
(15 prompts sequentiels dans son chemin le plus long) — reduit ici a un
formulaire avec deux branches conditionnelles (patron #3) : "Sur-mesure"
(nom + source de log + ports + filtre + regles de bannissement) ou
"Modele/Preset" (choix dans une liste geree via JailPresetsScreen).
Logique identique a interfaces/cli/actions.py::action_4_4_create_jail.

get_jail_status() (verification des noms existants) et l'installation du
jail (write_filter()/create_jail(), qui recharge le service — fail2ban-
client, jusqu'a 10s de timeout chacun) s'executent en arriere-plan
(run_blocking, voir _base.py) — synchrones, elles gelaient TOUTE l'app
(retour utilisateur reel, mode degrade)."""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Footer, Header, Input, Select, Static

from omega_fire.application.commands.manage_jail_presets import ManageJailPresetsCommand
from omega_fire.application.commands.manage_pinned_log_paths import ManagePinnedLogPathsCommand
from omega_fire.application.queries.jail_status import get_jail_status
from omega_fire.domain.fail2ban.filters import generate_default_http_filter
from omega_fire.infrastructure.config.paths import DEFAULT_PINNED_FILES, RUNTIME_DIR
from omega_fire.infrastructure.storage.files.json_store import JsonStore
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.screens.confirm import ConfirmScreen
from omega_fire.interfaces.tui.screens.jail_presets_screen import JailPresetsScreen
from omega_fire.interfaces.tui.screens.pinned_paths_screen import PinnedPathsScreen
from omega_fire.interfaces.tui.support.action_audit import log_action_result

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ACTION_TITLE = "4.4 Creation et configuration de Jail Fail2ban"
_MODE_CUSTOM = "custom"
_MODE_PRESET = "preset"
_LOG_MANUAL = "__manual__"


class CreateJailScreen(OmegaScreen):
    """Creation et activation d'un nouveau jail Fail2ban."""

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container
        try:
            self._fail2ban_port = container.get_fail2ban_port()
        except Exception:
            self._fail2ban_port = None
        self._existing_names: set[str] = set()
        self._names_loaded = False
        self._pinned_command = ManagePinnedLogPathsCommand(
            JsonStore(RUNTIME_DIR),
            relative_path="blocklist_analysis_pinned_paths.json",
            defaults=[str(p) for p in DEFAULT_PINNED_FILES],
        )
        self._preset_command = ManageJailPresetsCommand(JsonStore(RUNTIME_DIR))

    def _preset_options(self) -> list[tuple[str, str]]:
        return [(f"{p['name']} — {p['desc']}", p["name"]) for p in self._preset_command.list_presets()]

    def _log_options(self) -> list[tuple[str, str]]:
        return [(p, p) for p in self._pinned_command.list_paths()] + [("Chemin manuel", _LOG_MANUAL)]

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(classes="omega-form-panel"):
            yield Static("CREER UN JAIL FAIL2BAN", classes="omega-title")
            if self._fail2ban_port is None:
                yield Static("Port Fail2ban indisponible (conteneur non initialise).", classes="omega-hint")
                with Horizontal(classes="omega-actions"), Container(classes="omega-btn-frame"):
                    yield Button("Retour", id="back")
                yield Footer()
                return

            yield Static("Mode de creation", classes="omega-subtitle")
            yield Select(
                [("Sur-mesure (assistant)", _MODE_CUSTOM), ("Modele / Preset", _MODE_PRESET)],
                value=_MODE_CUSTOM,
                id="mode-select",
            )

            # --- Bloc PRESET ---
            yield Static("Modele", id="preset-label", classes="omega-subtitle omega-hidden")
            yield Select(self._preset_options(), id="preset-select", classes="omega-hidden")
            with Horizontal(classes="omega-actions", id="preset-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button("Gerer les modeles", id="manage-presets")

            # --- Bloc SUR-MESURE ---
            yield Static("Nom du jail", id="name-label", classes="omega-subtitle")
            yield Input(placeholder="ex. my-app-jail", id="name-input")

            yield Static("Source du log a surveiller", id="log-source-label", classes="omega-subtitle")
            yield Select(self._log_options(), id="log-select")
            with Horizontal(classes="omega-actions", id="pins-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button("Gerer les epingles", id="manage-pins")
            yield Static("Chemin manuel", id="log-manual-label", classes="omega-subtitle omega-hidden")
            yield Input(id="log-manual-input", classes="omega-hidden")

            yield Static("Ports concernes", id="port-label", classes="omega-subtitle")
            yield Input(value="http,https", id="port-input")

            yield Static("Nom du filtre Fail2ban (vide = identique au nom du jail)", id="filter-label", classes="omega-subtitle")
            yield Input(id="filter-input")

            yield Static("Max Retry", id="retry-label", classes="omega-subtitle")
            yield Input(value="5", id="retry-input")
            yield Static("Findtime", id="find-label", classes="omega-subtitle")
            yield Input(value="10m", id="find-input")
            yield Static("Bantime", id="ban-label", classes="omega-subtitle")
            yield Input(value="1h", id="ban-input")

            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button("Creer le jail", id="launch", variant="primary", disabled=True)
                with Container(classes="omega-btn-frame"):
                    yield Button("Retour", id="back")
        yield Footer()

    def on_mount(self) -> None:
        if self._fail2ban_port is None:
            return
        log_options = self._log_options()
        if log_options:
            self.query_one("#log-select", Select).value = log_options[0][1]
        preset_options = self._preset_options()
        if preset_options:
            self.query_one("#preset-select", Select).value = preset_options[0][1]
        self._apply_mode(_MODE_CUSTOM)

        def _fetch_existing_names() -> set[str]:
            status = get_jail_status(fail2ban_port=self._fail2ban_port)
            return {j.name.lower() for j in status.jails}

        self.run_blocking(_fetch_existing_names, self._on_names_loaded, busy_message="Verification des jails existants...")

    def _on_names_loaded(self, existing_names: set[str]) -> None:
        self._existing_names = existing_names
        self._names_loaded = True
        self.query_one("#launch", Button).disabled = False

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "mode-select":
            self._apply_mode(str(event.value))
        elif event.select.id == "log-select":
            is_manual = str(event.value) == _LOG_MANUAL
            self.query_one("#log-manual-label", Static).set_class(not is_manual, "omega-hidden")
            self.query_one("#log-manual-input", Input).set_class(not is_manual, "omega-hidden")

    def _apply_mode(self, mode: str) -> None:
        is_preset = mode == _MODE_PRESET
        self.query_one("#preset-label", Static).set_class(not is_preset, "omega-hidden")
        self.query_one("#preset-select", Select).set_class(not is_preset, "omega-hidden")
        self.query_one("#preset-actions", Horizontal).set_class(not is_preset, "omega-hidden")

        for widget_id in (
            "name-label", "name-input", "log-source-label", "log-select", "pins-actions",
            "port-label", "port-input", "filter-label", "filter-input",
            "retry-label", "retry-input", "find-label", "find-input", "ban-label", "ban-input",
        ):
            self.query_one(f"#{widget_id}").set_class(is_preset, "omega-hidden")

        if not is_preset:
            log_select = str(self.query_one("#log-select", Select).value)
            is_manual = log_select == _LOG_MANUAL
            self.query_one("#log-manual-label", Static).set_class(not is_manual, "omega-hidden")
            self.query_one("#log-manual-input", Input).set_class(not is_manual, "omega-hidden")
        else:
            self.query_one("#log-manual-label", Static).set_class(True, "omega-hidden")
            self.query_one("#log-manual-input", Input).set_class(True, "omega-hidden")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss()
            return
        if event.button.id == "manage-presets":
            self.app.push_screen(JailPresetsScreen(container=self._container), self._refresh_preset_select)
            return
        if event.button.id == "manage-pins":
            self.app.push_screen(PinnedPathsScreen(container=self._container), self._refresh_log_select)
            return
        if event.button.id != "launch":
            return
        self._launch()

    def _refresh_preset_select(self, _result: None) -> None:
        self.query_one("#preset-select", Select).set_options(self._preset_options())

    def _refresh_log_select(self, _result: None) -> None:
        self.query_one("#log-select", Select).set_options(self._log_options())

    def _launch(self) -> None:
        if not self._names_loaded:
            self.app.notify("Verification des jails existants encore en cours, patientez.", severity="warning")
            return
        mode = str(self.query_one("#mode-select", Select).value)

        if mode == _MODE_PRESET:
            preset_name = self.query_one("#preset-select", Select).value
            if preset_name is None or preset_name == Select.BLANK:
                self.app.notify("Aucun modele disponible ou selectionne.", severity="warning")
                return
            preset = next((p for p in self._preset_command.list_presets() if p["name"] == str(preset_name)), None)
            if preset is None:
                self.app.notify("Modele introuvable.", severity="error")
                return
            jail_name = preset["name"]
            if jail_name.lower() in self._existing_names:
                jail_name = f"{jail_name}-custom"
            log_path = preset["log"]
            filter_name = preset["filter"]
            port_spec = preset["port"]
            max_retry = preset["retry"]
            find_time = preset["find"]
            ban_time = preset["ban"]
        else:
            jail_name = self.query_one("#name-input", Input).value.strip()
            if not jail_name:
                self.app.notify("Le nom du jail est requis.", severity="warning")
                return
            if jail_name.lower() in self._existing_names:
                self.app.notify(f"Un jail nomme '{jail_name}' existe deja.", severity="error")
                return
            jail_name = re.sub(r"[^a-zA-Z0-9_-]", "", jail_name)

            log_select = self.query_one("#log-select", Select).value
            if log_select == _LOG_MANUAL or log_select is None or log_select == Select.BLANK:
                log_path = self.query_one("#log-manual-input", Input).value.strip()
            else:
                log_path = str(log_select)
            if not log_path:
                self.app.notify("Le chemin du log est requis.", severity="warning")
                return

            port_spec = self.query_one("#port-input", Input).value.strip() or "http,https"
            filter_name = self.query_one("#filter-input", Input).value.strip() or jail_name
            max_retry = self.query_one("#retry-input", Input).value.strip() or "5"
            find_time = self.query_one("#find-input", Input).value.strip() or "10m"
            ban_time = self.query_one("#ban-input", Input).value.strip() or "1h"

        config_filepath = f"/etc/fail2ban/jail.d/{jail_name}.conf"
        summary = (
            f"Nom : {jail_name}\nFichier : {config_filepath}\nLog : {log_path}\n"
            f"Ports : {port_spec}\nFiltre : {filter_name}\n"
            f"Max Retry : {max_retry} | Findtime : {find_time} | Bantime : {ban_time}"
        )
        self.app.push_screen(
            ConfirmScreen(title="CONFIRMER LA CREATION DU JAIL", message=summary),
            lambda confirmed: self._create_if_confirmed(
                confirmed, jail_name, log_path, filter_name, port_spec, max_retry, find_time, ban_time, config_filepath,
            ),
        )

    def _create_if_confirmed(
        self, confirmed: bool | None, jail_name: str, log_path: str, filter_name: str,
        port_spec: str, max_retry: str, find_time: str, ban_time: str, config_filepath: str,
    ) -> None:
        if not confirmed:
            return

        def _execute():
            filter_content = generate_default_http_filter(jail_name)
            filter_written = self._fail2ban_port.write_filter(filter_name, filter_content)
            created_info = self._fail2ban_port.create_jail(
                jail_name, filter_name, log_path,
                max_retry=max_retry, ban_time=ban_time, find_time=find_time, port=port_spec,
            )
            return filter_written, created_info

        def _on_done(result) -> None:
            filter_written, created_info = result
            if filter_written:
                self.app.notify(f"Filtre automatique cree dans '/etc/fail2ban/filter.d/{filter_name}.conf'.")

            self.app.notify(f"Configuration jail enregistree dans '{config_filepath}'.")
            if created_info.active:
                self.app.notify(f"Service Fail2ban recharge. Le jail '{jail_name}' est desormais ACTIF.")
            else:
                self.app.notify(f"Configuration ecrite mais le jail '{jail_name}' n'apparait pas encore actif.", severity="warning")

            log_action_result(self._container, _ACTION_TITLE, status="success")
            self.dismiss()

        def _on_error(error: Exception) -> None:
            self.app.notify(f"Erreur lors de l'installation du jail : {error}", severity="error")
            log_action_result(self._container, _ACTION_TITLE, status="failure", error=str(error))

        self.run_blocking(_execute, _on_done, busy_message=f"Creation du jail '{jail_name}'...", on_error=_on_error)
