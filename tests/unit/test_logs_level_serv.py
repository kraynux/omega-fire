# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Gestionnaire de logs au niveau d'omega-serv / omega-log (2026-11-09,
OMEGA-FIRE_PLAN_LOGS_NIVEAU_SERV_LOG.md) : Bibliotheque dans toutes les selections, fichiers de
blocklist par defaut, viewer Simple, 5.4 (recherche et retrait d'une IP)."""
from __future__ import annotations

import asyncio
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from omega_lib.terminal.models import RenderProfile
from textual.widgets import Button, DataTable, Input, Select, Static

from omega_fire.domain.logs.library import LibraryRecord
from omega_fire.infrastructure.config import paths as config_paths
from omega_fire.interfaces.tui.rendering.stylesheet_loader import load_paths_for
from omega_fire.interfaces.tui.screens import _log_sources

from .i18n_helpers import HostApp

ACCESS_LINES = [
    '203.0.113.5 - - [09/Nov/2026:18:00:00 +0100] "GET /wp-login.php HTTP/1.1" 404 120 "-" "curl"\n',
    '203.0.113.5 - - [09/Nov/2026:18:00:01 +0100] "GET /.env HTTP/1.1" 403 80 "-" "curl"\n',
    '198.51.100.7 - - [09/Nov/2026:18:00:02 +0100] "GET / HTTP/1.1" 200 5000 "-" "Mozilla"\n',
    '198.51.100.7 - - [09/Nov/2026:18:00:03 +0100] "GET /api HTTP/1.1" 429 10 "-" "Mozilla"\n',
    '192.0.2.44 - - [09/Nov/2026:18:00:04 +0100] "GET / HTTP/1.1" 200 4000 "-" "Mozilla"\n',
    '203.0.113.5 - - [09/Nov/2026:18:00:05 +0100] "GET /wp-login.php HTTP/1.1" 404 120 "-" "curl"\n',
]


class _StyledHost(HostApp):
    CSS_PATH = load_paths_for(RenderProfile.COMPLETE)


class _FakeLibrary:
    def __init__(self, paths: list[str]) -> None:
        self._paths = paths

    def records(self) -> list[LibraryRecord]:
        return [LibraryRecord(path) for path in self._paths]


async def _settle(pilot, rounds: int = 3) -> None:
    for _ in range(rounds):
        await pilot.pause()
        await asyncio.sleep(0.15)
    await pilot.pause()


class LibraryFeedsSelectionsTest(unittest.TestCase):
    def test_library_first_then_pins_without_duplicates_then_manual(self) -> None:
        library = _FakeLibrary(["/srv/omega-serv/var/log/access.log", "/var/log/auth.log"])
        with mock.patch.object(_log_sources, "library_command", return_value=library):
            options = _log_sources.log_source_options(["/var/log/auth.log", "var/blocklist/blocklist.txt"], "__m__")
        self.assertEqual([value for _label, value in options],
                         ["/srv/omega-serv/var/log/access.log", "/var/log/auth.log", "var/blocklist/blocklist.txt",
                          "__m__"])

    def test_unreadable_library_falls_back_to_pins(self) -> None:
        broken = mock.Mock()
        broken.records.side_effect = ValueError("json")
        with mock.patch.object(_log_sources, "library_command", return_value=broken):
            self.assertEqual(_log_sources.log_source_options(["/a.log"], None), [("/a.log", "/a.log")])

    def test_screens_5_4_to_5_6_and_8_5_8_6_offer_library_logs(self) -> None:
        from omega_fire.interfaces.tui.screens import live_tail_screen, lnav_screen
        from omega_fire.interfaces.tui.screens.remove_ip_from_log_screen import RemoveIpFromLogScreen
        from omega_fire.interfaces.tui.screens.rotate_logs_screen import RotateLogsScreen
        from omega_fire.interfaces.tui.screens.top_ips_screen import TopIpsScreen

        library_log = "/srv/omega-serv/var/log/access.log"
        library = _FakeLibrary([library_log])
        container = mock.Mock()

        async def scenario(screen) -> list[str]:
            app = _StyledHost(screen)
            async with app.run_test(size=(120, 40)) as pilot:
                await pilot.pause()
                if app.screen.query("#source-select"):
                    return [str(v) for _label, v in app.screen.query_one("#source-select", Select)._options]
                table = app.screen.query_one("#sources-table", DataTable)
                return [str(table.get_row_at(i)[-1]) for i in range(table.row_count)]

        with mock.patch.object(_log_sources, "library_command", return_value=library), \
                mock.patch.object(live_tail_screen, "library_paths", return_value=[library_log]), \
                mock.patch.object(lnav_screen, "library_paths", return_value=[library_log]):
            for factory in (TopIpsScreen, RemoveIpFromLogScreen, RotateLogsScreen,
                            live_tail_screen.LiveTailScreen, lnav_screen.LnavScreen):
                with self.subTest(screen=factory.__name__):
                    values = asyncio.run(scenario(factory(container=container)))
                    self.assertIn(library_log, values)


class DefaultBlocklistFilesTest(unittest.TestCase):
    def test_created_empty_group_writable_never_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            first, second = Path(tmp) / "blocklist.txt", Path(tmp) / "blocklist-f2b.txt"
            second.write_text("192.0.2.1\n", encoding="utf-8")
            with mock.patch.object(config_paths, "DEFAULT_PINNED_FILES", [first, second]):
                config_paths.ensure_default_blocklist_files()
                config_paths.ensure_default_blocklist_files()
            self.assertEqual(first.read_text(encoding="utf-8"), "")
            self.assertEqual(stat.S_IMODE(os.stat(first).st_mode), 0o664)
            self.assertEqual(second.read_text(encoding="utf-8"), "192.0.2.1\n")

    def test_read_only_folder_never_raises(self) -> None:
        with mock.patch.object(config_paths, "DEFAULT_PINNED_FILES", [Path("/proc/omega-fire-impossible.txt")]):
            config_paths.ensure_default_blocklist_files()


class SimpleViewerTest(unittest.TestCase):
    def test_stats_like_omega_log(self) -> None:
        from omega_fire.interfaces.tui.screens.live_tail_screen import LiveTailScreen

        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "access.log"
            log.write_text("".join(ACCESS_LINES), encoding="utf-8")

            async def scenario() -> str:
                app = _StyledHost(LiveTailScreen(container=mock.Mock(), source=str(log)))
                async with app.run_test(size=(120, 40)) as pilot:
                    await _settle(pilot)
                    return str(app.screen.query_one("#stats-box", Static).render())

            text = asyncio.run(scenario())
        for expected in ("Refus 403    : 1", "Refus 429    : 1", "Top 5 IP", "203.0.113.5", "CHEMINS DEMANDÉS",
                         "CHEMINS EN 404", "/wp-login.php"):
            self.assertIn(expected, text)


class TopIpsSearchAndRemoveTest(unittest.TestCase):
    def test_analyze_search_and_remove_an_ip(self) -> None:
        from omega_fire.interfaces.tui.screens import top_ips_screen

        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "access.log"
            log.write_text("".join(ACCESS_LINES), encoding="utf-8")
            container = mock.Mock()

            async def scenario() -> list[str]:
                app = _StyledHost(top_ips_screen.TopIpsScreen(container=container))
                async with app.run_test(size=(120, 50)) as pilot:
                    await pilot.pause()
                    screen = app.screen
                    screen.query_one("#source-select", Select).value = "__manual__"
                    screen.query_one("#manual-input", Input).value = str(log)
                    screen.query_one("#launch", Button).press()
                    await _settle(pilot)
                    table = screen.query_one("#result-table", DataTable)
                    first_ips = [str(table.get_row_at(i)[1]) for i in range(table.row_count)]
                    screen.query_one("#search-ip-input", Input).value = "198.51.100.7"
                    screen.query_one("#search-ip", Button).press()
                    await _settle(pilot)
                    self.assertIn("2", str(screen.query_one("#ip-search-result", Static).render()))
                    self.assertFalse(screen.query_one("#remove-ip", Button).disabled)
                    screen.query_one("#remove-ip", Button).press()
                    await pilot.pause()
                    app.screen.query_one("#confirm", Button).press()
                    await _settle(pilot)
                    return first_ips

            with mock.patch.object(top_ips_screen, "log_action_result"):
                first_ips = asyncio.run(scenario())
            self.assertEqual(first_ips[0], "203.0.113.5")
            remaining = log.read_text(encoding="utf-8")
        self.assertNotIn("198.51.100.7", remaining)
        self.assertEqual(remaining.count("\n"), 4)


class ExportLogStatsTest(unittest.TestCase):
    def test_6_5_computes_and_exports_json_and_html(self) -> None:
        from omega_fire.interfaces.tui.screens import export_log_stats_screen as screen_module
        from omega_fire.interfaces.tui.section_registry import find_item

        self.assertEqual(find_item("6.5")[1].label, "Exporter les statistiques des logs")
        self.assertEqual(find_item("6.6")[1].label, "Voir tous les exports")
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "access.log"
            log.write_text("".join(ACCESS_LINES), encoding="utf-8")
            exports = Path(tmp) / "exports"
            container = mock.Mock(exports_dir=exports)

            async def scenario() -> str:
                with mock.patch.object(screen_module, "log_source_options", return_value=[(str(log), str(log))]), \
                        mock.patch.object(screen_module, "export_translation", return_value=None), \
                        mock.patch.object(screen_module, "log_action_result"):
                    app = _StyledHost(screen_module.ExportLogStatsScreen(container=container))
                    async with app.run_test(size=(140, 60)) as pilot:
                        await pilot.pause()
                        app.screen.query_one("#period-Tout", Button).press()
                        for _ in range(40):
                            await _settle(pilot, 1)
                            if app.screen._result is not None:
                                break
                        summary = str(app.screen.query_one("#stats-summary", Static).render())
                        app.screen.query_one("#export-json", Button).press()
                        await pilot.pause()
                        app.screen.query_one("#export-html", Button).press()
                        await pilot.pause()
                        return summary

            summary = asyncio.run(scenario())
            files = sorted(f.name for f in exports.iterdir())
            html = next(exports.glob("logs-stats_*.html")).read_text(encoding="utf-8")
        self.assertIn("203.0.113.5", summary)
        self.assertIn("CHEMINS EN 404", summary)
        self.assertEqual(len(files), 2)
        self.assertTrue(all(name.startswith("logs-stats_") for name in files))
        self.assertIn("OMEGA-FIRE", html)
        self.assertIn("/wp-login.php", html)

    def test_old_6_5_history_entries_keep_their_label(self) -> None:
        from omega_fire.interfaces.tui.section_registry import MENU_5_BEFORE_3_5, MENU_6_BEFORE_3_6, SECTIONS
        from omega_fire.interfaces.tui.support.action_titles import ActionTitleTranslator, menu_labels_by_action

        translator = ActionTitleTranslator(menu_labels_by_action(SECTIONS), lambda: [], lambda code: {},
                                           renumbered={**MENU_5_BEFORE_3_5, **MENU_6_BEFORE_3_6})
        self.assertEqual(translator("6.5 Voir tous les exports"), "6.5 Voir tous les exports")
        self.assertEqual(translator("6.5 Exporter les statistiques des logs"), "6.5 Exporter les statistiques des logs")
        self.assertEqual(translator("6.6 Voir tous les exports"), "6.6 Voir tous les exports")


class RotationAutomationTest(unittest.TestCase):
    def _store(self, tmp: str, items: list[dict]):
        from omega_fire.application.commands.rotation_automation import AutomationStore

        store = AutomationStore(Path(tmp) / "scheduled_rotations.json")
        store.save_all(items)
        return store

    def test_due_automations_run_failures_stay_due(self) -> None:
        from datetime import datetime

        from omega_fire.application.commands.rotation_automation import run_due_automations

        with tempfile.TemporaryDirectory() as tmp:
            store = self._store(tmp, [
                {"source_path": "/var/log/a.log", "days_interval": 1, "created_at": "2026-11-01 10:00"},
                {"source_path": "/var/log/b.log", "days_interval": 7, "created_at": "2026-11-08 10:00", "keep": 5},
                {"source_path": "/var/log/c.log", "days_interval": 1, "created_at": "2026-11-01 10:00"},
                {"source_path": "illisible"},
            ])
            calls: list[tuple[str, int]] = []

            def backup(path: str, keep: int) -> tuple[bool, str]:
                calls.append((path, keep))
                return path != "/var/log/c.log", "ok" if path != "/var/log/c.log" else "absent"

            runs = run_due_automations(store, datetime(2026, 11, 9, 3, 45), backup)
            saved = store.list_all()
        self.assertEqual(calls, [("/var/log/a.log", 10), ("/var/log/c.log", 10)])
        self.assertEqual([r.success for r in runs], [True, False])
        self.assertEqual(saved[0]["last_run_at"], "2026-11-09T03:45:00")
        self.assertNotIn("last_run_at", saved[2])
        self.assertEqual(saved[2]["last_result"], "absent")

    def test_install_and_remove_with_systemd(self) -> None:
        from omega_fire.application.commands import rotation_automation as ra

        calls: list[list[str]] = []

        def runner(argv: list[str], _input: str | None) -> ra.CommandResult:
            calls.append(argv)
            return ra.CommandResult(0)

        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(ra, "uses_systemd", return_value=True):
            units = Path(tmp)
            result = ra.install_rotation_schedule(Path("/opt/omega-fire"), "/opt/omega-fire/.venv/bin/python",
                                                  runner, unit_dir=units)
            service = (units / "omega-fire-rotation.service").read_text(encoding="utf-8")
            self.assertTrue(result.success)
            self.assertIn("ExecStart=/opt/omega-fire/.venv/bin/python -m omega_fire rotate run-automations", service)
            self.assertIn("WorkingDirectory=/opt/omega-fire", service)
            self.assertNotIn("User=", service)  # root, comme omega-fire
            self.assertIn(["systemctl", "enable", "--now", "omega-fire-rotation.timer"], calls)
            removed = ra.remove_rotation_schedule(runner, unit_dir=units)
            self.assertTrue(removed.success)
            self.assertFalse((units / "omega-fire-rotation.timer").exists())

    def test_install_and_remove_with_root_crontab(self) -> None:
        from omega_fire.application.commands import rotation_automation as ra

        crontab = {"text": "0 1 * * * /usr/bin/true\n"}

        def runner(argv: list[str], input_text: str | None) -> ra.CommandResult:
            if argv == ["crontab", "-l"]:
                return ra.CommandResult(0, crontab["text"])
            if argv == ["crontab", "-"]:
                crontab["text"] = input_text or ""
                return ra.CommandResult(0)
            return ra.CommandResult(1)

        with mock.patch.object(ra, "uses_systemd", return_value=False):
            self.assertTrue(ra.install_rotation_schedule(Path("/opt/omega-fire"), "/usr/bin/python3", runner).success)
            self.assertIn("rotate run-automations", crontab["text"])
            self.assertIn("/usr/bin/true", crontab["text"])
            self.assertTrue(ra.rotation_schedule_status(runner).success)
            ra.remove_rotation_schedule(runner)
            self.assertNotIn("rotate run-automations", crontab["text"])
            self.assertIn("/usr/bin/true", crontab["text"])

    def test_entry_point_dispatches_without_interface(self) -> None:
        from omega_fire.app import bootstrap

        with mock.patch.object(bootstrap.sys, "argv", ["omega_fire", "rotate", "run-automations"]), \
                mock.patch("omega_fire.app.rotation_runner.run_rotation_automations", return_value=0) as run, \
                mock.patch.object(bootstrap, "bootstrap_tui") as tui:
            self.assertEqual(bootstrap.main(), 0)
        run.assert_called_once()
        tui.assert_not_called()


if __name__ == "__main__":
    unittest.main()
