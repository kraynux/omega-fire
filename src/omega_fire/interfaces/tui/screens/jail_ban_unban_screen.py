# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 4.2 — Bannir / Debannir dans un jail. Deuxieme ecran de la
Phase 2 : valide le PATRON #3 ("formulaire a champs conditionnels") sur
une action reelle. Logique metier identique a
interfaces/cli/actions.py::action_4_2_jail_ban_unban (choix du jail,
choix ban/debannir, saisie d'IPs ou de numeros d'index pour le
debannissement) — seule la couche presentation change.

Champ conditionnel : le selecteur "IP bannie a reprendre" ne s'affiche
que lorsque l'action choisie est "Debannir" ET que le jail selectionne a
au moins une IP actuellement bannie — meme mecanisme que
omega-check/screens/scan_setup.py (D-008) : widget pre-compose en
classes="omega-hidden", bascule via .set_class() sur on_select_changed,
jamais de montage/demontage dynamique.

La collecte des jails (N+1 appels fail2ban-client : list_jails() puis
get_jail_status() par jail, jusqu'a 10s de timeout chacun) et l'execution
du ban/unban se font en arriere-plan (run_blocking, voir _base.py) — les
faire de facon synchrone dans __init__/compose() ou dans le handler de
confirmation gelait TOUTE l'app (retour utilisateur reel, mode degrade)."""
from __future__ import annotations

import ipaddress
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Input, Select, Static

from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.screens.confirm import ConfirmScreen
from omega_fire.interfaces.tui.support.action_audit import log_action_result
from omega_fire.shared.i18n import _

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ACTION_TITLE = "4.2 Bannir / Debannir dans un jail"
_NO_QUICK_PICK = "__none__"

_HIDDEN_UNTIL_LOADED = (
    "jail-label", "jail-select", "action-label", "action-select", "ips-label", "ips-input",
)


class JailBanUnbanScreen(OmegaScreen):
    """Formulaire de bannissement/debannissement d'IP(s) dans un jail."""

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container
        self._jails_info: dict[str, list[str]] = {}

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(classes="omega-form-panel"):
            yield Static(_("BANNIR / DÉBANNIR DANS UN JAIL"), classes="omega-title")
            yield Static(_("Chargement des jails..."), id="status-hint", classes="omega-hint")

            yield Static(_("Jail"), id="jail-label", classes="omega-subtitle omega-hidden")
            yield Select([], id="jail-select", classes="omega-hidden", prompt=_("Sélectionner"))

            yield Static(_("Action"), id="action-label", classes="omega-subtitle omega-hidden")
            yield Select([(_("Bannir"), "ban"), (_("Débannir"), "unban")], value="ban", id="action-select", classes="omega-hidden")

            yield Static(_("IP bannie à reprendre (optionnel)"), id="quick-pick-label", classes="omega-hidden")
            yield Select([], id="quick-pick-select", classes="omega-hidden", prompt=_("Sélectionner"))

            yield Static(_("Adresse(s) IP"), id="ips-label", classes="omega-subtitle omega-hidden")
            yield Input(
                placeholder=_("ex. 10.0.0.5, 10.0.0.6  (ou numéros d'index en débannissement)"),
                id="ips-input", classes="omega-hidden",
            )

            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Exécuter"), id="launch", variant="primary", disabled=True)
                with Container(classes="omega-btn-frame"):
                    yield Button(_("Retour"), id="back")
        yield Footer()

    def on_mount(self) -> None:
        self.run_blocking(self._collect_jails, self._on_loaded, busy_message=_("Chargement des jails..."))

    def _collect_jails(self) -> dict[str, list[str]]:
        try:
            fail2ban_port = self._container.get_fail2ban_port()
        except Exception:
            return {}
        if not fail2ban_port:
            return {}
        jails: dict[str, list[str]] = {}
        try:
            for name in fail2ban_port.list_jails():
                try:
                    status = fail2ban_port.get_jail_status(name)
                except Exception:
                    status = {}
                jails[name] = list(status.get("banned_ips", []))
        except Exception:
            return {}
        return jails

    def _on_loaded(self, jails_info: dict[str, list[str]]) -> None:
        self._jails_info = jails_info
        hint = self.query_one("#status-hint", Static)

        if not jails_info:
            hint.update(_("Impossible de communiquer avec le service Fail2ban (aucun jail détecté)."))
            return

        hint.set_class(True, "omega-hidden")
        for widget_id in _HIDDEN_UNTIL_LOADED:
            self.query_one(f"#{widget_id}").set_class(False, "omega-hidden")

        jail_select = self.query_one("#jail-select", Select)
        jail_select.set_options([(_("{name} ({count} bannie(s))").format(name=name, count=len(ips)), name) for name, ips in jails_info.items()])
        jail_select.value = next(iter(jails_info))

        self.query_one("#launch", Button).disabled = False
        self._refresh_quick_pick()

    def on_select_changed(self, event: Select.Changed) -> None:
        if not self._jails_info:
            return
        if event.select.id in ("jail-select", "action-select"):
            self._refresh_quick_pick()
            return
        if event.select.id == "quick-pick-select" and event.value != _NO_QUICK_PICK:
            ips_input = self.query_one("#ips-input", Input)
            existing = [i.strip() for i in ips_input.value.split(",") if i.strip()]
            picked = str(event.value)
            if picked not in existing:
                existing.append(picked)
            ips_input.value = ", ".join(existing)

    def _refresh_quick_pick(self) -> None:
        jail_name = str(self.query_one("#jail-select", Select).value)
        action = str(self.query_one("#action-select", Select).value)
        banned_ips = self._jails_info.get(jail_name, [])

        show_quick_pick = action == "unban" and bool(banned_ips)
        self.query_one("#quick-pick-label", Static).set_class(not show_quick_pick, "omega-hidden")
        quick_pick = self.query_one("#quick-pick-select", Select)
        quick_pick.set_class(not show_quick_pick, "omega-hidden")

        if show_quick_pick:
            quick_pick.set_options(
                [(_("(choisir une IP bannie)"), _NO_QUICK_PICK)] + [(ip, ip) for ip in banned_ips]
            )
            quick_pick.value = _NO_QUICK_PICK

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss()
            return
        if event.button.id != "launch" or not self._jails_info:
            return

        jail_name = str(self.query_one("#jail-select", Select).value)
        action_type = str(self.query_one("#action-select", Select).value)
        currently_banned = self._jails_info.get(jail_name, [])

        raw_input = self.query_one("#ips-input", Input).value.strip()
        if not raw_input:
            self.app.notify(_("Saisissez au moins une IP (ou un numéro d'index)."), severity="warning")
            return

        raw_items = [item.strip() for item in raw_input.split(",") if item.strip()]
        target_ips: list[str] = []
        for item in raw_items:
            resolved_ip = item
            if action_type == "unban" and item.isdigit():
                num_idx = int(item) - 1
                if 0 <= num_idx < len(currently_banned):
                    resolved_ip = currently_banned[num_idx]
                else:
                    self.app.notify(
                        _("Le numéro [{item}] ne correspond a aucune IP bannie dans '{jail_name}' — ignore.").format(item=item, jail_name=jail_name),
                        severity="warning",
                    )
                    continue
            try:
                ipaddress.ip_address(resolved_ip)
            except ValueError:
                self.app.notify(_("Format d'adresse IP invalide : '{item}' — ignore.").format(item=item), severity="warning")
                continue
            if resolved_ip not in target_ips:
                target_ips.append(resolved_ip)

        if not target_ips:
            self.app.notify(_("Aucune entrée valide dans la saisie."), severity="warning")
            return

        action_verb = "bannir" if action_type == "ban" else "debannir"
        self.app.push_screen(
            ConfirmScreen(
                title=_("CONFIRMER L'ACTION"),
                message=_("Jail : {jail_name}\nAction : {action_verb}\nIP(s) : {value}").format(jail_name=jail_name, action_verb=action_verb, value=', '.join(target_ips)),
            ),
            lambda confirmed: self._execute_if_confirmed(confirmed, jail_name, action_type, target_ips),
        )

    def _execute_if_confirmed(
        self, confirmed: bool | None, jail_name: str, action_type: str, target_ips: list[str]
    ) -> None:
        if not confirmed:
            return

        def _execute() -> tuple[list[tuple[str, str]], int, int]:
            fail2ban_port = self._container.get_fail2ban_port()
            banned_set = set(self._jails_info.get(jail_name, []))
            notifications: list[tuple[str, str]] = []
            success_count = 0
            skipped_count = 0

            for ip in target_ips:
                if action_type == "ban" and ip in banned_set:
                    notifications.append((_("IP {ip} : déjà bannie dans '{jail_name}'.").format(ip=ip, jail_name=jail_name), "warning"))
                    skipped_count += 1
                    continue
                if action_type == "unban" and ip not in banned_set:
                    notifications.append((_("IP {ip} : absente de la liste des bannis du jail '{jail_name}'.").format(ip=ip, jail_name=jail_name), "warning"))
                    skipped_count += 1
                    continue

                executed_successfully = False
                error_detail = ""
                try:
                    if action_type == "ban":
                        from omega_fire.application.commands.jail_ban import JailBanCommand, JailBanRequest
                        cmd_result = JailBanCommand(fail2ban_port).execute(
                            JailBanRequest(jail_name=jail_name, ip=ip)
                        )
                    else:
                        from omega_fire.application.commands.jail_unban import JailUnbanCommand, JailUnbanRequest
                        cmd_result = JailUnbanCommand(fail2ban_port).execute(
                            JailUnbanRequest(jail_name=jail_name, ip=ip)
                        )
                    executed_successfully = cmd_result.success
                    error_detail = cmd_result.message or ""
                except Exception as e:
                    executed_successfully = False
                    error_detail = str(e)

                if executed_successfully:
                    msg_action = "bannie" if action_type == "ban" else "debannie"
                    notifications.append((_("IP {ip} {msg_action} avec succès dans '{jail_name}'.").format(ip=ip, msg_action=msg_action, jail_name=jail_name), "information"))
                    success_count += 1
                else:
                    suffix = f" ({error_detail})" if error_detail else ""
                    notifications.append((_("IP {ip} : échec de l'action Fail2ban.{suffix}").format(ip=ip, suffix=suffix), "error"))

            return notifications, success_count, skipped_count

        def _on_done(result: tuple[list[tuple[str, str]], int, int]) -> None:
            notifications, success_count, skipped_count = result
            for message, severity in notifications:
                self.app.notify(message, severity=severity)
            self.app.notify(_("Bilan : {success_count} IP(s) traitée(s), {skipped_count} ignorée(s).").format(success_count=success_count, skipped_count=skipped_count), title=jail_name)
            log_action_result(self._container, _ACTION_TITLE, status="success" if success_count else "failure")
            self.dismiss()

        busy_label = _("Bannissement") if action_type == "ban" else _("Débannissement")
        self.run_blocking(_execute, _on_done, busy_message=_("{busy_label} en cours...").format(busy_label=busy_label))
