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
from omega_fire.application.queries.foreign_rules import (
    describe_foreign_rules,
    foreign_rules_by_backend,
)
from omega_fire.domain.rules.presets import get_preset, list_presets
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.screens.choice import ChoiceScreen
from omega_fire.interfaces.tui.screens.confirm import ConfirmScreen
from omega_fire.interfaces.tui.support.action_audit import log_action_result
from omega_fire.shared.i18n import _

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ACTION_TITLE = "3.4 Appliquer une politique prédéfinie"


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
            yield Static(_("APPLIQUER UNE POLITIQUE PRÉDÉFINIE"), classes="omega-title")

            if self._active_keys:
                names = [get_preset(k).name if get_preset(k) else k for k in self._active_keys]
                yield Static(_("Profil(s) actif(s) : {value}").format(value=', '.join(names)), classes="omega-hint")
            else:
                yield Static(_("Aucun profil actuellement actif (règles personnalisées)."), classes="omega-hint")

            yield Static(_("Profil"), classes="omega-subtitle")
            presets = list_presets()
            yield Select(
                [(p.name, p.key) for p in presets],
                value=presets[0].key,
                id="preset-select",
            )
            yield Static(presets[0].description, id="preset-detail", classes="omega-hint")

            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Appliquer"), id="launch", variant="error")
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Retour"), id="back")
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
            self.app.notify(_("Profil introuvable."), severity="error")
            return

        available_backends = []
        registry = getattr(self._container, "capability_registry", None)
        if registry is not None:
            if registry.is_available("nftables"):
                available_backends.append("nftables")
            if registry.is_available("iptables"):
                available_backends.append("iptables")
        if not available_backends:
            self.app.notify(_("Aucun backend firewall disponible (nftables/iptables non détectés)."), severity="error")
            return

        adapters = self._firewall_adapters()
        targets = [name for name, adapter in adapters.items() if adapter is not None]

        # Garde-fou (retour utilisateur 2026-10-28) : sur iptables / ip6tables, un
        # profil vide TOUTE la table filter, regles des autres outils comprises.
        # L'utilisateur decide, en sachant ce qu'il efface (detail dans l'aide 3.4).
        foreign = foreign_rules_by_backend(adapters)
        if foreign:
            choices = [(_("Tous les backends — efface ces règles"), "all", "error")]
            if adapters.get("nftables") is not None:
                choices.append((_("Seulement nftables — garde ces règles"), "nftables", "warning"))
            self.app.push_screen(
                ChoiceScreen(
                    title=_("RÈGLES D'AUTRES OUTILS DÉTECTÉES"),
                    message=_(
                        "Le profil « {name} » va remplacer les règles d'Omega-Fire sur : {targets}.\n\n"
                        "Règles d'autres outils trouvées : {detail}.\n\n"
                        "• Tous les backends : sur iptables / ip6tables, le profil vide toute la table "
                        "filter (iptables -F, -X). Ces règles et leurs chaînes sont effacées, la "
                        "politique par défaut devient celle du profil. L'outil ne les repose qu'à son "
                        "prochain rechargement (ex. « ufw reload », redémarrage de Tailscale).\n"
                        "• Seulement nftables : les règles des autres outils restent en place ; les deux "
                        "pare-feu s'appliquent ensemble, un paquet doit être accepté par les deux.\n\n"
                        "Une sauvegarde automatique est tentée avant application. Détails : touche « a »."
                    ).format(name=preset.name, targets=", ".join(targets), detail=describe_foreign_rules(foreign)),
                    choices=choices,
                    help_node="3.4",
                ),
                lambda choice: self._apply_choice(choice, preset, adapters),
            )
            return

        self.app.push_screen(
            ConfirmScreen(
                title=_("CONFIRMER LE BASCULEMENT"),
                message=(
                    _("Le profil '{name}' va REMPLACER toutes les règles actives sur : {value}.\nUne sauvegarde automatique sera tentée avant application.").format(name=preset.name, value=', '.join(targets))
                ),
            ),
            lambda confirmed: self._apply_choice("all" if confirmed else None, preset, adapters),
        )

    def _firewall_adapters(self) -> dict[str, object]:
        adapters: dict[str, object] = {}
        for name in ("nftables", "iptables", "ip6tables"):
            try:
                adapters[name] = self._container.get_firewall_port(name)
            except Exception:
                adapters[name] = None
        return adapters

    def _apply_choice(self, choice: str | None, preset, firewall_adapters: dict[str, object]) -> None:
        if choice not in ("all", "nftables"):
            return

        adapters: dict[str, object] = dict(firewall_adapters)
        if choice == "nftables":
            adapters["iptables"] = adapters["ip6tables"] = None
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
            self.app.notify(_("Échec de l'application du profil : {error}").format(error=error), severity="error")
            log_action_result(self._container, _ACTION_TITLE, status="failure", error=str(error))

        self.run_blocking(_execute, _on_done, busy_message=_("Application du profil en cours..."), on_error=_on_error)
