# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Nettoyage-synchronisation de la table des regles (3.2) et exclusion des tables
iptables-nft cote nftables (retour utilisateur 2026-10-28 : 564 lignes en base, 323
regles lues dans le noyau, dont les regles ip6tables comptees deux fois)."""
from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from omega_fire.application.commands.reconcile_rules import ReconcileRulesCommand
from omega_fire.domain.rules.models import FirewallRule, RuleAction, RuleChain, RuleFamily
from omega_fire.infrastructure.backends.nftables.adapter import NftablesAdapter, iptables_nft_tables
from omega_fire.infrastructure.config.paths import MIGRATIONS_DIR
from omega_fire.infrastructure.storage.sqlite.connection import DatabaseConnection
from omega_fire.infrastructure.storage.sqlite.migrations import MigrationManager
from omega_fire.infrastructure.storage.sqlite.repositories import RuleRepository
from omega_fire.infrastructure.storage.sqlite.schema import create_schema


def _nft(handle: int, table: str = "filter", family: RuleFamily = RuleFamily.INET, **kw) -> FirewallRule:
    return FirewallRule(backend="nftables", family=family, table_name=table, chain=RuleChain.INPUT,
                        action=RuleAction.ACCEPT, external_ref=str(handle), **kw)


def _ipt(line: str, backend: str = "iptables", **kw) -> FirewallRule:
    return FirewallRule(backend=backend, family=RuleFamily.INET, table_name="filter",
                        chain=RuleChain.INPUT, action=RuleAction.ACCEPT, external_ref=line, **kw)


class _Live:
    def __init__(self, rules=None, error: Exception | None = None) -> None:
        self._rules, self._error = rules or [], error
        self.writes = 0

    def list_rules(self):
        if self._error:
            raise self._error
        return list(self._rules)

    def __getattr__(self, name):  # toute ecriture noyau serait une faute
        if name.startswith(("add", "delete", "flush", "load", "apply")):
            self.writes += 1
        raise AttributeError(name)


class ReconcileRulesTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.db = DatabaseConnection(root / "omega.db")
        self.db.connect()
        create_schema(self.db)
        manager = MigrationManager(self.db, MIGRATIONS_DIR)
        manager.ensure_schema_version_table()
        manager.apply_all_pending()
        self.repo = RuleRepository(self.db)
        self.backup_dir = root / "backups" / "db"
        self.command = ReconcileRulesCommand(self.repo, self.backup_dir)

    def tearDown(self) -> None:
        self.db.close()
        self._tmp.cleanup()

    def _save(self, rule: FirewallRule, origin: str = "imported", enabled: bool = True) -> int:
        rule.origin, rule.enabled = origin, enabled
        return self.repo.save(rule)

    def test_classe_doublons_absentes_et_imports(self) -> None:
        kept = self._save(_nft(5), origin="managed")
        self._save(_nft(5))                                  # doublon du meme handle
        self._save(_nft(9))                                  # disparu du noyau
        self._save(_nft(10), origin="managed")               # restauration : plus dans le noyau
        self._save(FirewallRule(backend="nftables", family=RuleFamily.INET, table_name="filter",
                                chain=RuleChain.INPUT), origin="managed")  # sans external_ref
        live = {"nftables": _Live([_nft(5), _nft(7)]), "iptables": _Live(), "ip6tables": _Live()}

        plan = self.command.plan(live)

        self.assertEqual([r.rule_id for r in plan.keep], [kept])  # « managed » garde en priorite
        self.assertEqual(len(plan.duplicates), 1)
        self.assertEqual(len(plan.stale), 3)
        self.assertEqual([r.external_ref for r in plan.to_import], ["7"])

    def test_meme_handle_dans_deux_tables_sont_deux_regles(self) -> None:
        self._save(_nft(3, table="filter"))
        live = {"nftables": _Live([_nft(3, table="filter"), _nft(3, table="docker")]),
                "iptables": _Live(), "ip6tables": _Live()}
        plan = self.command.plan(live)
        self.assertEqual(len(plan.keep), 1)
        self.assertEqual([(r.table_name, r.external_ref) for r in plan.to_import], [("docker", "3")])

    def test_lignes_iptables_identiques_gardees_selon_le_noyau(self) -> None:
        line = "-A ufw-before-input -i lo -j ACCEPT"
        for _i in range(3):
            self._save(_ipt(line))
        live = {"iptables": _Live([_ipt(line), _ipt(line)]), "nftables": _Live(), "ip6tables": _Live()}
        plan = self.command.plan(live)
        self.assertEqual((len(plan.keep), len(plan.duplicates)), (2, 1))

    def test_backend_illisible_jamais_touche(self) -> None:
        self._save(_ipt("-A INPUT -j ufw-before-input"))
        live = {"iptables": _Live(error=PermissionError("Operation not permitted")),
                "nftables": _Live(), "ip6tables": _Live()}
        plan = self.command.plan(live)
        self.assertIn("iptables", plan.unreadable)
        self.assertEqual(plan.to_remove, [])

    def test_backend_absent_retire(self) -> None:
        self._save(_nft(4))
        plan = self.command.plan({"nftables": None, "iptables": _Live(), "ip6tables": _Live()})
        self.assertEqual(len(plan.unavailable), 1)

    def test_apply_sauvegarde_puis_nettoie_sans_ecrire_dans_le_noyau(self) -> None:
        self._save(_nft(5), origin="managed", enabled=False)
        self._save(_nft(5))
        self._save(_nft(9))
        nft = _Live([_nft(5), _nft(7)])
        plan = self.command.plan({"nftables": nft, "iptables": _Live(), "ip6tables": _Live()})

        result = self.command.apply(plan)

        self.assertTrue(result.success, result.message)
        self.assertEqual((result.removed, result.imported, result.enabled), (2, 1, 1))
        rows = self.repo.find_all()
        self.assertEqual(sorted((r.external_ref, r.origin, r.enabled) for r in rows),
                         [("5", "managed", True), ("7", "imported", True)])
        self.assertEqual(nft.writes, 0)
        with sqlite3.connect(str(result.backup_path)) as backup:
            self.assertEqual(backup.execute("select count(*) from rules").fetchone()[0], 3)

        again = self.command.plan({"nftables": nft, "iptables": _Live(), "ip6tables": _Live()})
        self.assertFalse(again.has_changes)


class IptablesNftTablesTest(unittest.TestCase):
    _STDERR = (
        "# Warning: table ip filter is managed by iptables-nft, do not touch!\n"
        "# Warning: table ip6 filter is managed by iptables-nft, do not touch!\n"
        "# Warning: table ip nat is managed by iptables-nft, do not touch!\n"
    )
    _RULESET = (
        "table ip6 filter { # handle 2\n\tchain ufw6-before-input { # handle 3\n"
        "\t\tiifname \"lo\" counter accept # handle 10\n\t}\n}\n"
        "table ip nat { # handle 4\n\tchain POSTROUTING { # handle 5\n"
        "\t\tcounter masquerade # handle 11\n\t}\n}\n"
        "table inet filter { # handle 6\n\tchain input { # handle 7\n"
        "\t\ttcp dport 22 accept # handle 12\n\t}\n}\n"
    )

    def test_avertissements_reconnus(self) -> None:
        self.assertEqual(iptables_nft_tables(self._STDERR),
                         {("ip", "filter"), ("ip6", "filter"), ("ip", "nat")})

    def test_list_rules_ignore_les_tables_iptables_nft(self) -> None:
        adapter = NftablesAdapter.__new__(NftablesAdapter)
        from omega_fire.infrastructure.backends.nftables.mapper import NftMapper
        from omega_fire.infrastructure.backends.nftables.parser import NftParser
        adapter._parser, adapter._mapper = NftParser(), NftMapper()

        def run(cmd):
            adapter._last_stderr = self._STDERR
            return self._RULESET
        adapter._run_command = run

        rules = adapter.list_rules()
        self.assertEqual([(r.table_name, r.external_ref) for r in rules], [("filter", "12")])


if __name__ == "__main__":
    unittest.main()
