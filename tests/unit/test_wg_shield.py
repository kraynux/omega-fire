# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Bouclier du port WireGuard (3.7.0, omega-lib D-018, omega-tail lot 8) : service, commande `bouclier-wg`,
ecran 3.6, ligne de la liste des regles, et les deux correctifs trouves en preparant le lot (lecteur nft qui
prenait les ensembles pour des regles ; synchronisation qui confondait les handles de tables differentes).
La table elle-meme est essayee sur le vrai noyau dans omega-lib (tests/test_shield.py)."""

from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

from omega_lib.shield.models import (
    SETTINGS_NAME,
    ShieldCounters,
    ShieldMode,
    ShieldSettings,
    ShieldSpec,
    ShieldStatus,
)
from omega_lib.shield.policies import parse_settings
from omega_lib.shield.system import SCRIPT_PATH, SETTINGS_PATH
from textual.widgets import Button, DataTable, Static

from omega_fire.app.shield_runner import parse, view_dict
from omega_fire.application.commands.sync_rules_from_backends import (
    SyncRulesFromBackendsCommand,
    SyncRulesRequest,
)
from omega_fire.application.commands.wg_shield import OMEGA_FIRE, WgShieldService
from omega_fire.domain.rules.models import FirewallRule, RuleAction, RuleChain, RuleFamily
from omega_fire.infrastructure.backends.nftables.adapter import NftablesAdapter
from omega_fire.infrastructure.backends.nftables.mapper import NftMapper
from omega_fire.infrastructure.backends.nftables.parser import NftParser
from omega_fire.infrastructure.config.paths import MIGRATIONS_DIR
from omega_fire.infrastructure.storage.sqlite.connection import DatabaseConnection
from omega_fire.infrastructure.storage.sqlite.migrations import MigrationManager
from omega_fire.infrastructure.storage.sqlite.repositories import RuleRepository
from omega_fire.infrastructure.storage.sqlite.schema import create_schema
from omega_fire.interfaces.cli.help_text import get_help_entry
from omega_fire.interfaces.tui.screens.wg_shield_screen import WgShieldScreen, view_lines
from omega_fire.ports.wg_shield import CommandLine

from .i18n_helpers import HostApp

SPEC = ShieldSpec(41641, ("enp5s0", "wlan0"), ShieldMode.OBSERVE, "omega-tail")


class FakeMachine:
    """Machine simulee : les commandes d'omega-lib changent reglages et etat comme le ferait le script root."""

    def __init__(self, settings: ShieldSettings | None = None, present: bool = False) -> None:
        self._settings = settings
        self._status = (ShieldStatus(True, 1000.0, settings.spec.mode, settings.spec.requested_by, 3,
                                     ShieldCounters(peer=50, other=7)) if settings and present else None)
        self.staged: dict[str, str] = {}
        self.commands: list[tuple[str, ...]] = []
        self.port = 41641
        self.modules = True

    def init_name(self) -> str:
        return "systemd"

    def runit_dir(self) -> str:
        return "/var/service"

    def kernel_release(self) -> str:
        return "7.2.14-zen"

    def modules_ready(self) -> bool:
        return self.modules

    def tailscaled_port(self) -> int:
        return self.port

    def devices(self) -> tuple[str, ...]:
        return ("enp5s0", "wlan0")

    def settings(self) -> ShieldSettings | None:
        return self._settings

    def status(self, *, refresh: bool = True) -> ShieldStatus | None:
        return self._status

    def stage(self, files: dict[str, str]) -> str:
        self.staged = dict(files)
        return "/prep"

    def run(self, commands, *, keep_going: bool = False) -> list[CommandLine]:
        lines = []
        for command in commands:
            self.commands.append(tuple(command))
            if command[-1] == SETTINGS_PATH:
                self._settings = parse_settings(self.staged[SETTINGS_NAME])
            elif command[:2] in ((SCRIPT_PATH, "poser"), (SCRIPT_PATH, "installer")) and self._settings is not None:
                self._status = ShieldStatus(True, 1000.0, self._settings.spec.mode,
                                            self._settings.spec.requested_by)
            elif command[:2] == (SCRIPT_PATH, "mode") and self._status is not None:
                self._status = ShieldStatus(True, 1000.0, ShieldMode(command[2]), self._status.requested_by,
                                            self._status.peers, self._status.counters)
            elif command[:2] == ("sh", "-c") and f"{SCRIPT_PATH} retirer" in command[2]:
                self._settings, self._status = None, None
            lines.append(CommandLine(tuple(command), 0, ""))
        return lines

    def now(self) -> float:
        return 1010.0


