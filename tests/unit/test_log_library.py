# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Bibliotheque de logs (5.1), Favoris (5.2), sources distantes SSH, detection d'omega-serv
(version 3.5, decisions utilisateur 2026-10-28)."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from omega_fire.application.commands.manage_log_library import (
    LogFavoritesCommand,
    LogLibraryCommand,
    RemoteLogSourcesCommand,
)
from omega_fire.domain.logs.remote_source import RemoteLogSource, build_scp_command, safe_cache_filename
from omega_fire.domain.logs.viewer_type import ViewerType, allowed_viewers
from omega_fire.infrastructure.probe.omega_serv_detector import detect_omega_serv_instances, instance_log_files
from omega_fire.infrastructure.storage.files.json_store import JsonStore


class LibraryTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.store = JsonStore(self.root / "runtime")
        self.library = LogLibraryCommand(self.store)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_epinglage_manuel_et_etat_recalcule(self) -> None:
        log = self.root / "a.log"
        self.assertFalse(self.library.pin_path("relatif.log").success)
        self.assertEqual(self.library.pin_path(str(log)).count, 1)
        self.assertEqual(self.library.pin_path(str(log)).count, 0)  # pas de doublon
        self.assertFalse(self.library.list_logs()[0].exists)
        log.write_text("x\n")
        state = self.library.list_logs()[0]
        self.assertTrue(state.exists)
        self.assertEqual(state.size_bytes, 2)
        self.assertEqual(self.library.remove([str(log)]), 1)
        self.assertEqual(self.library.list_logs(), [])

    def test_import_omega_serv(self) -> None:
        paths = [self.root / "access.log", self.root / "waf-alerts.log"]
        result = self.library.import_omega_serv([("omega-serv", paths)])
        self.assertEqual(result.count, 2)
        self.assertEqual(self.library.import_omega_serv([("omega-serv", paths)]).count, 0)
        self.assertEqual({(l.access, l.source) for l in self.library.list_logs()}, {("omega-serv", "omega-serv")})
        self.assertFalse(self.library.import_omega_serv([]).success)


class FavoritesTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.favorites = LogFavoritesCommand(JsonStore(Path(self._tmp.name)))

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_garde_fou_lnav_pour_plusieurs_logs(self) -> None:
        self.assertEqual(allowed_viewers(2), (ViewerType.LNAV,))
        refused = self.favorites.create(name="web", paths=["/a", "/b"], viewer=ViewerType.CLASSIC)
        self.assertFalse(refused.success)
        self.assertTrue(self.favorites.create(name="web", paths=["/a", "/b"], viewer=ViewerType.LNAV).success)
        self.assertTrue(self.favorites.create(name="seul", paths=["/a"], viewer=ViewerType.SIMPLE).success)
        self.assertEqual([(f.name, f.viewer) for f in self.favorites.list_favorites()],
                         [("web", ViewerType.LNAV), ("seul", ViewerType.SIMPLE)])
        self.assertTrue(self.favorites.remove("web"))
        self.assertFalse(self.favorites.create(name=" ", paths=["/a"], viewer=ViewerType.SIMPLE).success)


class RemoteSourcesTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        store = JsonStore(self.root / "runtime")
        self.sources = RemoteLogSourcesCommand(store)
        self.library = LogLibraryCommand(store)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_commande_scp_en_liste_sans_shell(self) -> None:
        source = RemoteLogSource(label="b; rm -rf /", host="h", remote_path="/var/log/x.log", user="u", port=2222)
        cmd = build_scp_command(source, Path("/tmp/x.log"))
        self.assertEqual(cmd[:3], ["scp", "-P", "2222"])
        self.assertIn("BatchMode=yes", cmd)
        self.assertEqual(cmd[-2:], ["u@h:/var/log/x.log", "/tmp/x.log"])
        self.assertNotIn("/", safe_cache_filename("../../etc/passwd"))

    def test_validation_et_recuperation(self) -> None:
        self.assertFalse(self.sources.save_source(label="a", host="h", remote_path="/x", port="99999").success)
        self.assertTrue(self.sources.save_source(label="web1", host="10.0.0.2", remote_path="/var/log/a.log").success)
        source = self.sources.list_sources()[0]

        def runner(cmd):
            Path(cmd[-1]).write_text("ligne\n")
            return True, ""

        result = self.sources.fetch(source, self.root / "remote", self.library, runner)
        self.assertTrue(result.success, result.message)
        self.assertEqual([(l.access, l.source, l.exists) for l in self.library.list_logs()], [("ssh", "web1", True)])
        failed = self.sources.fetch(source, self.root / "remote", self.library, lambda cmd: (False, "refusé"))
        self.assertIn("refusé", failed.message)


class OmegaServDetectorTest(unittest.TestCase):
    def test_unite_systemd_et_registre(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            main, extra = root / "serv", root / "serv2"
            for inst in (main, extra):
                (inst / "var" / "log").mkdir(parents=True)
                (inst / "var" / "log" / "access.log").write_text("")
            (main / "var" / "log" / "active-defense-enriched.jsonl").write_text("")
            (main / "var" / "log" / "notes.txt").write_text("")
            units = root / "systemd"
            units.mkdir()
            (units / "omega-serv.service").write_text(f"[Service]\nWorkingDirectory={main}\nUser=omega-serv\n")
            (units / "autre.service").write_text(f"[Service]\nWorkingDirectory={extra}\n")
            registry = root / "instances.json"
            registry.write_text(json.dumps([{"name": "seconde", "path": str(extra)},
                                            {"name": "doublon", "path": str(main)},
                                            {"name": "absente", "path": str(root / "rien")}]))

            instances = detect_omega_serv_instances((units, root / "absent"), [registry])
            self.assertEqual([(i.name, i.root) for i in instances],
                             [("omega-serv", main.resolve()), ("seconde", extra.resolve())])
            self.assertEqual([p.name for p in instance_log_files(instances[0])],
                             ["access.log", "active-defense-enriched.jsonl"])


if __name__ == "__main__":
    unittest.main()
