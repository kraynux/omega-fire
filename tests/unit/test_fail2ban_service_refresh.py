# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Retour utilisateur 2026-10-28 : apres « Démarrer le service » (4.10), fail2ban restait
« inactif » au tableau de bord jusqu'au prochain re-scan (1.3). Demarrer / arreter /
redemarrer attend maintenant que le serveur reponde (ou plus) puis re-scanne le registre
des capacites, que lit le tableau de bord."""
from __future__ import annotations

import unittest
from unittest import mock

from omega_fire.interfaces.tui.support import direct_actions
from omega_fire.interfaces.tui.support.direct_actions import (
    fail2ban_service_enable,
    fail2ban_service_start,
    fail2ban_service_stop,
    wait_for_fail2ban,
)


class _Port:
    """Serveur qui ne repond a `ping` qu'apres `delay` appels (socket pas encore ouverte)."""

    def __init__(self, delay: int = 2, up: bool = False) -> None:
        self.delay = delay
        self.up = up
        self.calls: list[str] = []

    def start_service(self) -> None:
        self.calls.append("start")
        self.up = True

    def stop_service(self) -> None:
        self.calls.append("stop")
        self.up = False

    def enable_service(self) -> None:
        self.calls.append("enable")

    def is_available(self) -> bool:
        if self.delay:
            self.delay -= 1
            return not self.up
        return self.up


class _Container:
    def __init__(self, port: _Port) -> None:
        self._port = port
        self.scanner = mock.Mock()
        self.scanner.scan.side_effect = lambda: self._port.calls.append("scan") or {}

    def get_fail2ban_port(self) -> _Port:
        return self._port


class Fail2banRefreshTest(unittest.TestCase):
    def setUp(self) -> None:
        patcher = mock.patch.object(direct_actions.time, "sleep", lambda _s: None)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_demarrage_attend_le_serveur_puis_rescanne(self) -> None:
        port = _Port(delay=2)
        ok, message = fail2ban_service_start(_Container(port))
        self.assertTrue(ok)
        self.assertEqual(port.calls, ["start", "scan"])
        self.assertEqual(port.delay, 0)  # le scan n'a lieu qu'une fois le ping repondu
        self.assertIn("tableau de bord", message)

    def test_arret_rescanne_aussi(self) -> None:
        port = _Port(delay=0, up=True)
        ok, _message = fail2ban_service_stop(_Container(port))
        self.assertTrue(ok)
        self.assertEqual(port.calls, ["stop", "scan"])

    def test_activation_au_boot_ne_rescanne_pas(self) -> None:
        port = _Port(delay=0)
        self.assertTrue(fail2ban_service_enable(_Container(port))[0])
        self.assertEqual(port.calls, ["enable"])

    def test_delai_depasse(self) -> None:
        port = _Port(delay=0, up=False)
        now = iter(range(100))
        self.assertFalse(wait_for_fail2ban(port, expect_up=True, timeout=3, sleep=lambda _s: None,
                                           clock=lambda: next(now)))


if __name__ == "__main__":
    unittest.main()