class ServiceTest(unittest.TestCase):
    def test_pose_records_origin_and_omega_fire_as_manager(self) -> None:
        machine = FakeMachine()
        outcome = WgShieldService(machine).pose(ShieldMode.OBSERVE, "omega-tail")
        self.assertTrue(outcome.ok)
        self.assertEqual(outcome.reason, "pose")
        self.assertEqual((outcome.view.requested_by, outcome.view.manager), ("omega-tail", OMEGA_FIRE))
        self.assertTrue(outcome.view.present)
        self.assertIn('comment "omega bouclier-wg pour=omega-tail v=1"', machine.staged["bouclier.nft"])
        self.assertIn(("systemctl", "enable", "omega-bouclier-wg.service"), machine.commands)

    def test_take_over_changes_only_the_manager(self) -> None:
        machine = FakeMachine(ShieldSettings(SPEC, "omega-tail"), present=True)
        outcome = WgShieldService(machine).take_over()
        self.assertTrue(outcome.ok and outcome.reason == "gestion")
        self.assertEqual(outcome.view.manager, OMEGA_FIRE)
        self.assertEqual(outcome.view.requested_by, "omega-tail")
        self.assertNotIn((SCRIPT_PATH, "poser"), machine.commands)   # table, compteurs et pairs intacts
        self.assertEqual(outcome.view.status.counters.other, 7)

    def test_mode_repose_remove(self) -> None:
        machine = FakeMachine(ShieldSettings(SPEC, OMEGA_FIRE), present=True)
        service = WgShieldService(machine)
        outcome = service.set_mode(ShieldMode.ACTIVE)
        self.assertTrue(outcome.ok)
        self.assertEqual(outcome.view.status.mode, ShieldMode.ACTIVE)
        self.assertEqual(outcome.view.settings.spec.mode, ShieldMode.ACTIVE)   # le demarrage reprend le mode
        machine._status = ShieldStatus(False, 1000.0)
        self.assertTrue(service.view().missing)
        self.assertEqual(service.repose().reason, "repose")
        outcome = service.remove()
        self.assertTrue(outcome.ok and outcome.reason == "retire")
        self.assertFalse(outcome.view.installed or outcome.view.stale)   # rien d'ancien sans bouclier

    def test_refusals(self) -> None:
        machine = FakeMachine()
        machine.port = 0
        self.assertEqual(WgShieldService(machine).pose(ShieldMode.OBSERVE, "omega-fire").reason, "port-aleatoire")
        machine.port = 41641
        service = WgShieldService(machine)
        self.assertEqual(service.pose(ShieldMode.OBSERVE, "omega-fire", devices=('x"',)).reason, "invalide")
        self.assertEqual(service.set_mode(ShieldMode.ACTIVE).reason, "absent")
        self.assertEqual(service.remove().reason, "absent")
        machine.port, machine.modules = 41641, False   # noyau mis a jour sans redemarrage (craftdark)
        self.assertEqual(service.pose(ShieldMode.OBSERVE, "omega-tail").reason, "redemarrage")
        self.assertEqual(machine.commands, [])


class RunnerTest(unittest.TestCase):
    def test_parse(self) -> None:
        self.assertEqual(parse(["etat", "--format", "json"]), {"action": "etat"})
        self.assertEqual(parse(["poser", "--mode", "observation", "--pour", "omega-tail", "--cartes", "eth0,wlan0"]),
                         {"action": "poser", "pour": "omega-tail", "mode": ShieldMode.OBSERVE,
                          "cartes": ("eth0", "wlan0")})
        self.assertEqual(parse(["mode", "actif", "--pour", "omega-tail"])["mode"], ShieldMode.ACTIVE)
        self.assertEqual(parse(["reprendre", "--pour", "omega-tail"]), {"action": "reprendre", "pour": "omega-tail"})
        for bad in (["poser", "--pour", "omega-tail"], ["mode", "fort", "--pour", "x"], ["retirer"],
                    ["poser", "--mode", "actif", "--pour", "omega-tail", "--cartes", 'a"b'],
                    ["poser", "--mode", "actif", "--pour", "omega-tail", "--port", "0"],
                    ["etat", "--pour", "x"], ["vider"]):
            self.assertIsNone(parse(bad), bad)

    def test_json_view(self) -> None:
        machine = FakeMachine(ShieldSettings(SPEC, "omega-tail"), present=True)
        data = view_dict(WgShieldService(machine).view())
        self.assertEqual((data["pour"], data["gestionnaire"], data["mode"], data["refuses"]),
                         ("omega-tail", "omega-tail", "observation", 7))
        self.assertEqual(data["cartes"], ["enp5s0", "wlan0"])


