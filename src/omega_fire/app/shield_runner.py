# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""`omega-fire.sh bouclier-wg ...` (3.7.0, omega-lib D-018) : bouclier du port WireGuard pour un outil relie par
omega-connect (omega-tail), sans interface. Root obligatoire (omega-fire.sh eleve les privileges).

    bouclier-wg etat [--format json]
    bouclier-wg poser --mode observation|actif --pour OUTIL [--port N] [--cartes a,b] [--format json]
    bouclier-wg mode observation|actif --pour OUTIL [--format json]
    bouclier-wg reprendre|reposer|retirer --pour OUTIL [--format json]

`--pour` : l'outil qui demande (journal d'audit ; pour `poser`, c'est aussi l'origine inscrite dans la table).
Sortie JSON non traduite : {"ok", "raison", "bouclier": {...}, "lignes": [{"commande", "code", "detail"}]}.
Codes : 0 (fait), 1 (echec), 2 (usage). Une ligne au journal d'audit pour chaque action (pas pour `etat`)."""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Any

from omega_lib.shield.models import ShieldMode
from omega_lib.shield.policies import DEVICE_PATTERN

USAGE = ("usage: omega-fire.sh bouclier-wg etat | poser --mode observation|actif --pour OUTIL [--port N] "
         "[--cartes a,b] | mode observation|actif --pour OUTIL | reprendre|reposer|retirer --pour OUTIL "
         "[--format json]")
_LABEL = re.compile(r"^[a-z0-9][a-z0-9._-]{0,31}$")
ACTIONS = ("etat", "poser", "mode", "reprendre", "reposer", "retirer")


def parse(argv: list[str]) -> dict[str, Any] | None:
    args = list(argv)
    if args[-2:] == ["--format", "json"]:
        args = args[:-2]
    if not args or args[0] not in ACTIONS:
        return None
    action, rest = args[0], args[1:]
    parsed: dict[str, Any] = {"action": action}
    if action == "mode":
        if not rest or rest[0] not in (ShieldMode.OBSERVE.value, ShieldMode.ACTIVE.value):
            return None
        parsed["mode"], rest = ShieldMode(rest[0]), rest[1:]
    if len(rest) % 2:
        return None
    options = dict(zip(rest[::2], rest[1::2], strict=True))
    allowed = {"etat": set(), "poser": {"--mode", "--pour", "--port", "--cartes"}}.get(action, {"--pour"})
    if set(options) - allowed:
        return None
    if action != "etat":
        label = options.get("--pour", "")
        if not _LABEL.match(label):
            return None
        parsed["pour"] = label
    if action == "poser":
        try:
            parsed["mode"] = ShieldMode(options.get("--mode", ""))
        except ValueError:
            return None
        if "--port" in options:
            text = options["--port"]
            if not text.isdigit() or not 1 <= int(text) <= 65535:
                return None
            parsed["port"] = int(text)
        if "--cartes" in options:
            devices = tuple(name for name in options["--cartes"].split(",") if name)
            if not devices or any(not DEVICE_PATTERN.match(name) for name in devices):
                return None
            parsed["cartes"] = devices
    return parsed


def view_dict(view: Any) -> dict[str, Any]:
    status, settings = view.status, view.settings
    counters = status.counters if status is not None else None
    spec = settings.spec if settings is not None else None
    mode = status.mode if status is not None and status.present else (spec.mode if spec else None)
    return {
        "enregistre": view.installed,
        "present": view.present,
        "perime": view.stale,
        "mode": mode.value if mode is not None else None,
        "pour": view.requested_by,
        "gestionnaire": view.manager,
        "port": spec.port if spec else view.port,
        "cartes": list(spec.devices if spec else view.devices),
        "egress": spec.egress if spec else view.egress,
        "pairs": status.peers if status is not None else 0,
        "compteurs": counters.__dict__ if counters is not None else {},
        "refuses": counters.refused if counters is not None else 0,
        "heure": status.at if status is not None else None,
    }


def run_shield(argv: list[str]) -> int:
    parsed = parse(argv)
    if parsed is None:
        print(USAGE, file=sys.stderr)
        return 2
    if os.geteuid() != 0:
        print("error: root required (use omega-fire.sh, which asks for sudo)", file=sys.stderr)
        return 1

    from omega_fire.application.commands.wg_shield import WgShieldService
    from omega_fire.infrastructure.backends.wg_shield.adapter import SystemWgShield

    service = WgShieldService(SystemWgShield())
    action = parsed["action"]
    if action == "etat":
        print(json.dumps({"ok": True, "raison": "etat", "bouclier": view_dict(service.view()), "lignes": []},
                         ensure_ascii=False))
        return 0
    if action == "poser":
        outcome = service.pose(parsed["mode"], parsed["pour"], port=parsed.get("port"),
                               devices=parsed.get("cartes"))
    elif action == "mode":
        outcome = service.set_mode(parsed["mode"])
    elif action == "reprendre":
        outcome = service.take_over()
    elif action == "reposer":
        outcome = service.repose()
    else:
        outcome = service.remove()
    lines = [{"commande": " ".join(line.command), "code": line.code, "detail": line.detail}
             for line in outcome.lines]
    try:
        from omega_fire.app.dependency_container import DependencyContainer

        DependencyContainer().audit_logger.log_event(
            event_type="action_execution", actor=f"cli:{parsed['pour']}",
            action=f"bouclier-wg {action}" + (f" {parsed['mode'].value}" if "mode" in parsed else ""),
            result="success" if outcome.ok else "failure", details={"raison": outcome.reason, "lignes": lines})
    except Exception as error:  # noqa: BLE001 - l'audit ne bloque jamais le bouclier
        print(f"warning: audit not written: {error}", file=sys.stderr)
    print(json.dumps({"ok": outcome.ok, "raison": outcome.reason, "bouclier": view_dict(outcome.view),
                      "lignes": lines}, ensure_ascii=False))
    return 0 if outcome.ok else 1
