# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ecran 4.3 / 2.10 — Transfert / Import / Export IPs (Jails, Backends,
Fichiers & Epingles). La fonction CLI la plus volumineuse du projet
(929 lignes, 7 sources x 7 destinations) — reduite ici a UN formulaire
avec deux groupes de champs conditionnels (source, destination), chacun
reutilisant les patrons deja etablis (jail/fichier/epingle, gestion des
epingles via PinnedPathsScreen). Logique identique a
interfaces/cli/actions.py::action_4_3_jail_transfer, execution comprise
(CAS A a E : jail/fichier/nftables/iptables/ip6tables).

get_jail_status() (a l'ouverture) et la collecte+transfert complet (au
clic sur "Lancer" — fail2ban-client/backends, jusqu'a 10s de timeout par
appel) s'executent en arriere-plan (run_blocking, voir _base.py) —
synchrones, ils gelaient TOUTE l'app (retour utilisateur reel, mode
degrade). Notify()/query_one() en lecture restent utilisables depuis ce
thread (verifie empiriquement), inutile de faire remonter chaque valeur
saisie via des parametres explicites comme pour d'autres ecrans plus
courts de ce lot."""
from __future__ import annotations

import os
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Footer, Header, Input, Select, Static

from omega_fire.application.commands.manage_pinned_log_paths import ManagePinnedLogPathsCommand
from omega_fire.application.queries.jail_status import get_jail_status
from omega_fire.domain.ip_blacklist.exceptions import IPAlreadyBannedError
from omega_fire.infrastructure.config.paths import (
    DEFAULT_BLOCKLIST_FILE,
    DEFAULT_F2B_BLOCKLIST_FILE,
    DEFAULT_PINNED_FILES,
    RUNTIME_DIR,
)
from omega_fire.infrastructure.storage.files.json_store import JsonStore
from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.interfaces.tui.screens.ban_ip_list_screen import _extract_valid_ips
from omega_fire.interfaces.tui.screens.pinned_paths_screen import PinnedPathsScreen
from omega_fire.interfaces.tui.support.action_audit import log_action_result
from omega_fire.shared.networking import IPAddress

if TYPE_CHECKING:
    from omega_fire.app.dependency_container import DependencyContainer

_ACTION_TITLE = "4.3 Transfert / Import / Export IPs (Jails, Backends, Fichiers)"

_SRC_JAIL = "jail"
_SRC_NFTABLES = "nftables"
_SRC_IPTABLES = "iptables"
_SRC_MANUAL = "manual"
_SRC_PINNED = "pinned"
_SRC_ALL = "all"
_SRC_IP6TABLES = "ip6tables"

_DST_JAIL = "jail"
_DST_NFTABLES = "nftables"
_DST_IPTABLES = "iptables"
_DST_DEFAULT_FILE = "default_file"
_DST_MANUAL = "manual"
_DST_PINNED = "pinned"
_DST_IP6TABLES = "ip6tables"


class JailTransferScreen(OmegaScreen):
    """Collecte des IPs depuis une source, transfert vers une destination."""

    def __init__(self, *, container: DependencyContainer) -> None:
        super().__init__()
        self._container = container

        try:
            self._fail2ban_port = container.get_fail2ban_port()
        except Exception:
            self._fail2ban_port = None
        try:
            self._nftables_port = container.get_firewall_port("nftables")
        except Exception:
            self._nftables_port = None
        try:
            self._iptables_port = container.get_firewall_port("iptables")
        except Exception:
            self._iptables_port = None
        try:
            self._ip6tables_port = container.get_firewall_port("ip6tables")
        except Exception:
            self._ip6tables_port = None

        self._jails_info: dict[str, list[str]] = {}

        self._pinned_command = ManagePinnedLogPathsCommand(
            JsonStore(RUNTIME_DIR),
            relative_path="blocklist_analysis_pinned_paths.json",
            defaults=[str(p) for p in DEFAULT_PINNED_FILES],
        )

    def _pinned_options(self) -> list[tuple[str, str]]:
        return [(p, p) for p in self._pinned_command.list_paths()]

    def _jail_options(self) -> list[tuple[str, str]]:
        return [(f"{name} ({len(ips)} IP(s))", name) for name, ips in self._jails_info.items()]

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(classes="omega-form-panel"):
            yield Static("TRANSFERT / INTEROPERABILITE DES IPs", classes="omega-title")

            # --- SOURCE ---
            yield Static("Source de collecte", classes="omega-subtitle")
            yield Select(
                [
                    ("Jail Fail2ban (temps reel)", _SRC_JAIL),
                    ("Pare-feu nftables (set blackhole)", _SRC_NFTABLES),
                    ("Pare-feu iptables (chaine INPUT)", _SRC_IPTABLES),
                    ("Pare-feu ip6tables (chaine INPUT)", _SRC_IP6TABLES),
                    ("Fichier texte / chemin manuel", _SRC_MANUAL),
                    ("Fichier epingle", _SRC_PINNED),
                    ("Tous les backends reunis (nft, ipt, ip6t, jails)", _SRC_ALL),
                ],
                value=_SRC_JAIL,
                id="source-select",
            )
            yield Static("Jail source", id="source-jail-label", classes="omega-subtitle")
            yield Select(self._jail_options(), id="source-jail-select")
            yield Static("Chemin du fichier", id="source-manual-label", classes="omega-subtitle omega-hidden")
            yield Input(id="source-manual-input", classes="omega-hidden")
            yield Static("Fichier epingle", id="source-pinned-label", classes="omega-subtitle omega-hidden")
            yield Select(self._pinned_options(), id="source-pinned-select", classes="omega-hidden")
            with Horizontal(classes="omega-actions", id="source-pins-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button("Gerer les epingles (source)", id="manage-source-pins")

            # --- DESTINATION ---
            yield Static("Destination", classes="omega-subtitle")
            yield Select(
                [
                    ("Jail Fail2ban (bannir dans un jail actif)", _DST_JAIL),
                    ("Pare-feu nftables (set blackhole)", _DST_NFTABLES),
                    ("Pare-feu iptables (chaine INPUT)", _DST_IPTABLES),
                    ("Pare-feu ip6tables (chaine INPUT)", _DST_IP6TABLES),
                    (f"Fichier texte par defaut ({DEFAULT_F2B_BLOCKLIST_FILE.name})", _DST_DEFAULT_FILE),
                    ("Chemin manuel personnalise", _DST_MANUAL),
                    ("Fichier epingle", _DST_PINNED),
                ],
                value=_DST_JAIL,
                id="dest-select",
            )
            yield Static("Jail destination", id="dest-jail-label", classes="omega-subtitle")
            yield Select(self._jail_options(), id="dest-jail-select")
            yield Static("Chemin du fichier", id="dest-manual-label", classes="omega-subtitle omega-hidden")
            yield Input(id="dest-manual-input", classes="omega-hidden")
            yield Static("Fichier epingle", id="dest-pinned-label", classes="omega-subtitle omega-hidden")
            yield Select(self._pinned_options(), id="dest-pinned-select", classes="omega-hidden")
            with Horizontal(classes="omega-actions", id="dest-pins-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button("Gerer les epingles (destination)", id="manage-dest-pins")

            yield Static("Mode d'ecriture (fichier)", id="file-mode-label", classes="omega-subtitle omega-hidden")
            yield Select(
                [("Ecraser", "overwrite"), ("Rajouter (brut)", "append"), ("Incrementer (nouvelles IP uniquement)", "increment")],
                value="increment",
                id="file-mode-select",
                classes="omega-hidden",
            )
            yield Static("Mode d'injection (iptables/ip6tables)", id="ipt-mode-label", classes="omega-subtitle omega-hidden")
            yield Select(
                [("Reinitialiser / ecraser la chaine", "flush"), ("Incrementer (nouvelles IP uniquement)", "increment")],
                value="increment",
                id="ipt-mode-select",
                classes="omega-hidden",
            )

            with Horizontal(classes="omega-actions"):
                with Container(classes="omega-btn-frame"):
                    yield Button("Transferer", id="launch", variant="primary", disabled=True)
                with Container(classes="omega-btn-frame"):
                    yield Button("Retour", id="back")
        yield Footer()

    def on_mount(self) -> None:
        pinned_options = self._pinned_options()
        if pinned_options:
            self.query_one("#source-pinned-select", Select).value = pinned_options[0][1]
            self.query_one("#dest-pinned-select", Select).value = pinned_options[0][1]
        self._apply_source(_SRC_JAIL)
        self._apply_dest(_DST_JAIL)

        def _fetch_jails() -> dict[str, list[str]]:
            status = get_jail_status(fail2ban_port=self._fail2ban_port)
            return {j.name: sorted({str(ip) for ip in j.banned_ips}) for j in status.jails}

        self.run_blocking(_fetch_jails, self._on_jails_loaded, busy_message="Chargement des jails...")

    def _on_jails_loaded(self, jails_info: dict[str, list[str]]) -> None:
        self._jails_info = jails_info
        jail_options = self._jail_options()
        if jail_options:
            self.query_one("#source-jail-select", Select).set_options(jail_options)
            self.query_one("#source-jail-select", Select).value = jail_options[0][1]
            self.query_one("#dest-jail-select", Select).set_options(jail_options)
            self.query_one("#dest-jail-select", Select).value = jail_options[0][1]
        self.query_one("#launch", Button).disabled = False

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "source-select":
            self._apply_source(str(event.value))
        elif event.select.id == "dest-select":
            self._apply_dest(str(event.value))

    def _apply_source(self, source: str) -> None:
        is_jail = source == _SRC_JAIL
        is_manual = source == _SRC_MANUAL
        is_pinned = source == _SRC_PINNED
        self.query_one("#source-jail-label", Static).set_class(not is_jail, "omega-hidden")
        self.query_one("#source-jail-select", Select).set_class(not is_jail, "omega-hidden")
        self.query_one("#source-manual-label", Static).set_class(not is_manual, "omega-hidden")
        self.query_one("#source-manual-input", Input).set_class(not is_manual, "omega-hidden")
        self.query_one("#source-pinned-label", Static).set_class(not is_pinned, "omega-hidden")
        self.query_one("#source-pinned-select", Select).set_class(not is_pinned, "omega-hidden")
        self.query_one("#source-pins-actions", Horizontal).set_class(not is_pinned, "omega-hidden")

    def _apply_dest(self, dest: str) -> None:
        is_jail = dest == _DST_JAIL
        is_manual = dest == _DST_MANUAL
        is_pinned = dest == _DST_PINNED
        is_file = dest in (_DST_DEFAULT_FILE, _DST_MANUAL, _DST_PINNED)
        is_ipt = dest in (_DST_IPTABLES, _DST_IP6TABLES)

        self.query_one("#dest-jail-label", Static).set_class(not is_jail, "omega-hidden")
        self.query_one("#dest-jail-select", Select).set_class(not is_jail, "omega-hidden")
        self.query_one("#dest-manual-label", Static).set_class(not is_manual, "omega-hidden")
        self.query_one("#dest-manual-input", Input).set_class(not is_manual, "omega-hidden")
        self.query_one("#dest-pinned-label", Static).set_class(not is_pinned, "omega-hidden")
        self.query_one("#dest-pinned-select", Select).set_class(not is_pinned, "omega-hidden")
        self.query_one("#dest-pins-actions", Horizontal).set_class(not is_pinned, "omega-hidden")
        self.query_one("#file-mode-label", Static).set_class(not is_file, "omega-hidden")
        self.query_one("#file-mode-select", Select).set_class(not is_file, "omega-hidden")
        self.query_one("#ipt-mode-label", Static).set_class(not is_ipt, "omega-hidden")
        self.query_one("#ipt-mode-select", Select).set_class(not is_ipt, "omega-hidden")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.dismiss()
            return
        if event.button.id == "manage-source-pins":
            self.app.push_screen(PinnedPathsScreen(container=self._container), self._refresh_source_pinned)
            return
        if event.button.id == "manage-dest-pins":
            self.app.push_screen(PinnedPathsScreen(container=self._container), self._refresh_dest_pinned)
            return
        if event.button.id != "launch":
            return
        self._launch()

    def _refresh_source_pinned(self, _result: None) -> None:
        self.query_one("#source-pinned-select", Select).set_options(self._pinned_options())

    def _refresh_dest_pinned(self, _result: None) -> None:
        self.query_one("#dest-pinned-select", Select).set_options(self._pinned_options())

    # ------------------------------------------------------------------
    # Collecte depuis la source
    # ------------------------------------------------------------------
    def _collect_from_source(self) -> tuple[set[str], str] | None:
        source = str(self.query_one("#source-select", Select).value)

        if source == _SRC_JAIL:
            jail_name = self.query_one("#source-jail-select", Select).value
            if jail_name is None or jail_name == Select.BLANK:
                self.app.notify("Aucun jail disponible ou selectionne.", severity="warning")
                return None
            return set(self._jails_info.get(str(jail_name), [])), f"Jail '{jail_name}'"

        if source == _SRC_NFTABLES:
            if self._nftables_port is None:
                self.app.notify("Port nftables indisponible.", severity="error")
                return None
            return {b.ip for b in self._nftables_port.list_bans()}, "Pare-feu nftables (blackhole)"

        if source == _SRC_IPTABLES:
            if self._iptables_port is None:
                self.app.notify("Port iptables indisponible.", severity="error")
                return None
            return {b.ip.split("/")[0] for b in self._iptables_port.list_bans()}, "Pare-feu iptables (INPUT)"

        if source == _SRC_IP6TABLES:
            if self._ip6tables_port is None:
                self.app.notify("Port ip6tables indisponible.", severity="error")
                return None
            return {b.ip.split("/")[0] for b in self._ip6tables_port.list_bans()}, "Pare-feu ip6tables (INPUT)"

        if source == _SRC_MANUAL:
            src_file = self.query_one("#source-manual-input", Input).value.strip()
            if not src_file or not os.path.exists(src_file):
                self.app.notify(f"Fichier source '{src_file}' introuvable.", severity="error")
                return None
            with open(src_file, "r", encoding="utf-8") as f:
                return _extract_valid_ips(f.read()), f"Fichier '{src_file}'"

        if source == _SRC_PINNED:
            src_file = self.query_one("#source-pinned-select", Select).value
            if src_file is None or src_file == Select.BLANK or not os.path.exists(str(src_file)):
                self.app.notify("Fichier epingle introuvable ou non selectionne.", severity="error")
                return None
            with open(str(src_file), "r", encoding="utf-8") as f:
                return _extract_valid_ips(f.read()), f"Epingle '{src_file}'"

        if source == _SRC_ALL:
            collected: set[str] = set()
            for ips in self._jails_info.values():
                collected.update(ips)
            if self._nftables_port is not None:
                try:
                    collected.update(b.ip for b in self._nftables_port.list_bans())
                except Exception:
                    pass
            if self._iptables_port is not None:
                try:
                    collected.update(b.ip.split("/")[0] for b in self._iptables_port.list_bans())
                except Exception:
                    pass
            if self._ip6tables_port is not None:
                try:
                    collected.update(b.ip.split("/")[0] for b in self._ip6tables_port.list_bans())
                except Exception:
                    pass
            return collected, "Tous les backends reunis"

        return None

    def _launch(self) -> None:
        # _collect_from_source()/_execute_transfer() appellent fail2ban-
        # client et/ou les backends nftables/iptables/ip6tables (jusqu'a
        # 10s de timeout chacun) — le tout execute en arriere-plan
        # (run_blocking) pour ne pas geler l'app le temps du transfert.
        # notify()/query_one() en lecture sont surs depuis ce thread
        # (verifie empiriquement, voir docstring du fichier).
        def _work() -> None:
            collected = self._collect_from_source()
            if collected is None:
                return
            collected_ips, source_label = collected
            banned_ips = sorted(collected_ips)
            if not banned_ips:
                self.app.notify(f"La source {source_label} ne contient aucune IP bannie a transferer.", severity="warning")
                return

            dest = str(self.query_one("#dest-select", Select).value)
            self._execute_transfer(dest, banned_ips, source_label)

        self.run_blocking(_work, lambda _r: None, busy_message="Transfert en cours...")

    # ------------------------------------------------------------------
    # Execution vers la destination
    # ------------------------------------------------------------------
    def _execute_transfer(self, dest: str, banned_ips: list[str], source_label: str) -> None:
        if dest == _DST_JAIL:
            jail_name = self.query_one("#dest-jail-select", Select).value
            if jail_name is None or jail_name == Select.BLANK:
                self.app.notify("Aucun jail disponible ou selectionne.", severity="warning")
                return
            self._transfer_to_jail(str(jail_name), banned_ips, source_label)
            return

        if dest in (_DST_DEFAULT_FILE, _DST_MANUAL, _DST_PINNED):
            if dest == _DST_DEFAULT_FILE:
                target_path = str(DEFAULT_F2B_BLOCKLIST_FILE)
            elif dest == _DST_MANUAL:
                target_path = self.query_one("#dest-manual-input", Input).value.strip()
            else:
                selected = self.query_one("#dest-pinned-select", Select).value
                target_path = str(selected) if selected not in (None, Select.BLANK) else ""
            if not target_path:
                self.app.notify("Chemin de destination manquant.", severity="warning")
                return
            write_mode = str(self.query_one("#file-mode-select", Select).value)
            self._transfer_to_file(target_path, write_mode, banned_ips, source_label)
            return

        if dest == _DST_NFTABLES:
            self._transfer_to_firewall("nftables", self._nftables_port, banned_ips, source_label, mode=None)
            return

        if dest in (_DST_IPTABLES, _DST_IP6TABLES):
            port = self._iptables_port if dest == _DST_IPTABLES else self._ip6tables_port
            mode = str(self.query_one("#ipt-mode-select", Select).value)
            self._transfer_to_firewall(dest, port, banned_ips, source_label, mode=mode)
            return

    def _transfer_to_jail(self, jail_name: str, banned_ips: list[str], source_label: str) -> None:
        if self._fail2ban_port is None:
            self.app.notify("Port Fail2ban indisponible.", severity="error")
            return
        current_jail_banned = set(self._jails_info.get(jail_name, []))
        added_count = 0
        already_present = 0
        failed_count = 0

        from omega_fire.application.commands.jail_ban import JailBanCommand, JailBanRequest

        for ip in banned_ips:
            if ip in current_jail_banned:
                already_present += 1
                continue
            try:
                res = JailBanCommand(self._fail2ban_port).execute(JailBanRequest(jail_name=jail_name, ip=ip))
                if getattr(res, "success", False):
                    added_count += 1
                else:
                    failed_count += 1
            except Exception:
                failed_count += 1

        self.app.notify(
            f"Source : {source_label} | {added_count} bannie(s), {already_present} ignoree(s), {failed_count} echec(s).",
            title=f"Jail '{jail_name}'",
        )
        log_action_result(self._container, _ACTION_TITLE, status="success" if not failed_count else "failure")
        self.app.call_from_thread(self.dismiss)

    def _transfer_to_file(self, target_path: str, write_mode: str, banned_ips: list[str], source_label: str) -> None:
        try:
            folder_path = os.path.dirname(target_path)
            if folder_path and not os.path.exists(folder_path):
                os.makedirs(folder_path, exist_ok=True)

            existing_ips: set[str] = set()
            if os.path.exists(target_path) and write_mode != "overwrite":
                with open(target_path, "r", encoding="utf-8") as f:
                    existing_ips = _extract_valid_ips(f.read())
            source_ips_set = set(banned_ips)

            if write_mode == "overwrite":
                final_ips = sorted(source_ips_set)
                new_added = len(final_ips)
                already_present = 0
            elif write_mode == "append":
                new_added = len(banned_ips)
                already_present = 0
            else:
                new_ips_set = source_ips_set - existing_ips
                new_added = len(new_ips_set)
                already_present = len(banned_ips) - new_added

            with open(target_path, "w" if write_mode == "overwrite" else "a", encoding="utf-8") as f:
                if write_mode == "overwrite":
                    f.write(f"# Omega-Fire Blocklist - Source: {source_label}\n")
                    for ip in final_ips:
                        f.write(f"{ip}\n")
                else:
                    f.write(f"\n# Omega-Fire Append/Inc - Source: {source_label}\n")
                    ips_to_append = banned_ips if write_mode == "append" else sorted(source_ips_set - existing_ips)
                    for ip in ips_to_append:
                        f.write(f"{ip}\n")
        except Exception as e:
            self.app.notify(f"Erreur d'ecriture dans le fichier : {e}", severity="error")
            log_action_result(self._container, _ACTION_TITLE, status="failure", error=str(e))
            return

        self.app.notify(
            f"Source : {source_label} | {new_added} nouvelle(s) IP(s), {already_present} deja presente(s), "
            f"dans '{target_path}'.",
        )
        log_action_result(self._container, _ACTION_TITLE, status="success")
        self.app.call_from_thread(self.dismiss)

    def _transfer_to_firewall(self, name: str, port, banned_ips: list[str], source_label: str, mode: str | None) -> None:
        if port is None:
            self.app.notify(f"Port {name} indisponible.", severity="error")
            return

        flush_first = mode == "flush"
        if flush_first:
            port.flush_chain("INPUT")
            existing_ips: set[str] = set()
        else:
            try:
                existing_ips = {b.ip.split("/")[0] if "/" in b.ip else b.ip for b in port.list_bans()}
            except Exception:
                existing_ips = set()

        added_count = 0
        already_present = 0
        failed_count = 0
        for ip in banned_ips:
            if ip in existing_ips:
                already_present += 1
                continue
            try:
                port.ban_single_ip(IPAddress(ip), reason=source_label)
                added_count += 1
            except IPAlreadyBannedError:
                already_present += 1
            except Exception:
                failed_count += 1

        self.app.notify(
            f"Source : {source_label} | {added_count} injectee(s), {already_present} ignoree(s), {failed_count} echec(s).",
            title=name,
            severity="warning" if failed_count else "information",
        )
        log_action_result(self._container, _ACTION_TITLE, status="success" if not failed_count else "failure")
        self.app.call_from_thread(self.dismiss)
