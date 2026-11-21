# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""`omega-fire.sh port ouvrir --port N --sources CIDR[,CIDR...] --pour OUTIL[:INSTANCE] [--format json]` : ouvre
N/tcp depuis ces réseaux (application/commands/open_port.py), sans interface. Appelé avec sudo par un outil relié
par omega-connect (omega-serv, administration web). Root obligatoire (omega-fire.sh élève les privilèges).

Sortie JSON non traduite : {"ok": bool, "port": N, "lignes": [{"cible", "source", "etat", "detail"}]} ; etat :
ajoutee, deja, ignoree, echec. Codes : 0 (port ouvert), 1 (échec), 2 (usage). Une ligne au journal d'audit."""

from __future__ import annotations

import ipaddress
import json
import os
import re
import sys

USAGE = "usage: omega-fire.sh port ouvrir --port N --sources CIDR[,CIDR...] --pour OUTIL[:INSTANCE] [--format json]"
_LABEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9:._-]{0,63}$")
MAX_SOURCES = 16


def parse(argv: list[str]) -> tuple[int, tuple[str, ...], str] | None:
    args = list(argv)
    if args[-2:] == ["--format", "json"]:
        args = args[:-2]
    if len(args) != 7 or args[0] != "ouvrir" or args[1::2] != ["--port", "--sources", "--pour"]:
        return None
    port_text, sources_text, label = args[2], args[4], args[6]
    if not port_text.isdigit() or not 1 <= int(port_text) <= 65535 or not _LABEL.match(label):
        return None
    sources = []
    for raw in sources_text.split(","):
        try:
            network = ipaddress.ip_network(raw.strip(), strict=False)
        except ValueError:
            return None
        if network.is_loopback:
            continue  # la boucle locale n'a jamais besoin d'ouverture
        if str(network) not in sources:
            sources.append(str(network))
    if not sources or len(sources) > MAX_SOURCES:
        return None
    return int(port_text), tuple(sources), label


def run_port(argv: list[str]) -> int:
    parsed = parse(argv)
    if parsed is None:
        print(USAGE, file=sys.stderr)
        return 2
    if os.geteuid() != 0:
        print("error: root required (use omega-fire.sh, which asks for sudo)", file=sys.stderr)
        return 1
    port, sources, label = parsed

    from omega_fire.app.dependency_container import DependencyContainer
    from omega_fire.application.commands.open_port import (
        OpenPortCommand,
        OpenPortRequest,
    )
    from omega_fire.infrastructure.backends.host_firewall.adapter import (
        SystemHostFirewall,
    )

    container = DependencyContainer()
    registry = container.capability_registry
    scanner = container.scanner
    try:  # meme balayage que le lancement de l'interface : sans lui, aucun backend n'est connu
        if hasattr(scanner, "scan_all"):
            registry.update_from_scan(scanner.scan_all())
        elif hasattr(scanner, "scan"):
            scanner.scan()
    except Exception as error:  # noqa: BLE001 - backend absent : rendu dans les lignes (aucun adaptateur)
        print(f"warning: partial scan: {error}", file=sys.stderr)
    adapters: dict[str, object] = {}
    for backend in ("nftables", "iptables"):
        if registry.is_available(backend):
            try:
                adapters[backend] = container.get_firewall_port(backend)
            except Exception:  # noqa: BLE001
                adapters[backend] = None
    if not adapters:
        print(json.dumps({"ok": False, "port": port, "lignes": [], "erreur": "no firewall backend"}))
        return 1
    result = OpenPortCommand(container.rule_repository, adapters, SystemHostFirewall()).execute(
        OpenPortRequest(port, sources, label))
    lines = [{"cible": line.target, "source": line.source, "etat": line.state, "detail": line.detail}
             for line in result.lines]
    try:
        container.audit_logger.log_event(event_type="action_execution", actor=f"cli:{label}",
                                         action=f"port ouvrir {port}/tcp", result="success" if result.ok else "failure",
                                         details={"sources": list(sources), "lignes": lines})
    except Exception as error:  # noqa: BLE001 - l'audit ne bloque jamais l'ouverture
        print(f"warning: audit not written: {error}", file=sys.stderr)
    print(json.dumps({"ok": result.ok, "port": port, "lignes": lines}, ensure_ascii=False))
    return 0 if result.ok else 1
