# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Politiques differentes selon les backends (3.5) : effet reel, cause, remede
(retour utilisateur 2026-10-28 : message apparu a l'initialisation de nftables, sur une
machine filtree par UFW)."""
from __future__ import annotations

import unittest
from collections import Counter

from omega_fire.application.commands.manage_tables import TableStatusEntry
from omega_fire.application.queries.policy_divergence import analyze_policies, describe_policies


def _entry(backend, input_p, forward_p="drop", output_p="accept", rules=0, exists=True):
    return TableStatusEntry(backend=backend, available=True, table_exists=exists, rule_count=rules,
                            policies={"input": input_p, "output": output_p, "forward": forward_p})


class PolicyDivergenceTest(unittest.TestCase):
    def test_table_nft_absente_pas_comparee(self) -> None:
        entries = [_entry("nftables", None, None, None, exists=False),
                   _entry("iptables", "drop", rules=83), _entry("ip6tables", "drop", rules=116)]
        self.assertEqual(describe_policies(analyze_policies(entries, {}, set())), [])

    def test_ufw_apres_initialisation_nft_information(self) -> None:
        entries = [_entry("nftables", "accept", "accept"),
                   _entry("iptables", "drop", rules=83), _entry("ip6tables", "drop", rules=116)]
        foreign = {"iptables": Counter({"UFW": 79, "Tailscale": 4}), "ip6tables": Counter({"UFW": 112})}
        analysis = analyze_policies(entries, foreign, set())
        self.assertEqual([(d.chain, d.effective) for d in analysis.chains], [("input", "drop"), ("forward", "drop")])
        self.assertFalse(analysis.has_alert)
        lines = describe_policies(analysis)
        self.assertIn("INPUT : nftables ACCEPT · iptables DROP · ip6tables DROP → en pratique DROP", lines[1])
        causes = [line for line in lines if line.startswith("  •")]
        # iptables (UFW + Tailscale) et ip6tables (UFW seul) : deux causes distinctes.
        self.assertEqual(len(causes), 2)
        self.assertIn("Rien à faire", causes[0])

    def test_drop_orphelin_alerte_avec_remede(self) -> None:
        entries = [_entry("nftables", "drop", rules=0), _entry("iptables", "accept", "accept", rules=0)]
        analysis = analyze_policies(entries, {}, set())
        self.assertTrue(analysis.has_alert)
        self.assertIn("Remettre les politiques à ACCEPT", describe_policies(analysis)[-1])

    def test_profil_actif_et_regles_sans_profil(self) -> None:
        entries = [_entry("nftables", "drop", rules=12), _entry("iptables", "accept", "accept"),
                   _entry("ip6tables", "drop", rules=3)]
        analysis = analyze_policies(entries, {}, {"nftables"})
        kinds = {c.kind: c.backends for c in analysis.causes}
        self.assertEqual(kinds, {"preset": ["nftables"], "rules": ["ip6tables"]})
        self.assertFalse(analysis.has_alert)


if __name__ == "__main__":
    unittest.main()
