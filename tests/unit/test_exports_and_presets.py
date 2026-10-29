# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Version 3.5 (decisions utilisateur 2026-10-28) : presets a cocher pour les epingles,
export du Top N (5.4) recharge en 5.5 (plusieurs IPs), 6.5 Voir tous les exports et
ouverture du HTML dans le navigateur de l'utilisateur."""
from __future__ import annotations

import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from omega_fire.application.commands.manage_pinned_log_paths import ManagePinnedLogPathsCommand
from omega_fire.domain.reports.top_ips import TopIpRow, TopIpsReport
from omega_fire.infrastructure.desktop.browser_opener import readable_by, session_environment
from omega_fire.infrastructure.exporters.export_catalog import export_kind, ip_list_exports, list_exports
from omega_fire.infrastructure.exporters.html_exporter import HtmlExporter
from omega_fire.infrastructure.exporters.top_ips_exporter import read_exported_ips, write_top_ips
from omega_fire.infrastructure.storage.files.json_store import JsonStore
from omega_fire.interfaces.tui.screens.remove_ip_from_log_screen import parse_ip_list, split_lines_by_ips

TEMPLATES = Path(__file__).resolve().parents[2] / "src" / "omega_fire" / "domain" / "reports" / "templates"


def _report() -> TopIpsReport:
    rows = [TopIpRow(1, "203.0.113.9", 40, 50.0, 2048), TopIpRow(2, "2001:db8::1", 30, 37.5, 10),
            TopIpRow(3, "198.51.100.7", 10, 12.5, 0)]
    return TopIpsReport(source="/var/log/x.log", period="all", total_occurrences=80, unique_ips=3,
                        raw_ip_file=False, rows=rows)


