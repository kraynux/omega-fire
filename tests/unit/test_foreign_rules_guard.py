# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Garde-fou avant de vider iptables / ip6tables quand d'autres outils (UFW,
Tailscale...) y ont des regles (retour utilisateur 2026-10-28 : l'utilisateur decide,
l'aide detaille les consequences)."""
from __future__ import annotations

import asyncio
import unittest
from types import SimpleNamespace
from unittest import mock

from textual.app import App
from textual.widgets import Button

from omega_fire.application.queries.foreign_rules import describe_foreign_rules, foreign_rules_by_backend
from omega_fire.domain.rules.models import FirewallRule, RuleChain, RuleFamily
from omega_fire.interfaces.cli.help_text import get_help_entry
from omega_fire.interfaces.tui.screens import apply_preset_screen
from omega_fire.interfaces.tui.screens.choice import ChoiceScreen


def _ipt(raw: str, backend: str = "iptables") -> FirewallRule:
    return FirewallRule(backend=backend, family=RuleFamily.INET, table_name="filter",
                        chain=RuleChain.INPUT, external_ref=raw)


class _Adapter:
    def __init__(self, rules=(), error=None) -> None:
        self._rules, self._error = list(rules), error

    def list_rules(self):
        if self._error:
            raise self._error
        return list(self._rules)


UFW = "-A ufw-before-input -i lo -j ACCEPT"
TS = "-A ts-input -i tailscale0 -j ACCEPT"
OMEGA = "-A INPUT -p tcp -m tcp --dport 22 -j ACCEPT"


class ForeignRulesQueryTest(unittest.TestCase):
    def test_compte_par_backend_et_par_outil(self) -> None:
        found = foreign_rules_by_backend({
            "nftables": _Adapter([FirewallRule(backend="nftables", family=RuleFamily.IP, table_name="nat",
                                               chain=RuleChain.INPUT, external_ref="3")]),
            "iptables": _Adapter([_ipt(UFW), _ipt(UFW), _ipt(TS), _ipt(OMEGA)]),
            "ip6tables": _Adapter([_ipt(OMEGA, "ip6tables")]),
        })
        # nftables jamais compte : Omega-Fire n'y vide que sa propre table.
        self.assertEqual(found, {"iptables": {"UFW": 2, "Tailscale": 1}})
        self.assertEqual(describe_foreign_rules(found), "iptables : Tailscale 1, UFW 2")

    def test_backend_illisible_ou_absent_ignore(self) -> None:
        self.assertEqual(foreign_rules_by_backend({"iptables": _Adapter(error=PermissionError()), "ip6tables": None}), {})

    def test_aide_detaille_les_consequences(self) -> None:
        for node in ("3.4", "3.5"):
            entry = get_help_entry(node)
            self.assertIsNotNone(entry, node)
            text = " ".join(entry.consequences + entry.warnings)
            self.assertIn("UFW", text, node)
            self.assertIn("iptables -F", text, node)


class _Host(App):
    def __init__(self, screen) -> None:
        super().__init__()
        self._first = screen
        self.result = "unset"

    def on_mount(self) -> None:
        self.push_screen(self._first, lambda value: setattr(self, "result", value))


class ChoiceScreenTest(unittest.TestCase):
    def test_retourne_le_choix_ou_none(self) -> None:
        async def run(button_id: str):
            app = _Host(ChoiceScreen(title="T", message="M", choices=[("Tout", "all", "error"), ("nft", "nftables", "warning")]))
            async with app.run_test(size=(80, 24)) as pilot:
                await pilot.pause()
                app.screen.query_one(f"#{button_id}", Button).press()
                await pilot.pause()
            return app.result

        self.assertEqual(asyncio.run(run("choice-nftables")), "nftables")
        self.assertIsNone(asyncio.run(run("cancel")))


class ApplyPresetGuardTest(unittest.TestCase):
    def test_seulement_nftables_retire_iptables_et_ip6tables(self) -> None:
        adapters = {"nftables": _Adapter(), "iptables": _Adapter([_ipt(UFW)]), "ip6tables": _Adapter()}
        registry = SimpleNamespace(is_available=lambda name: name in ("nftables", "iptables"))
        container = SimpleNamespace(
            capability_registry=registry, rule_repository=None,
            get_firewall_port=lambda name: adapters[name],
            get_fail2ban_port=lambda: None, get_persistence_port=lambda: None,
        )
        seen: dict = {}

        class _Command:
            def __init__(self, *, adapters, persistence_port, rule_repository) -> None:
                seen.update(adapters)

            def execute(self, request):
                return SimpleNamespace(snapshot_warning=None, outcomes=[])

        async def run():
            with mock.patch.object(apply_preset_screen, "ApplyPresetToAllBackendsCommand", _Command), \
                    mock.patch.object(apply_preset_screen, "_active_preset_keys", lambda c: set()), \
                    mock.patch.object(apply_preset_screen, "log_action_result", lambda *a, **k: None):
                app = _Host(apply_preset_screen.ApplyPresetScreen(container=container))
                async with app.run_test(size=(100, 40)) as pilot:
                    await pilot.pause()
                    app.screen.query_one("#launch", Button).press()
                    await pilot.pause()
                    self.assertIsInstance(app.screen, ChoiceScreen)
                    app.screen.query_one("#choice-nftables", Button).press()
                    for _i in range(20):
                        await pilot.pause()
                        if seen:
                            break

        asyncio.run(run())
        self.assertIsNotNone(seen.get("nftables"))
        self.assertIsNone(seen.get("iptables"))
        self.assertIsNone(seen.get("ip6tables"))


if __name__ == "__main__":
    unittest.main()
