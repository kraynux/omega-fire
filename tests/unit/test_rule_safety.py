# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Securisation de la restauration 7.2 et signalement des regles d'autres outils
(retour utilisateur 2026-10-28, machine avec UFW + Tailscale : 7.2 retirait les regles
UFW importees, remettait INPUT a ACCEPT et reappliquait des regles sans leurs criteres)."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from omega_fire.application.commands import restore_state
from omega_fire.application.commands.restore_state import RestoreStateCommand, RestoreStateRequest
from omega_fire.domain.persistence.backup import build_rules_snapshot
from omega_fire.domain.rules.models import FirewallRule, RuleAction, RuleChain, RuleFamily
from omega_fire.domain.rules.ownership import rule_owner
from omega_fire.infrastructure.backends.iptables.mapper import IptMapper
from omega_fire.infrastructure.backends.iptables.parser import IptParser
from omega_fire.infrastructure.backends.nftables.mapper import NftMapper
from omega_fire.infrastructure.backends.nftables.parser import NftParser
from omega_fire.infrastructure.backends.rule_fidelity import (
    iptables_rule_restorable,
    nft_rule_restorable,
)


class FidelityTest(unittest.TestCase):
    def test_regles_omega_restaurables(self) -> None:
        for raw in (
            "-A INPUT -p tcp -m tcp --dport 22 -j ACCEPT",
            '-A INPUT -s 192.168.1.0/24 -p tcp -m tcp --dport 445 -m comment --comment "partage SMB" -j ACCEPT',
            "-A INPUT -s 203.0.113.7/32 -j DROP",
            "-A INPUT -p tcp -m tcp --dport 23 -j REJECT --reject-with icmp-port-unreachable",
            "-A INPUT -s 2001:db8::/32 -p ipv6-icmp -j ACCEPT",
        ):
            self.assertTrue(iptables_rule_restorable(raw), raw)
        for raw in (
            'tcp dport 22 counter packets 4 bytes 240 accept comment "SSH" # handle 7',
            "ip saddr 192.168.1.0/24 tcp dport 445 accept # handle 9",
            "meta l4proto icmp accept # handle 3",
            "ip6 saddr 2001:db8::/32 drop # handle 12",
        ):
            self.assertTrue(nft_rule_restorable("inet", "filter", "input", raw), raw)

    def test_criteres_perdus_ou_chaine_etrangere_non_restaurables(self) -> None:
        for raw in (
            "-A ufw-before-input -i lo -j ACCEPT",
            "-A INPUT -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT",
            "-A INPUT -i lo -j ACCEPT",
            "-A INPUT -j ufw-before-input",
            "-A INPUT -p icmp -m icmp --icmp-type 8 -j ACCEPT",
            "-A INPUT -m limit --limit 3/min -j LOG --log-prefix \"[UFW] \"",
            "-A INPUT ! -s 10.0.0.0/8 -j DROP",
            "-A INPUT -p tcp -m tcp --dport 22 -j REJECT --reject-with tcp-reset",
        ):
            self.assertFalse(iptables_rule_restorable(raw), raw)
        self.assertFalse(nft_rule_restorable("inet", "filter", "input", "ct state established,related accept # handle 4"))
        self.assertFalse(nft_rule_restorable("inet", "filter", "input", 'iifname "lo" accept # handle 5'))
        self.assertFalse(nft_rule_restorable("inet", "filter", "input", "tcp dport { 22, 80 } accept # handle 6"))
        self.assertFalse(nft_rule_restorable("inet", "filter", "input", "ct state invalid drop # handle 8"))
        self.assertFalse(nft_rule_restorable("ip6", "filter", "INPUT", "tcp dport 22 accept # handle 9"))
        self.assertFalse(nft_rule_restorable("inet", "filter", "ufw-user-input", "tcp dport 22 accept # handle 9"))

    def test_mappers_renseignent_chaine_et_fidelite(self) -> None:
        ipt = IptMapper().map_rules(IptParser().parse_rules_save(
            "-P INPUT DROP\n-A INPUT -j ufw-before-input\n-A ufw-user-input -p tcp -m tcp --dport 22 -j ACCEPT\n"
            "-A INPUT -p tcp -m tcp --dport 8080 -j ACCEPT\n"
        ))
        self.assertEqual([(r.chain_name, r.restorable) for r in ipt],
                         [("INPUT", False), ("ufw-user-input", False), ("INPUT", True)])
        # La chaine UFW est rangee dans INPUT par le mapper : seul chain_name la distingue.
        self.assertEqual(ipt[1].chain, RuleChain.INPUT)
        nft = NftMapper().map_rules(NftParser().parse_ruleset(
            "table inet filter { # handle 1\n\tchain input { # handle 2\n"
            "\t\tct state established,related accept # handle 3\n"
            "\t\ttcp dport 22 accept # handle 4\n\t}\n}\n"
        ))
        self.assertEqual([r.restorable for r in nft], [False, True])
        snap = build_rules_snapshot(ipt + nft)
        self.assertEqual([(r["chain_name"], r["restorable"]) for r in snap.rules][-2:],
                         [("input", False), ("input", True)])


