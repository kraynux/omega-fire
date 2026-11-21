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
from textual.widgets import Button, DataTable, RichLog

from omega_fire.application.commands.manage_live_tail_pins import (
    ManageLiveTailPinsCommand,
)
from omega_fire.domain.logs.viewer_type import ViewerType
from omega_fire.infrastructure.logs.tail_reader import FileTailReader, read_last_lines
from omega_fire.infrastructure.storage.files.json_store import JsonStore
from omega_fire.interfaces.tui.screens import live_tail_screen, lnav_screen
from omega_fire.interfaces.tui.screens.live_tail_screen import LiveTailScreen
from omega_fire.interfaces.tui.screens.log_classic_viewer_screen import (
    LogClassicViewerScreen,
)
from omega_fire.interfaces.tui.support.log_viewers import open_viewer


class TailReaderTest(unittest.TestCase):
    def test_dernieres_lignes_et_suivi_avec_rotation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.log"
            path.write_text("".join(f"ligne {i}\n" for i in range(5000)))
            self.assertEqual(
                read_last_lines(path, 3), ["ligne 4997", "ligne 4998", "ligne 4999"]
            )
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
                self.assertTrue(
                    open_viewer(app, None, ViewerType.LNAV, [str(a), str(b)])
                )
            run.assert_called_once_with(app, [str(a)])
            app.push_screen.assert_not_called()
            with mock.patch.object(
                lnav_screen, "run_lnav", side_effect=FileNotFoundError
            ):
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
            ManageLiveTailPinsCommand(JsonStore(runtime)).add_pinned(
                "Nginx", "/var/log/nginx/access.log"
            )
            with (
                mock.patch.object(live_tail_screen, "RUNTIME_DIR", runtime),
                mock.patch.object(lnav_screen, "RUNTIME_DIR", runtime),
                mock.patch.object(
                    live_tail_screen, "log_action_result", lambda *a, **k: None
                ),
                mock.patch.object(
                    lnav_screen, "log_action_result", lambda *a, **k: None
                ),
            ):
                app = _Host()
                async with app.run_test(size=(100, 30)) as pilot:
                    app.push_screen(LiveTailScreen(container=None, source=str(path)))
                    await pilot.pause()
                    await pilot.pause()
                    self.assertNotIn(
                        "omega-hidden", app.screen.query_one("#live-panel").classes
                    )
                    await pilot.pause(0.3)
                    # Retour utilisateur 2026-10-28 : la 1re epingle par defaut (apache) remplacait
                    # le log choisi apres la surbrillance automatique du tableau.
                    self.assertEqual(app.screen._reader.source, str(path))
                    app.screen.action_back()
                    await pilot.pause()
            self.assertFalse(any(runtime.glob("*history*")))

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "access.log"
            path.write_text(
                '1.2.3.4 - - [28/Oct/2026:10:00:00 +0100] "GET / HTTP/1.1" 200 12\n'
            )
            asyncio.run(run(path, Path(tmp) / "runtime"))

    def test_simple_affiche_tout_le_tampon_avec_ascenseur(self) -> None:
        """Retour utilisateur 2026-11-02 : comme le viewer Simple d'omega-serv (reference), tout le
        tampon defile, du plus ancien au plus recent, ouvert sur les dernieres lignes - avant : les 30
        plus recentes en tete, sans ascenseur."""

        async def run(path: Path, runtime: Path):
            with (
                mock.patch.object(live_tail_screen, "RUNTIME_DIR", runtime),
                mock.patch.object(
                    live_tail_screen, "log_action_result", lambda *a, **k: None
                ),
            ):
                app = _Host()
                async with app.run_test(size=(120, 40)) as pilot:
                    app.push_screen(LiveTailScreen(container=None, source=str(path)))
                    await pilot.pause()
                    await pilot.pause()
                    await pilot.pause(0.3)
                    table = app.screen.query_one("#logs-table", DataTable)
                    self.assertEqual(table.row_count, 200)
                    self.assertIn(
                        "/p0", str(table.get_row_at(0)[8])
                    )  # plus ancien en haut
                    self.assertIn(
                        "/p199", str(table.get_row_at(199)[8])
                    )  # plus recent en bas
                    self.assertGreater(table.max_scroll_y, 0)
                    self.assertGreaterEqual(table.scroll_y, table.max_scroll_y - 1)
                    app.screen.action_back()
                    await pilot.pause()

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "access.log"
            path.write_text(
                "".join(
                    f'1.2.3.{i % 9} - - [02/Nov/2026:07:{i // 60:02d}:{i % 60:02d} +0000] "GET /p{i} HTTP/1.1" 200 12\n'
                    for i in range(200)
                )
            )
            asyncio.run(run(path, Path(tmp) / "runtime"))

    def test_simple_aligne_sur_omega_serv(self) -> None:
        """A_FAIRE §9 (2026-11-21) : colonnes du viewer Simple d'omega-serv + Type ; ligne entiere (User-Agent
        visible) ; Service lu sur l'etiquette syslog (jamais l'heure) ; taille, duree et agent jamais
        inventes ; Type d'apres le vrai User-Agent."""

        async def run(path: Path, runtime: Path):
            with (
                mock.patch.object(live_tail_screen, "RUNTIME_DIR", runtime),
                mock.patch.object(
                    live_tail_screen, "log_action_result", lambda *a, **k: None
                ),
            ):
                app = _Host()
                async with app.run_test(size=(140, 40)) as pilot:
                    app.push_screen(LiveTailScreen(container=None, source=str(path)))
                    await pilot.pause()
                    await pilot.pause(0.3)
                    table = app.screen.query_one("#logs-table", DataTable)
                    labels = [str(c.label) for c in table.columns.values()]
                    self.assertEqual(
                        labels,
                        ["Heure", "Niveau", "Source", "IP", "Type", "Service", "Code", "Durée", "Message"],
                    )
                    self.assertEqual(table.row_count, 3)
                    access, curl, syslog = (table.get_row_at(i) for i in range(3))
                    self.assertIn("Firefox/1.0", str(access[8]))  # ligne entiere, User-Agent compris
                    self.assertIn("Web", str(access[4]))
                    self.assertIn("CLI", str(curl[4]))
                    self.assertEqual(str(access[7]), "-")  # pas de duree dans le log : rien d'invente
                    self.assertEqual(str(syslog[5]), "sshd")  # pas « 10 » (heure de la date)
                    self.assertEqual(str(syslog[4]), "-")  # pas de User-Agent : pas de type suppose
                    stats = str(app.screen.query_one("#stats-box").render())
                    self.assertIn(" ⏱ Latence moy. : -", stats)
                    self.assertNotIn("350", stats)
                    app.screen.action_back()
                    await pilot.pause()

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "mixed.log"
            path.write_text(
                '203.0.113.7 - - [21/Nov/2026:10:00:00 +0000] "GET /a.png HTTP/1.1" 200 1076 "-" "Mozilla/5.0 Firefox/1.0"\n'
                '203.0.113.8 - - [21/Nov/2026:10:00:05 +0000] "GET /x HTTP/1.1" 404 - "-" "curl/8.1"\n'
                "Nov 21 10:00:09 machine sshd[812]: Failed password for root from 198.51.100.4 port 22\n"
            )
            asyncio.run(run(path, Path(tmp) / "runtime"))

    def test_url_relue_sans_doublons(self) -> None:
        """Une URL se relit en entier : seules les lignes nouvelles entrent au tampon (avant le 2026-11-21,
        toute la fin du fichier etait rajoutee toutes les 2 s)."""
        overlap = live_tail_screen._lines_after_overlap
        self.assertEqual(overlap([], ["a", "b"]), ["a", "b"])
        self.assertEqual(overlap(["a", "b"], ["a", "b", "c"]), ["c"])
        self.assertEqual(overlap(["a", "b", "c"], ["b", "c", "d", "e"]), ["d", "e"])
        self.assertEqual(overlap(["a", "b"], ["a", "b"]), [])
        self.assertEqual(overlap(["x"], ["a", "b"]), ["a", "b"])  # rotation : tout est nouveau

    def test_plus_d_epingles_par_defaut(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(
                ManageLiveTailPinsCommand(JsonStore(Path(tmp))).list_active_pinned(), {}
            )


if __name__ == "__main__":
    unittest.main()
