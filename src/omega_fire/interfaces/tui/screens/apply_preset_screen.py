# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 3.4 — Appliquer une politique pre-definie. Patron #2 (un seul
champ) + confirmation destructive (patron #1). Logique identique a
interfaces/cli/actions.py::action_3_4_apply_preset : le profil choisi
remplace les regles actives sur TOUS les backends detectes, une
sauvegarde automatique est tentee avant application."""
from __future__ import annotations

import json
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Select, Static

from omega_fire.application.commands.apply_preset import state_file_for
from omega_fire.application.commands.apply_preset_all_backends import (
    ApplyPresetAllBackendsRequest,
    ApplyPresetToAllBackendsCommand,
)
from omega_fire.domain.rules.presets import get_preset, list_presets
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.screens.confirm import ConfirmScreen
from omega_fire.interfaces.tui.support.action_audit import log_action_result

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ACTION_TITLE = "3.4 Appliquer une politique predefinie"


def _active_preset_keys(container: DependencyContainer) -> set[str]:
    keys: set[str] = set()
    for backend_name in ("nftables", "iptables", "ip6tables"):
        state_file = state_file_for(backend_name)
        if not state_file.exists():
            continue
        try:
            data = json.loads(state_file.read_text(encoding="utf-8"))
            key = data.get("active_preset")
            if key:
                keys.add(key)
        except Exception:
            continue
    return keys


class ApplyPresetScreen(OmegaScreen):
    """Selection et application d'un profil de regles pre-defini."""

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container
        self._active_keys = _active_preset_keys(container)

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="omega-form-panel"):
            yield Static("APPLIQUER UNE POLITIQUE PREDEFINIE", classes="omega-title")

            if self._active_keys:
                names = [get_preset(k).name if get_preset(k) else k for k in self._active_keys]
                yield Static(f"Profil(s) actif(s) : {', '.join(names)}", classes="omega-hint")
            else:
                yield Static("Aucun profil actuellement actif (regles personnalisees).", classes="omega-hint")

            yield Static("Profil", classes="omega-subtitle")
            presets = list_presets()
            yield Select(
                [(p.name, p.key) for p in presets],
                value=presets[0].key,
                id="preset-select",
            )
            yield Static(presets[0].description, id="preset-detail", classes="omega-hint")

            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button("Appliquer", id="launch", variant="error")
                with Container(classes="omega-btn-frame"):
                    yield Button("Retour", id="back")
        yield Footer()

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id != "preset-select":
            return
        preset = get_preset(str(event.value))
        self.query_one("#preset-detail", Static).update(preset.description if preset else "")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss()
            return
        if event.button.id != "launch":
            return

        key = str(self.query_one("#preset-select", Select).value)
        preset = get_preset(key)
        if preset is None:
            self.app.notify("Profil introuvable.", severity="error")
            return

        available_backends = []
        registry = getattr(self._container, "capability_registry", None)
        if registry is not None:
            if registry.is_available("nftables"):
                available_backends.append("nftables")
            if registry.is_available("iptables"):
                available_backends.append("iptables")
        if not available_backends:
            self.app.notify("Aucun backend firewall disponible (nftables/iptables non detectes).", severity="error")
            return

        self.app.push_screen(
            ConfirmScreen(
                title="CONFIRMER LE BASCULEMENT",
                message=(
                    f"Le profil '{preset.name}' va REMPLACER toutes les regles actives sur : "
                    f"{', '.join(available_backends)}.\nUne sauvegarde automatique sera tentee avant application."
                ),
            ),
            lambda confirmed: self._apply_if_confirmed(confirmed, preset),
        )

    def _apply_if_confirmed(self, confirmed: bool | None, preset) -> None:
        if not confirmed:
            return

        adapters: dict[str, object] = {}
        for name in ("nftables", "iptables", "ip6tables"):
            try:
                adapters[name] = self._container.get_firewall_port(name)
            except Exception:
                adapters[name] = None
        try:
            adapters["fail2ban"] = self._container.get_fail2ban_port()
        except Exception:
            adapters["fail2ban"] = None

        try:
            persistence_port = self._container.get_persistence_port()
        except Exception:
            persistence_port = None
        rule_repository = getattr(self._container, "rule_repository", None)

        def _execute():
            return ApplyPresetToAllBackendsCommand(
                adapters=adapters, persistence_port=persistence_port, rule_repository=rule_repository,
            ).execute(ApplyPresetAllBackendsRequest(preset=preset))

        def _on_done(result) -> None:
            if result.snapshot_warning:
                self.app.notify(result.snapshot_warning, severity="warning")

            any_success = False
            for outcome in result.outcomes:
                if outcome.success:
                    any_success = True
                    self.app.notify(outcome.message, title=outcome.backend, severity="information")
                else:
                    self.app.notify(outcome.message, title=outcome.backend, severity="error")

            log_action_result(self._container, _ACTION_TITLE, status="success" if any_success else "failure")
            self.dismiss()

        def _on_error(error: Exception) -> None:
            self.app.notify(f"Echec de l'application du profil : {error}", severity="error")
            log_action_result(self._container, _ACTION_TITLE, status="failure", error=str(error))

        self.run_blocking(_execute, _on_done, busy_message="Application du profil en cours...", on_error=_on_error)