class PresetsTest(unittest.TestCase):
    def test_presets_presents_non_epingles_sans_doublon(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            command = ManagePinnedLogPathsCommand(JsonStore(Path(tmp)), relative_path="p.json", defaults=["/a"])
            exists = {"/a", "/b", "/c"}.__contains__
            self.assertEqual(command.preset_candidates(["/a", "/b", "/absent", "/b", "/c"], exists), ["/b", "/c"])
            result = command.add_paths(["/b", "/c", "/a"])
            self.assertTrue(result.success)
            self.assertEqual(command.list_paths(), ["/a", "/b", "/c"])
            self.assertFalse(command.add_paths(["/a"]).success)


class TopIpsExportTest(unittest.TestCase):
    def test_json_txt_html_relus_dans_l_ordre(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            expected = ["203.0.113.9", "2001:db8::1", "198.51.100.7"]
            for fmt in ("json", "txt", "html"):
                path = Path(tmp) / f"top-ips_1.{fmt}"
                context = {"page_title": "t", "heading": "h", "source_label": "s", "source_value": "/v",
                           "period_label": "p", "period_value": "all", "theme_name": "omega-base",
                           "columns": ["#", "IP"], "table_rows": [[f"#{i}", ip] for i, ip in enumerate(expected, 1)]}
                write_top_ips(_report(), fmt, path, "2026-10-28 12:00:00",
                              html_exporter=HtmlExporter(TEMPLATES), html_context=context)
                self.assertEqual(read_exported_ips(path), expected, fmt)
            data = json.loads((Path(tmp) / "top-ips_1.json").read_text())
            self.assertEqual(data["rows"][0]["count"], 40)

    def test_relit_aussi_un_export_blacklist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "export-blacklist.json"
            path.write_text(json.dumps({"ips": ["10.0.0.1", "pas-une-ip", "10.0.0.1", "10.0.0.2"]}))
            self.assertEqual(read_exported_ips(path), ["10.0.0.1", "10.0.0.2"])


class RemoveSeveralIpsTest(unittest.TestCase):
    def test_saisie_multiple(self) -> None:
        self.assertEqual(parse_ip_list("1.2.3.4, 5.6.7.8;1.2.3.4  ::1"), (["1.2.3.4", "5.6.7.8", "::1"], []))
        self.assertEqual(parse_ip_list("1.2.3.4, 999.1.1.1")[1], ["999.1.1.1"])

    def test_ip_exacte_seulement(self) -> None:
        lines = ['1.2.3.4 - - "GET /"\n', '11.2.3.4 - -\n', '1.2.3.45 - -\n', 'x 5.6.7.8 et 1.2.3.4\n',
                 '1.2.3.4.5 version\n', 'rien\n']
        counts, kept = split_lines_by_ips(lines, ["1.2.3.4", "5.6.7.8"])
        # La ligne qui contient les deux IPs compte pour la premiere de la liste.
        self.assertEqual(counts, {"1.2.3.4": 2, "5.6.7.8": 0})
        self.assertEqual(kept, ['11.2.3.4 - -\n', '1.2.3.45 - -\n', '1.2.3.4.5 version\n', 'rien\n'])


class ExportCatalogTest(unittest.TestCase):
    def test_types_et_blocklists_de_travail_exclues(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            exports, blocklist = Path(tmp) / "exports", Path(tmp) / "blocklist"
            exports.mkdir(), blocklist.mkdir()
            for name, age in (("top-ips_1.json", 3), ("audit-rapport_1.html", 2), ("top-ips_2.txt", 1)):
                (exports / name).write_text("1.2.3.4\n")
                os.utime(exports / name, (1_000_000 - age, 1_000_000 - age))
            (blocklist / "blocklist.txt").write_text("1.2.3.4\n")
            (blocklist / "export-blacklist.txt").write_text("1.2.3.4\n")
            names = [f.path.name for f in list_exports(exports, blocklist)]
            self.assertNotIn("blocklist.txt", names)
            self.assertEqual(len(names), 4)
            self.assertEqual([f.path.name for f in ip_list_exports(exports, blocklist)],
                             ["top-ips_2.txt", "top-ips_1.json", "export-blacklist.txt"])
            self.assertEqual(export_kind("list-sshd-f2b.html"), "jail")


class BrowserOpenerTest(unittest.TestCase):
    def test_session_relevee_dans_un_processus_de_l_utilisateur(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            proc = Path(tmp) / "proc"
            (proc / "4242").mkdir(parents=True)
            (proc / "4242" / "environ").write_bytes(
                b"DISPLAY=:0\0DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus\0SECRET=x\0")
            uid = os.getuid()
            env = session_environment(uid, current={}, proc_dir=proc, run_dir=Path(tmp) / "run",
                                      x11_dir=Path(tmp) / "x11")
            self.assertEqual(env, {"DISPLAY": ":0", "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus"})
            self.assertEqual(session_environment(uid + 1, current={}, proc_dir=proc, run_dir=Path(tmp) / "run",
                                                 x11_dir=Path(tmp) / "x11"), {})

    @unittest.skipIf(os.geteuid() == 0, "lance en root : pas d'utilisateur cible sans SUDO_USER")
    def test_le_navigateur_survit_apres_le_retour(self) -> None:
        """Retour utilisateur 2026-10-28 : Firefox se fermait 3 a 5 s apres l'ouverture
        (stderr en tube, ferme quand Python liberait xdg-open termine -> SIGPIPE)."""
        import gc
        import subprocess
        import time

        from omega_fire.infrastructure.desktop import browser_opener

        with tempfile.TemporaryDirectory() as tmp:
            alive = Path(tmp) / "alive"
            fake = Path(tmp) / "bin" / "xdg-open"
            fake.parent.mkdir()
            # Comme exo-open : lance le « navigateur » en arriere-plan (il herite de stderr)
            # et rend la main ; le navigateur ecrit ensuite sur stderr.
            fake.write_text(f"#!/bin/sh\n( sleep 0.6; echo bruit >&2; echo bruit >&2; sleep 0.3; "
                            f"touch {alive} ) &\nexit 0\n")
            fake.chmod(0o755)
            page = Path(tmp) / "r.html"
            page.write_text("x")
            with mock.patch.dict(os.environ, {"PATH": f"{fake.parent}:{os.environ['PATH']}"}), \
                    mock.patch.object(browser_opener, "session_environment", lambda uid: {"DISPLAY": ":0"}), \
                    mock.patch.object(browser_opener, "_WAIT_SECONDS", 0.2), \
                    mock.patch.object(browser_opener, "default_browser_desktop_file", lambda *a: None):
                self.assertTrue(browser_opener.open_in_browser(page).ok)
            subprocess.run(["true"], check=True)  # Python libere xdg-open termine
            gc.collect()
            time.sleep(1.5)
            self.assertTrue(alive.exists())

    @unittest.skipIf(os.geteuid() == 0, "lance en root : pas d'utilisateur cible sans SUDO_USER")
    def test_navigateur_web_par_defaut_pas_l_association_html(self) -> None:
        """Retour utilisateur 2026-10-28 : navigateur par defaut Brave, mais text/html associe
        a Firefox -> xdg-open ouvrait Firefox. On ouvre avec le navigateur web par defaut."""
        import time

        from omega_fire.infrastructure.desktop import browser_opener

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bin_dir, apps = root / "bin", root / "share" / "applications"
            bin_dir.mkdir()
            apps.mkdir(parents=True)
            (apps / "mon-navigateur.desktop").write_text("[Desktop Entry]\nExec=x %U\n")
            log = root / "calls.log"
            scripts = {
                "xdg-settings": "echo mon-navigateur.desktop",
                "gio": f'echo "gio $*" >> {log}',
                "xdg-open": f'echo "xdg-open $*" >> {log}',
            }
            for name, body in scripts.items():
                (bin_dir / name).write_text(f"#!/bin/sh\n{body}\n")
                (bin_dir / name).chmod(0o755)
            page = root / "r.html"
            page.write_text("x")
            env = {"PATH": f"{bin_dir}:/usr/bin:/bin", "XDG_DATA_DIRS": str(root / "share")}
            with mock.patch.dict(os.environ, env), \
                    mock.patch.object(browser_opener, "session_environment",
                                      lambda uid: {"DISPLAY": ":0", "XDG_DATA_DIRS": str(root / "share")}):
                self.assertTrue(browser_opener.open_in_browser(page).ok)
                for _attempt in range(20):
                    if log.exists():
                        break
                    time.sleep(0.05)
                self.assertEqual(log.read_text().split(),
                                 ["gio", "launch", str(apps / "mon-navigateur.desktop"), str(page)])
                # Sans navigateur par defaut declare : repli sur xdg-open.
                log.unlink()
                (bin_dir / "xdg-settings").write_text("#!/bin/sh\nexit 1\n")
                self.assertTrue(browser_opener.open_in_browser(page).ok)
                self.assertEqual(log.read_text().split(), ["xdg-open", str(page)])

    def test_lisibilite_du_fichier(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "r.html"
            path.write_text("x")
            path.chmod(0o600)
            self.assertTrue(readable_by(path, os.getuid(), os.getgid()))
            self.assertFalse(readable_by(path, os.getuid() + 12345, os.getgid() + 12345))


class TopIpsToRemoveFlowTest(unittest.TestCase):
    """5.4 analyse + export, puis 5.5 charge l'export et coche deux IPs : la saisie est
    remplie et la confirmation compte les lignes par IP."""

    def test_parcours_complet(self) -> None:
        from textual.widgets import Button, Input, Select

        from .i18n_helpers import FakeContainer, HostApp, MemorySettings
        from omega_fire.interfaces.tui.screens import remove_ip_from_log_screen, top_ips_screen
        from omega_fire.interfaces.tui.screens.remove_ip_from_log_screen import RemoveIpFromLogScreen
        from omega_fire.interfaces.tui.screens.top_ips_screen import TopIpsScreen

        async def run(tmp: Path) -> None:
            log = tmp / "access.log"
            log.write_text("".join(
                f'{ip} - - [28/Oct/2026:10:00:00 +0100] "GET / HTTP/1.1" 200 10\n'
                for ip in ["203.0.113.9"] * 3 + ["192.0.2.1"] * 2 + ["10.0.0.4"]))
            container = FakeContainer(MemorySettings(), tmp)
            app = HostApp(TopIpsScreen(container=container))
            async with app.run_test(size=(110, 34)) as pilot:
                await pilot.pause()
                screen = app.screen
                screen.query_one("#source-select", Select).value = "__manual__"
                screen.query_one("#manual-input", Input).value = str(log)
                screen._analyze()
                await pilot.pause()
                screen._export()
            exported = list((tmp / "var" / "exports").glob("top-ips_*.json"))
            self.assertEqual(len(exported), 1)

            app = HostApp(RemoveIpFromLogScreen(container=container))
            async with app.run_test(size=(110, 34)) as pilot:
                await pilot.pause()
                screen = app.screen
                screen._pick_export()
                await pilot.pause()
                await pilot.press("enter")
                await pilot.pause()
                checklist = app.screen.query_one("#checklist")
                checklist.select("203.0.113.9")
                checklist.select("10.0.0.4")
                app.screen.query_one("#confirm", Button).press()
                await pilot.pause()
                self.assertEqual(screen.query_one("#ip-input", Input).value, "203.0.113.9, 10.0.0.4")
                screen.query_one("#source-select", Select).value = "__manual__"
                await pilot.pause()
                screen.query_one("#manual-input", Input).value = str(log)
                screen._launch()
                await pilot.pause()
                app.screen.query_one("#confirm", Button).press()
                await pilot.pause()
            self.assertEqual(log.read_text().count("192.0.2.1"), 2)
            self.assertNotIn("203.0.113.9", log.read_text())
            self.assertNotIn("10.0.0.4", log.read_text())

        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp) / "runtime"
            with mock.patch.object(top_ips_screen, "RUNTIME_DIR", runtime), \
                    mock.patch.object(remove_ip_from_log_screen, "RUNTIME_DIR", runtime), \
                    mock.patch.object(top_ips_screen, "log_action_result", lambda *a, **k: None), \
                    mock.patch.object(remove_ip_from_log_screen, "log_action_result", lambda *a, **k: None):
                asyncio.run(run(Path(tmp)))


if __name__ == "__main__":
    unittest.main()
