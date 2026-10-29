# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Lecteurs de logs ouverts directement depuis 5.2 Favoris / 5.3 Voir les logs (version
3.5) : Classique (nouveau), Simple (Live Tail de 8.5) et lnav (8.6), garde-fou lnav seul pour
plusieurs logs, lecture depuis la fin du fichier."""
from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from textual.app import App
from textual.widgets import Button, RichLog

from omega_fire.application.commands.manage_live_tail_pins import ManageLiveTailPinsCommand
from omega_fire.domain.logs.viewer_type import ViewerType
from omega_fire.infrastructure.storage.files.json_store import JsonStore
from omega_fire.infrastructure.logs.tail_reader import FileTailReader, read_last_lines
from omega_fire.interfaces.tui.screens import live_tail_screen, lnav_screen
from omega_fire.interfaces.tui.screens.live_tail_screen import LiveTailScreen
from omega_fire.interfaces.tui.screens.log_classic_viewer_screen import LogClassicViewerScreen
from omega_fire.interfaces.tui.support.log_viewers import open_viewer


class TailReaderTest(unittest.TestCase):
    def test_dernieres_lignes_et_suivi_avec_rotation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.log"
            path.write_text("".join(f"ligne {i}\n" for i in range(5000)))
            self.assertEqual(read_last_lines(path, 3), ["ligne 4997", "ligne 4998", "ligne 4999"])
            reader = FileTailReader(path)
            self.assertEqual(reader.read_new_lines(), [])
            with path.open("a") as handle:
                handle.write("nouvelle\npartiel")
            self.assertEqual(reader.read_new_lines(), ["nouvelle"])
            path.unlink()
            path.write_text("apres rotation\n")
            self.assertEqual(reader.read_new_lines(), ["apres rotation"])


class _Host(App):
    def __init__(self) -> None:
        super().__init__()
        self.pushed: list = []


class OpenViewerTest(unittest.TestCase):
    def test_garde_fou_plusieurs_logs(self) -> None:
        app = mock.Mock()
        self.assertFalse(open_viewer(app, None, ViewerType.CLASSIC, ["/a", "/b"]))
        self.assertFalse(open_viewer(app, None, ViewerType.SIMPLE, []))
        app.push_screen.assert_not_called()

    def test_lnav_lance_directement_depuis_le_clic(self) -> None:
        """Retour utilisateur 2026-10-28 : lance a l'ouverture de l'ecran 8.6, l'interface se
        bloquait ; lnav est desormais lance par le clic lui-meme, sans ecran intermediaire."""
        app = mock.Mock()
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a.log", Path(tmp) / "b.log"
            a.write_text("x\n")
            with mock.patch.object(lnav_screen, "run_lnav") as run:
                self.assertTrue(open_viewer(app, None, ViewerType.LNAV, [str(a), str(b)]))
            run.assert_called_once_with(app, [str(a)])
            app.push_screen.assert_not_called()
            with mock.patch.object(lnav_screen, "run_lnav", side_effect=FileNotFoundError):
                self.assertFalse(open_viewer(app, None, ViewerType.LNAV, [str(a)]))


class DirectViewersTest(unittest.TestCase):
    def test_classique_affiche_puis_suit(self) -> None:
        async def run(path: Path):
            app = _Host()
            async with app.run_test(size=(80, 24)) as pilot:
                app.push_screen(LogClassicViewerScreen(container=None, path=str(path)))
                await pilot.pause()
                log = app.screen.query_one("#log-content", RichLog)
                self.assertEqual(len(log.lines), 3)
                app.screen.query_one("#follow", Button).press()
                await pilot.pause()
                with path.open("a") as handle:
                    handle.write("suivie\n")
                await pilot.pause(1.3)
                self.assertEqual(len(log.lines), 4)

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.log"
            path.write_text("un\ndeux\ntrois\n")
            asyncio.run(run(path))

    def test_simple_demarre_sur_le_log_choisi_sans_toucher_a_l_historique(self) -> None:

        async def run(path: Path, runtime: Path):
            # Une epingle presente (plus d'epingles par defaut depuis la 3.5) : c'est elle que la
            # surbrillance automatique du tableau substituait au log choisi.
            ManageLiveTailPinsCommand(JsonStore(runtime)).add_pinned("Nginx", "/var/log/nginx/access.log")
            with mock.patch.object(live_tail_screen, "RUNTIME_DIR", runtime), \
                    mock.patch.object(lnav_screen, "RUNTIME_DIR", runtime), \
                    mock.patch.object(live_tail_screen, "log_action_result", lambda *a, **k: None), \
                    mock.patch.object(lnav_screen, "log_action_result", lambda *a, **k: None):
                app = _Host()
                async with app.run_test(size=(100, 30)) as pilot:
                    app.push_screen(LiveTailScreen(container=None, source=str(path)))
                    await pilot.pause()
                    await pilot.pause()
                    self.assertNotIn("omega-hidden", app.screen.query_one("#live-panel").classes)
                    await pilot.pause(0.3)
                    # Retour utilisateur 2026-10-28 : la 1re epingle par defaut (apache) remplacait
                    # le log choisi apres la surbrillance automatique du tableau.
                    self.assertEqual(app.screen._provider.source, str(path))
                    app.screen.action_back()
                    await pilot.pause()
            self.assertFalse(any(runtime.glob("*history*")))

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "access.log"
            path.write_text('1.2.3.4 - - [28/Oct/2026:10:00:00 +0100] "GET / HTTP/1.1" 200 12\n')
            asyncio.run(run(path, Path(tmp) / "runtime"))

    def test_plus_d_epingles_par_defaut(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(ManageLiveTailPinsCommand(JsonStore(Path(tmp))).list_active_pinned(), {})


if __name__ == "__main__":
    unittest.main()