class OwnershipTest(unittest.TestCase):
    def _ipt(self, raw: str, backend: str = "iptables") -> FirewallRule:
        return FirewallRule(backend=backend, family=RuleFamily.INET, table_name="filter",
                            chain=RuleChain.INPUT, external_ref=raw)

    def test_outils_reconnus(self) -> None:
        self.assertEqual(rule_owner(self._ipt("-A ufw-before-input -i lo -j ACCEPT")), "UFW")
        self.assertEqual(rule_owner(self._ipt("-A ufw6-user-input -p tcp -j ACCEPT", "ip6tables")), "UFW")
        self.assertEqual(rule_owner(self._ipt("-A ts-input -i tailscale0 -j ACCEPT")), "Tailscale")
        self.assertEqual(rule_owner(self._ipt("-A DOCKER-USER -j RETURN")), "Docker")
        self.assertEqual(rule_owner(self._ipt("-A f2b-sshd -s 1.2.3.4/32 -j REJECT")), "Fail2Ban")
        self.assertEqual(rule_owner(self._ipt("-A MA-CHAINE -j ACCEPT")), "MA-CHAINE")
        nft = FirewallRule(backend="nftables", family=RuleFamily.INET, table_name="firewalld",
                           chain=RuleChain.INPUT, external_ref="4")
        self.assertEqual(rule_owner(nft), "firewalld")

    def test_regles_omega_sans_proprietaire(self) -> None:
        self.assertIsNone(rule_owner(self._ipt("-A INPUT -p tcp -m tcp --dport 22 -j ACCEPT")))
        self.assertIsNone(rule_owner(FirewallRule(backend="nftables", family=RuleFamily.INET,
                                                  table_name="filter", chain=RuleChain.INPUT, external_ref="7")))


class _Adapter:
    def __init__(self, live=()) -> None:
        self.live = list(live)
        self.calls: list[tuple] = []

    def list_rules(self):
        return list(self.live)

    def add_rule(self, **kw):
        self.calls.append(("add", kw.get("chain"), kw.get("port")))
        return True

    def delete_rule_by_content(self, ref):
        self.calls.append(("delete", ref))
        return True

    def delete_rule(self, **kw):
        self.calls.append(("delete", kw.get("handle")))
        return True

    def set_chain_policy(self, chain, policy):
        self.calls.append(("policy", chain, policy))


class _Repo:
    def __init__(self, rules) -> None:
        self.rules = list(rules)
        self.deleted: list[int] = []

    def find_all(self, backend=None):
        return list(self.rules)

    def delete(self, rule_id):
        self.deleted.append(rule_id)
        return True

    def save(self, rule):
        return 1000

    def update_external_ref(self, *_a):
        return True


def _snapshot(rules: list[dict]):
    content = SimpleNamespace(rules=SimpleNamespace(rules=rules), blacklist=None, fail2ban=None)
    return SimpleNamespace(content=content)


def _row(rule_id: int, raw: str, origin: str) -> FirewallRule:
    return FirewallRule(backend="iptables", family=RuleFamily.INET, table_name="filter",
                        chain=RuleChain.INPUT, action=RuleAction.ACCEPT, external_ref=raw,
                        origin=origin, rule_id=rule_id)


class RestoreSafetyTest(unittest.TestCase):
    UFW = "-A ufw-before-input -i lo -j ACCEPT"
    OMEGA = "-A INPUT -p tcp -m tcp --dport 8080 -j ACCEPT"

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.no_preset = mock.patch.object(restore_state, "state_file_for",
                                           lambda b: Path(self._tmp.name) / f"absent-{b}")
        self.no_preset.start()

    def tearDown(self) -> None:
        self.no_preset.stop()
        self._tmp.cleanup()

    def _run(self, snapshot_rules, repo_rows, live=()):
        ipt = _Adapter(live)
        port = SimpleNamespace(get_snapshot_content=lambda _id: _snapshot(snapshot_rules))
        repo = _Repo(repo_rows)
        result = RestoreStateCommand(port, {"iptables": ipt}, repo).execute(RestoreStateRequest("s"))
        return result, ipt, repo

    def test_regles_ufw_importees_jamais_retirees_et_politique_intacte(self) -> None:
        rows = [_row(1, self.UFW, "imported"), _row(2, self.OMEGA, "managed")]
        snap = [
            {"backend": "iptables", "chain": "input", "action": "accept", "port": "8080",
             "protocol": "tcp", "order": 0, "restorable": True},
            {"backend": "iptables", "chain": "input", "action": "accept", "port": "*",
             "order": 1, "restorable": False},
        ]
        result, ipt, repo = self._run(snap, rows, live=[_row(9, self.UFW, "imported"), _row(9, self.OMEGA, "imported")])

        self.assertTrue(result.success)
        self.assertIn(("delete", self.OMEGA), ipt.calls)
        self.assertNotIn(("delete", self.UFW), ipt.calls)
        self.assertNotIn(1, repo.deleted)
        self.assertEqual([c for c in ipt.calls if c[0] == "add"], [("add", "INPUT", "8080")])
        self.assertFalse([c for c in ipt.calls if c[0] == "policy"])
        self.assertEqual(result.rules_skipped, 1)

    def test_ancien_snapshot_ne_touche_a_aucune_regle(self) -> None:
        rows = [_row(2, self.OMEGA, "managed")]
        old = [{"backend": "iptables", "chain": "input", "action": "accept", "port": "*", "order": 0},
               {"backend": "iptables", "chain": "input", "action": "drop", "port": "*", "order": 1}]
        result, ipt, repo = self._run(old, rows, live=[_row(9, self.OMEGA, "imported")])
        self.assertTrue(result.success)
        self.assertEqual([c for c in ipt.calls if c[0] in ("add", "delete")], [])
        self.assertEqual(repo.deleted, [])
        self.assertEqual(result.rules_skipped, 2)

    def test_politique_remise_seulement_si_profil_actif(self) -> None:
        self.no_preset.stop()
        marker = Path(self._tmp.name) / "preset-iptables"
        marker.write_text("x")
        with mock.patch.object(restore_state, "state_file_for",
                               lambda b: marker if b == "iptables" else Path(self._tmp.name) / "absent"):
            _result, ipt, _repo = self._run([], [])
        self.no_preset.start()
        self.assertIn(("policy", "input", "ACCEPT"), ipt.calls)


if __name__ == "__main__":
    unittest.main()
