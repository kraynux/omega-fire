# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Aide -> Contact et support (ecrans partages d'omega-lib, D-016, 2026-11-09). Jamais de vrai envoi
ni de vrai navigateur : faux expediteur, fausse source, faux ouvreur."""
from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from omega_lib.infrastructure.declaration.json_store import JsonDeclarationStore
from omega_lib.ports.declaration import ContactSupportServices, SendOutcome
from textual.widgets import Button, Select, Static

from omega_fire.app.dependency_container import DependencyContainer
from omega_fire.core.constants import OMEGA_FIRE_VERSION
from omega_fire.infrastructure.config.paths import RUNTIME_DIR
from omega_fire.interfaces.tui.screens.help_screen import HelpScreen

from .i18n_helpers import HostApp


class _Sender:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    def send(self, payload: dict) -> SendOutcome:
        self.sent.append(payload)
        return SendOutcome(True)


class _Source:
    def fetch_sha_list(self) -> str | None:
        return "x  omega-fire-3.5.tar.gz\n"


async def _settle(pilot) -> None:
    await pilot.pause()
    await asyncio.sleep(0.2)
    await pilot.pause()


class ContactSupportTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.store_path = Path(self._tmp.name) / "declaration.json"
        self.sender = _Sender()
        self.services = ContactSupportServices(
            software="omega-fire", version="3.5", store=JsonDeclarationStore(self.store_path),
            sender=self.sender, release_source=_Source(), open_url=lambda url: False,
        )

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_container_declares_omega_fire_under_var_runtime(self) -> None:
        services = DependencyContainer().contact_support
        self.assertEqual(services.software, "omega-fire")
        self.assertEqual(services.version, OMEGA_FIRE_VERSION)
        self.assertEqual(services.store.path, RUNTIME_DIR / "declaration.json")

    def test_help_without_container_hides_the_button(self) -> None:
        async def scenario() -> None:
            app = HostApp(HelpScreen())
            async with app.run_test(size=(120, 50)) as pilot:
                await pilot.pause()
                self.assertFalse(app.screen.query("#contact-support"))

        asyncio.run(scenario())

    def test_declare_once_sends_three_part_version(self) -> None:
        async def scenario() -> None:
            app = HostApp(HelpScreen(container=SimpleNamespace(contact_support=self.services)))
            async with app.run_test(size=(120, 50)) as pilot:
                await pilot.pause()
                app.screen.query_one("#contact-support", Button).press()
                await pilot.pause()
                contact = app.screen
                self.assertEqual(type(contact).__name__, "ContactSupportScreen")
                contact.query_one("#check-update", Button).press()
                await _settle(pilot)
                self.assertIn("3.5", str(contact.query_one("#update-state", Static).render()))
                contact.query_one("#declare", Button).press()
                await pilot.pause()
                app.screen.query_one("#declaration-continent", Select).value = "EU"
                await pilot.pause()
                app.screen.query_one("#send", Button).press()
                await _settle(pilot)
                self.assertIs(app.screen, contact)

        asyncio.run(scenario())
        self.assertEqual(len(self.sender.sent), 1)
        payload = self.sender.sent[0]
        self.assertEqual((payload["logiciel"], payload["version"], payload["envoi"], payload["continent"]),
                         ("omega-fire", "3.5.0", "unique", "EU"))
        self.assertTrue(self.store_path.exists())


if __name__ == "__main__":
    unittest.main()
