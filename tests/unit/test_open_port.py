# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""`omega-fire.sh port ouvrir` (demande omega-serv du 2026-11-17, administration web) : arguments, une règle ACCEPT
par réseau et par backend (doublon = déjà ouvert, IPv6 ignoré sur iptables), ufw / firewalld actifs ouverts aussi,
root obligatoire, aiguillage depuis bootstrap. Jamais le vrai pare-feu : tout est simulé."""

from __future__ import annotations

from types import SimpleNamespace
from typing import ClassVar
from unittest.mock import patch

from omega_fire.app import bootstrap, port_runner
from omega_fire.application.commands.open_port import (
    IGNORED,
    OpenPortCommand,
    OpenPortRequest,
)
from omega_fire.infrastructure.backends.host_firewall.adapter import SystemHostFirewall
from omega_fire.ports.host_firewall import ADDED, ALREADY, FAILED

ARGS = ["ouvrir", "--port", "9643", "--sources", "127.0.0.0/8,192.168.1.0/24,fc00::/7,192.168.1.0/24",
        "--pour", "omega-serv:prod"]


def test_arguments_are_checked_and_loopback_dropped():
    assert port_runner.parse(ARGS) == (9643, ("192.168.1.0/24", "fc00::/7"), "omega-serv:prod")
    assert port_runner.parse([*ARGS, "--format", "json"]) == port_runner.parse(ARGS)
    for index, value in ((2, "0"), (2, "70000"), (2, "abc"), (4, "pas-un-reseau"), (4, "127.0.0.1"),
                         (6, "omega serv"), (6, "-x")):
        bad = list(ARGS)
        bad[index] = value
        assert port_runner.parse(bad) is None, value
    assert port_runner.parse(["fermer", *ARGS[1:]]) is None
    assert port_runner.parse(ARGS[:5]) is None


class _Create:
    """Faux CreateRuleCommand : réponse par (backend, source)."""

    answers: ClassVar[dict] = {}
    calls: ClassVar[list] = []

    def __init__(self, repository, adapter):
        self.adapter = adapter

    def execute(self, request):
        _Create.calls.append((request.backend, request.source_cidr, request.action, request.chain, request.dst_port,
                              request.name))
        return _Create.answers[(request.backend, request.source_cidr)]


class _Host:
    def __init__(self, name, answer=(ADDED, "")):
        self.name, self.answer, self.calls = name, answer, []

    def active_name(self):
        return self.name

    def allow(self, port, source, comment):
        self.calls.append((port, source, comment))
        return self.answer


def _outcome(success=True, applied=True, duplicate=None, message=""):
    return SimpleNamespace(success=success, applied=applied, duplicate_of=duplicate, rule_id=7, message=message)


def test_one_accept_rule_per_network_and_backend_then_ufw():
    _Create.calls = []
    _Create.answers = {("nftables", "10.0.0.0/8"): _outcome(), ("iptables", "10.0.0.0/8"): _outcome(duplicate=3),
                       ("nftables", "fc00::/7"): _outcome(success=False, applied=False, message="nft: erreur")}
    host = _Host("ufw")
    result = OpenPortCommand(object(), {"nftables": "a", "iptables": "b"}, host, create=_Create).execute(
        OpenPortRequest(9643, ("10.0.0.0/8", "fc00::/7"), "omega-serv:prod"))
    assert [(line.target, line.source, line.state) for line in result.lines] == [
        ("nftables", "10.0.0.0/8", ADDED), ("iptables", "10.0.0.0/8", ALREADY), ("ufw", "10.0.0.0/8", ADDED),
        ("nftables", "fc00::/7", FAILED), ("iptables", "fc00::/7", IGNORED), ("ufw", "fc00::/7", ADDED)]
    assert _Create.calls[0] == ("nftables", "10.0.0.0/8", "ACCEPT", "INPUT", 9643, "omega-serv:prod 9643/tcp")
    assert host.calls[0] == (9643, "10.0.0.0/8", "omega-serv:prod 9643/tcp")
    assert not result.ok  # une ligne en échec
    _Create.answers[("nftables", "fc00::/7")] = _outcome()
    assert OpenPortCommand(object(), {"nftables": "a", "iptables": "b"}, _Host(""), create=_Create).execute(
        OpenPortRequest(9643, ("10.0.0.0/8", "fc00::/7"), "omega-serv:prod")).ok


def test_ufw_and_firewalld_answers():
    def runner(answers):
        calls = []

        def run(command):
            calls.append(list(command))
            for prefix, answer in answers:
                if list(command[:len(prefix)]) == prefix:
                    return answer
            return 1, ""
        return run, calls

    run, calls = runner([(["ufw", "status"], (0, "Status: active\n\nTo Action From")),
                         (["ufw", "allow"], (0, "Rule added"))])
    ufw = SystemHostFirewall(run, which=lambda name: "/usr/bin/" + name)
    assert ufw.active_name() == "ufw"
    assert ufw.allow(9643, "10.0.0.0/8", "omega-serv 9643/tcp")[0] == ADDED
    assert calls[-1] == ["ufw", "allow", "proto", "tcp", "from", "10.0.0.0/8", "to", "any", "port", "9643",
                         "comment", "omega-serv 9643/tcp"]
    run, _calls = runner([(["ufw", "status"], (0, "Status: active")), (["ufw", "allow"], (0, "Skipping adding existing rule"))])
    assert SystemHostFirewall(run, which=lambda name: name).allow(9643, "10.0.0.0/8", "x")[0] == ALREADY
    run, calls = runner([(["ufw", "status"], (0, "Status: inactive")), (["firewall-cmd", "--state"], (0, "running")),
                         (["firewall-cmd"], (0, "Warning: ALREADY_ENABLED"))])
    firewalld = SystemHostFirewall(run, which=lambda name: name)
    assert firewalld.active_name() == "firewalld"
    assert firewalld.allow(9643, "fc00::/7", "x")[0] == ALREADY
    assert 'rule family="ipv6" source address="fc00::/7" port port="9643" protocol="tcp" accept' in calls[-1][-1]
    assert calls[-1][1] == "--permanent"
    assert SystemHostFirewall(lambda command: (1, ""), which=lambda name: None).active_name() == ""


def test_root_required_and_usage(capsys):
    assert port_runner.run_port(["ouvrir"]) == 2
    with patch.object(port_runner.os, "geteuid", return_value=1000):
        assert port_runner.run_port(ARGS) == 1
    assert "root required" in capsys.readouterr().err


def test_bootstrap_dispatches_port_without_interface():
    with patch.object(bootstrap.sys, "argv", ["omega_fire", "port", *ARGS]), \
            patch.object(port_runner, "run_port", return_value=0) as run, \
            patch.object(bootstrap, "bootstrap_tui") as tui:
        assert bootstrap.main() == 0
    run.assert_called_once_with(ARGS)
    tui.assert_not_called()
