# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Point 7 (version 3.5, decisions utilisateur 2026-10-28) : omega-serv / omega-waf /
omega-jail dans le registre des capacites, journaux d'omega-waf deplaces par la config
magnet, jails d'omega-jail retrouves par leur section et supprimes avec avertissement,
jails de jail.local ou de fichiers partages jamais supprimes."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from omega_fire.core.capability_registry import CapabilityRegistry
from omega_fire.core.enums import CapabilityStatus
from omega_fire.domain.fail2ban.definitions import (
    BLOCKED_MAIN_CONFIG,
    BLOCKED_SHARED_FILE,
    ORIGIN_MAIN_CONFIG,
    ORIGIN_OMEGA_JAIL,
)
from omega_fire.domain.fail2ban.exceptions import JailNotDeletableError
from omega_fire.infrastructure.backends.fail2ban.adapter import Fail2banAdapter
from omega_fire.infrastructure.probe import omega_serv_detector, scanner as scanner_module
from omega_fire.infrastructure.probe.omega_serv_detector import OmegaServInstance, instance_log_files, magnet_info
from omega_fire.infrastructure.probe.scanner import SystemScanner

OMEGA_JAIL = "# Genere par Omega-Jail\n[omega-serv-scan]\nenabled = true\nfilter = omega-jail-omega-serv-scan\nlogpath = /x\n"


class _Fixture:
    def __init__(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.jail_d = self.root / "jail.d"
        self.filter_d = self.root / "filter.d"
        self.jail_d.mkdir()
        self.filter_d.mkdir()
        (self.jail_d / "omega-jail-omega-serv-scan.conf").write_text(OMEGA_JAIL)
        (self.filter_d / "omega-jail-omega-serv-scan.conf").write_text("# Genere par Omega-Jail pour x\n[Definition]\n")
        (self.jail_d / "sshd-custom.conf").write_text("[sshd]\nenabled = true\nfilter = sshd\n")
        (self.filter_d / "sshd.conf").write_text("# filtre standard de fail2ban\n[Definition]\n")
        (self.jail_d / "honeypot.conf").write_text("[trap-a]\nenabled = true\n[trap-b]\nenabled = true\n")
        (self.root / "jail.local").write_text("[DEFAULT]\nbantime = 1h\n[recidive]\nenabled = true\n")
        self.adapter = Fail2banAdapter()
        self.adapter._run_raw = mock.Mock()
        self.adapter.list_jails = mock.Mock(return_value=["omega-serv-scan", "sshd", "recidive"])

    def kwargs(self) -> dict:
        return {"jail_d_dir": str(self.jail_d), "jail_conf_path": str(self.root / "jail.conf"),
                "jail_local_path": str(self.root / "jail.local")}

    def close(self) -> None:
        self._tmp.cleanup()


class JailDefinitionsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.fx = _Fixture()
        self.addCleanup(self.fx.close)

    def test_par_section_avec_origine(self) -> None:
        definitions = self.fx.adapter.jail_definitions(**self.fx.kwargs())
        self.assertEqual(definitions["omega-serv-scan"].origin, ORIGIN_OMEGA_JAIL)
        self.assertTrue(definitions["omega-serv-scan"].deletable)
        self.assertEqual(definitions["recidive"].origin, ORIGIN_MAIN_CONFIG)
        self.assertEqual(definitions["recidive"].blocked, BLOCKED_MAIN_CONFIG)
        self.assertEqual(definitions["trap-a"].blocked, BLOCKED_SHARED_FILE)
        self.assertNotIn("DEFAULT", definitions)
        # 4.5 liste le vrai nom du jail, plus le nom du fichier.
        files = self.fx.adapter.list_configured_jail_files(str(self.fx.jail_d))
        self.assertIn("omega-serv-scan", files)
        self.assertNotIn("omega-jail-omega-serv-scan", files)

    def test_suppression_jail_omega_jail_et_son_filtre(self) -> None:
        self.fx.adapter.delete_jail("omega-serv-scan", filter_d_dir=str(self.fx.filter_d), **self.fx.kwargs())
        self.assertFalse((self.fx.jail_d / "omega-jail-omega-serv-scan.conf").exists())
        self.assertFalse((self.fx.filter_d / "omega-jail-omega-serv-scan.conf").exists())

    def test_filtre_standard_jamais_supprime(self) -> None:
        self.fx.adapter.delete_jail("sshd", filter_d_dir=str(self.fx.filter_d), **self.fx.kwargs())
        self.assertFalse((self.fx.jail_d / "sshd-custom.conf").exists())
        self.assertTrue((self.fx.filter_d / "sshd.conf").exists())

    def test_refus_jail_local_et_fichier_partage(self) -> None:
        for name in ("recidive", "trap-a"):
            with self.assertRaises(JailNotDeletableError):
                self.fx.adapter.delete_jail(name, filter_d_dir=str(self.fx.filter_d), **self.fx.kwargs())
        self.assertTrue((self.fx.jail_d / "honeypot.conf").exists())
        self.assertIn("recidive", (self.fx.root / "jail.local").read_text())


class MagnetLogsTest(unittest.TestCase):
    def test_journaux_omega_waf_hors_de_var_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "config").mkdir()
            (root / "var" / "log").mkdir(parents=True)
            (root / "logs-waf").mkdir()
            (root / "var" / "log" / "access.log").write_text("x\n")
            (root / "logs-waf" / "alerts.log").write_text("x\n")
            (root / "config" / "omega-serve.json").write_text(json.dumps({"options": {"waf": {"magnet": {
                "enabled": True, "script": "secure/waf/omega-waf.lua",
                "paths": {"alerts_log": "logs-waf/alerts.log"}}}}}))
            instance = OmegaServInstance(name="omega-serv", root=root)
            magnet = magnet_info(instance)
            self.assertIsNotNone(magnet)
            names = [path.name for path in instance_log_files(instance)]
            self.assertEqual(sorted(names), ["access.log", "alerts.log"])
            (root / "config" / "omega-serve.json").write_text(json.dumps({"options": {"waf": {}}}))
            self.assertIsNone(magnet_info(instance))