class ScreenTest(unittest.TestCase):
    def _run(self, machine: FakeMachine, press: str = "") -> tuple[str, dict[str, bool], list[str]]:
        async def run() -> tuple[str, dict[str, bool], list[str]]:
            app = HostApp(WgShieldScreen(service=WgShieldService(machine)))
            async with app.run_test(size=(110, 40)) as pilot:
                for _i in range(10):
                    await pilot.pause()
                if press:
                    app.screen.query_one(f"#{press}", Button).press()
                    for _i in range(10):
                        await pilot.pause()
                screen = app.screen
                state = str(screen.query_one("#shield-state", Static).render())
                shown = {name: screen.query_one(f"#frame-{name}").display
                         for name in ("pose", "mode", "take", "repose", "remove")}
                rows = screen.query_one("#shield-counters", DataTable).row_count
                return state, shown, [*app.messages, str(rows)]
        return asyncio.run(run())

    def test_shield_posed_by_omega_tail_can_be_taken_over(self) -> None:
        state, shown, info = self._run(FakeMachine(ShieldSettings(SPEC, "omega-tail"), present=True))
        self.assertIn("omega-tail", state)
        self.assertIn("OBSERVATION", state)
        self.assertEqual(shown, {"pose": False, "mode": True, "take": True, "repose": False, "remove": True})
        self.assertEqual(info[-1], "7")

    def test_pose_button(self) -> None:
        machine = FakeMachine()
        state, shown, info = self._run(machine, press="pose")
        self.assertIn((SCRIPT_PATH, "installer"), machine.commands)
        self.assertFalse(shown["pose"])
        self.assertTrue(shown["remove"])

    def test_missing_table_is_signalled(self) -> None:
        machine = FakeMachine(ShieldSettings(SPEC, OMEGA_FIRE))
        machine._status = ShieldStatus(False, 1000.0)
        view = WgShieldService(machine).view()
        self.assertIn("ABSENT", str(view_lines(view)))
        self.assertTrue(self._run(machine)[1]["repose"])

    def test_help_entry(self) -> None:
        entry = get_help_entry("3.6")
        self.assertIsNotNone(entry)
        self.assertIn("omega-tail", " ".join(entry.usage))


RULESET_WITH_SHIELD = """table inet filter { # handle 7
\tset blackhole { # handle 3
\t\ttype ipv4_addr
\t\tflags interval
\t\telements = { 1.2.3.4 comment "a {piege}",
\t\t\t     5.6.7.8 }
\t}
\tchain input { # handle 1
\t\ttype filter hook input priority filter; policy accept;
\t\ttcp dport 22 accept # handle 9
\t}
}
table netdev omega_bouclier_wg { # handle 8
\tcomment "omega bouclier-wg pour=omega-tail v=1"
\tset pairs4 { # handle 1
\t\ttype ipv4_addr . inet_service
\t\tsize 65536
\t\tflags dynamic,timeout
\t\ttimeout 5m
\t}
\tcounter pair { # handle 3
\t\tpackets 0 bytes 0
\t}
\tchain wg { # handle 9
\t\tip saddr . udp sport @pairs4 counter name "pair" accept # handle 12
\t}
}
table ip nat { # handle 9
\tchain postrouting { # handle 1
\t\ttype nat hook postrouting priority srcnat; policy accept;
\t\tmasquerade # handle 9
\t}
}
"""


class ParserAndSyncTest(unittest.TestCase):
    def test_sets_and_named_objects_are_not_rules(self) -> None:
        parsed = NftParser().parse_ruleset(RULESET_WITH_SHIELD)
        self.assertEqual([(p["table"], p["handle"]) for p in parsed],
                         [("filter", 9), ("omega_bouclier_wg", 12), ("nat", 9)])

    def test_list_rules_leaves_the_shield_out(self) -> None:
        adapter = NftablesAdapter.__new__(NftablesAdapter)
        adapter._parser, adapter._mapper = NftParser(), NftMapper()

        def run(cmd):
            adapter._last_stderr = ""
            return RULESET_WITH_SHIELD

        adapter._run_command = run
        self.assertEqual([(r.table_name, r.external_ref) for r in adapter.list_rules()],
                         [("filter", "9"), ("nat", "9")])

    def test_same_handle_in_two_tables_are_two_rules(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            db = DatabaseConnection(Path(folder) / "omega.db")
            db.connect()
            create_schema(db)
            manager = MigrationManager(db, MIGRATIONS_DIR)
            manager.ensure_schema_version_table()
            manager.apply_all_pending()
            repo = RuleRepository(db)
            managed = FirewallRule(backend="nftables", family=RuleFamily.INET, table_name="filter",
                                   chain=RuleChain.INPUT, action=RuleAction.ACCEPT, external_ref="9")
            managed.origin = "managed"
            repo.save(managed)

            class Live:
                def list_rules(self):
                    return [FirewallRule(backend="nftables", family=RuleFamily.INET, table_name="filter",
                                         chain=RuleChain.INPUT, action=RuleAction.ACCEPT, external_ref="9"),
                            FirewallRule(backend="nftables", family=RuleFamily.IP, table_name="nat",
                                         chain=RuleChain.INPUT, action=RuleAction.ACCEPT, external_ref="9")]

            result = SyncRulesFromBackendsCommand(repo).execute(SyncRulesRequest(backends={"nftables": Live()}))
            self.assertEqual((result.added, result.unchanged), (1, 1))
            tables = sorted(rule.table_name for rule in repo.find_all(backend="nftables"))
            self.assertEqual(tables, ["filter", "nat"])
            db.close()


if __name__ == "__main__":
    unittest.main()
