# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ouvrir un port TCP depuis des réseaux précis, sans interface (`omega-fire.sh port ouvrir`), pour un outil relié
par omega-connect : omega-serv l'appelle pour son administration web (plan omega-serv tableau de bord web §9.4,
sous-lot 8b ; décisions de l'auteur du 2026-11-17).

Pour chaque réseau : une règle ACCEPT (chaîne INPUT, tcp, port) sur chaque backend d'omega-fire détecté, par la même
commande que le menu 3.1 (CreateRuleCommand : base, puis noyau) ; une règle identique déjà en base = « déjà ouvert ».
IPv6 sur iptables : ignoré (iptables ne porte que l'IPv4 ; nftables, table inet, porte les deux). Puis, si ufw ou
firewalld est actif, la même ouverture chez lui : sinon le paquet, accepté par omega-fire, serait refusé par lui."""

from __future__ import annotations

import ipaddress
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from omega_fire.application.commands.create_rule import (
    CreateRuleCommand,
    CreateRuleRequest,
)
from omega_fire.ports.host_firewall import ADDED, ALREADY, FAILED, HostFirewallPort

IGNORED = "ignoree"


@dataclass(frozen=True)
class OpenPortRequest:
    port: int
    sources: tuple[str, ...]
    label: str
    """Qui demande (« omega-serv:prod ») : nom des règles et commentaire ufw."""


@dataclass(frozen=True)
class OpenPortLine:
    target: str
    source: str
    state: str
    detail: str = ""


@dataclass
class OpenPortResult:
    lines: list[OpenPortLine] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return bool(self.lines) and all(line.state != FAILED for line in self.lines) \
            and any(line.state in (ADDED, ALREADY) for line in self.lines)


class OpenPortCommand:
    def __init__(self, rule_repository: Any, adapters: dict[str, Any], host_firewall: HostFirewallPort | None,
                 create: Callable[[Any, Any], Any] = CreateRuleCommand) -> None:
        self._repository = rule_repository
        self._adapters = adapters
        self._host = host_firewall
        self._create = create

    def execute(self, request: OpenPortRequest) -> OpenPortResult:
        result = OpenPortResult()
        host = self._host.active_name() if self._host is not None else ""
        name = f"{request.label} {request.port}/tcp"
        for source in request.sources:
            ipv6 = ipaddress.ip_network(source, strict=False).version == 6
            for backend, adapter in self._adapters.items():
                if ipv6 and backend == "iptables":
                    result.lines.append(OpenPortLine(backend, source, IGNORED, "IPv6"))
                    continue
                outcome = self._create(self._repository, adapter).execute(CreateRuleRequest(
                    name=name, backend=backend, action="ACCEPT", chain="INPUT", protocol="tcp",
                    source_cidr=source, dst_port=request.port, description=name))
                if outcome.duplicate_of is not None:
                    result.lines.append(OpenPortLine(backend, source, ALREADY, f"#{outcome.duplicate_of}"))
                elif outcome.success and outcome.applied:
                    result.lines.append(OpenPortLine(backend, source, ADDED, f"#{outcome.rule_id}"))
                else:
                    result.lines.append(OpenPortLine(backend, source, FAILED, outcome.message))
            if host and self._host is not None:
                state, detail = self._host.allow(request.port, source, name)
                result.lines.append(OpenPortLine(host, source, state, detail))
        return result


@dataclass(frozen=True)
class ClosePortRequest:
    port: int
    sources: tuple[str, ...]
    label: str


@dataclass
class ClosePortResult:
    lines: list[OpenPortLine] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(line.state != FAILED for line in self.lines)


class ClosePortCommand:
    """Inverse exact de OpenPortCommand (`omega-fire.sh port fermer`, demande omega-stress du 2026-11-21) : retire
    les règles qu'elle a posées — même nom « <outil> <port>/tcp », même réseau, même port — du noyau puis de la
    base (DeleteRuleCommand, comme le menu 3.2), puis l'autorisation ufw / firewalld. Ne touche à aucune autre
    règle : une règle créée à la main pour ce port reste en place."""

    def __init__(self, rule_repository: Any, adapters: dict[str, Any], host_firewall: HostFirewallPort | None,
                 delete: Callable[[Any, Any], Any] | None = None) -> None:
        from omega_fire.application.commands.delete_rule import DeleteRuleCommand

        self._repository = rule_repository
        self._adapters = adapters
        self._host = host_firewall
        self._delete = delete or DeleteRuleCommand

    def execute(self, request: ClosePortRequest) -> ClosePortResult:
        from omega_fire.application.commands.delete_rule import DeleteRuleRequest
        from omega_fire.ports.host_firewall import ABSENT, REMOVED

        result = ClosePortResult()
        host = self._host.active_name() if self._host is not None else ""
        name = f"{request.label} {request.port}/tcp"
        for source in request.sources:
            wanted = str(ipaddress.ip_network(source, strict=False))
            for backend, adapter in self._adapters.items():
                matches = [rule for rule in self._repository.find_all(backend)
                           if rule.comment == name and rule.port_start == request.port
                           and rule.source_cidr and _same_network(rule.source_cidr, wanted)]
                if not matches:
                    result.lines.append(OpenPortLine(backend, source, ABSENT))
                    continue
                for rule in matches:
                    outcome = self._delete(self._repository, adapter).execute(DeleteRuleRequest(rule.rule_id))
                    result.lines.append(OpenPortLine(backend, source, REMOVED if outcome.success else FAILED,
                                                     f"#{rule.rule_id}" if outcome.success else outcome.message))
            if host and self._host is not None:
                state, detail = self._host.remove(request.port, source)
                result.lines.append(OpenPortLine(host, source, state, detail))
        return result


def _same_network(raw: str, wanted: str) -> bool:
    try:
        return str(ipaddress.ip_network(raw, strict=False)) == wanted
    except ValueError:
        return False