class SuiteCapabilitiesTest(unittest.TestCase):
    def test_trois_capacites_suite_omega(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "config").mkdir()
            (root / "config" / "omega-serve.json").write_text(json.dumps(
                {"options": {"waf": {"magnet": {"enabled": True}}}}))
            jail_d = root / "jail.d"
            jail_d.mkdir()
            (jail_d / "omega-jail-omega-serv-scan.conf").write_text(OMEGA_JAIL)
            registry = CapabilityRegistry()
            scanner = SystemScanner(registry)
            instance = OmegaServInstance(name="omega-serv", root=root, systemd_unit="omega-serv.service")
            with mock.patch.object(omega_serv_detector, "detect_omega_serv_instances", return_value=[instance]), \
                    mock.patch.object(scanner_module, "_instance_running", return_value=False):
                scanner._scan_omega_suite(jail_d_dir=jail_d)
            self.assertEqual(registry.get("omega_serv").status, CapabilityStatus.DEGRADED)  # arretee
            self.assertEqual(registry.get("omega_waf").status, CapabilityStatus.AVAILABLE)
            self.assertEqual(registry.get("omega_jail").status, CapabilityStatus.AVAILABLE)
            self.assertEqual(registry.get("omega_jail").category, "omega_suite")
            with mock.patch.object(omega_serv_detector, "detect_omega_serv_instances", return_value=[]):
                scanner._scan_omega_suite(jail_d_dir=root / "absent")
            self.assertEqual(registry.get("omega_serv").status, CapabilityStatus.MISSING)
            self.assertEqual(registry.get("omega_jail").status, CapabilityStatus.MISSING)


class DashboardJailAlertTest(unittest.TestCase):
    """Retour utilisateur 2026-10-28 (craftdark) : « omega-jail-… configuré mais non chargé »
    alors que les jails etaient actifs — l'alerte comparait les noms de fichiers."""

    def test_alerte_par_section_et_enabled(self) -> None:
        from omega_fire.application.queries import dashboard_snapshot
        from omega_fire.application.queries.dashboard_snapshot import DashboardSnapshotProvider

        fx = _Fixture()
        self.addCleanup(fx.close)
        (fx.jail_d / "off.conf").write_text("[desactive]\nenabled = false\n")
        (fx.jail_d / "missing.conf").write_text("[absent]\nenabled = true\n")
        loaded = [mock.Mock(banned_count=0) for _n in range(4)]
        for jail, name in zip(loaded, ("omega-serv-scan", "sshd", "trap-a", "trap-b")):
            jail.name = name
        provider = DashboardSnapshotProvider.__new__(DashboardSnapshotProvider)
        with mock.patch.object(dashboard_snapshot, "_FAIL2BAN_JAIL_D_DIR", str(fx.jail_d)):
            alerts = provider._compute_fail2ban_alerts(loaded)
        self.assertEqual(len(alerts), 1, alerts)
        self.assertIn("absent", alerts[0])


class DeleteJailScreenTest(unittest.TestCase):
    """4.5 : avertissement pour un jail d'omega-jail, refus explique pour jail.local."""

    def test_avertissement_et_refus(self) -> None:
        import asyncio

        from textual.widgets import Button, Select

        from omega_fire.interfaces.tui.screens.confirm import ConfirmScreen
        from omega_fire.interfaces.tui.screens.delete_jail_screen import DeleteJailScreen

        from .i18n_helpers import FakeContainer, HostApp, MemorySettings

        fx = _Fixture()
        self.addCleanup(fx.close)
        definitions = fx.adapter.jail_definitions(**fx.kwargs())
        port = mock.Mock()
        port.list_configured_jail_files.return_value = {"omega-serv-scan": "/x/omega-jail-omega-serv-scan.conf"}
        port.jail_definitions.return_value = definitions
        status = mock.Mock(jails=[mock.Mock(name_="recidive")])
        status.jails[0].name = "recidive"

        async def run(tmp: Path) -> None:
            container = FakeContainer(MemorySettings(), tmp)
            container.get_fail2ban_port = lambda: port
            app = HostApp(DeleteJailScreen(container=container))
            with mock.patch("omega_fire.interfaces.tui.screens.delete_jail_screen.get_jail_status",
                            return_value=status):
                async with app.run_test(size=(110, 34)) as pilot:
                    for _attempt in range(20):
                        await pilot.pause(0.05)
                        if not app.screen.query_one("#launch", Button).disabled:
                            break
                    screen = app.screen
                    screen.query_one("#jail-select", Select).value = "omega-serv-scan"
                    await pilot.pause()
                    screen.query_one("#launch", Button).press()
                    await pilot.pause()
                    self.assertIsInstance(app.screen, ConfirmScreen)
                    self.assertIn("omega-jail --apply", app.screen._message)
                    await pilot.press("escape")
                    await pilot.pause()
                    screen.query_one("#jail-select", Select).value = "recidive"
                    await pilot.pause()
                    screen.query_one("#launch", Button).press()
                    await pilot.pause()
                    self.assertNotIsInstance(app.screen, ConfirmScreen)
                    self.assertTrue(any("enabled = false" in m for m in app.messages), app.messages)
            port.delete_jail.assert_not_called()

        with tempfile.TemporaryDirectory() as tmp:
            asyncio.run(run(Path(tmp)))


if __name__ == "__main__":
    unittest.main()
