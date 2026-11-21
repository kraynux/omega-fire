# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""`omega-fire.sh synchro jeton|fiche [--format json]` (contrats d'interconnexion, 2026-11-10) : aucune
interface, sortie JSON non traduite. Lance sans sudo (omega-fire.sh n'eleve pas les privileges pour
`synchro`) : le jeton n'est jamais ecrit en root, la fiche est alors partielle."""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

USAGE = "usage: omega-fire.sh synchro {jeton,fiche,bans} [--format json]"


def _project_root() -> Path:
    from omega_fire.infrastructure.config.paths import VAR_DIR

    return VAR_DIR.parent


def _probes(as_root: bool):  # -> FireProbes
    from omega_fire.application.queries.synchro_contracts import BinaryProbe, FireProbes
    from omega_fire.infrastructure.probe.command_probe import CommandProbe
    from omega_fire.infrastructure.probe.service_probe import ServiceProbe

    command = CommandProbe()

    def binary(name: str, test: list[str]) -> BinaryProbe:
        result = command.probe_command(binary_name=name, test_command=test)
        return BinaryProbe(bool(result.get("present")), bool(result.get("functional")))

    # Sans root, `nft list tables` et `fail2ban-client ping` echouent toujours : seule la presence compte.
    nft = binary("nft", ["nft", "list", "tables"] if as_root else ["nft", "--version"])
    iptables = binary(
        "iptables", ["iptables", "-S"] if as_root else ["iptables", "--version"]
    )
    if not as_root:
        nft = BinaryProbe(nft.present, False)
        iptables = BinaryProbe(iptables.present, False)
    fail2ban = binary("fail2ban-client", ["fail2ban-client", "--version"])
    service = ServiceProbe().probe_service("fail2ban")
    state = str(service.get("state") or "")
    if service.get("active"):
        state = "active"
    return FireProbes(
        nft=nft,
        iptables=iptables,
        fail2ban_client=fail2ban,
        fail2ban_service_state=state,
        jail_d_present=Path("/etc/fail2ban/jail.d").is_dir(),
        as_root=as_root,
    )


def run_synchro(argv: list[str]) -> int:
    from omega_lib.infrastructure.synchro.files import dumps
    from omega_lib.infrastructure.synchro.install_token import (
        read_install_token,
        refresh_install_token,
    )
    from omega_lib.synchro.codec import sheet_to_dict, token_to_dict

    from omega_fire.application.queries.synchro_contracts import (
        FIRE_CONTRACTS,
        FIRE_OFFERS,
        FIRE_TOOL,
        FIRE_WANTS,
        build_fire_sheet,
    )
    from omega_fire.core.constants import OMEGA_FIRE_VERSION

    args = list(argv)
    if args[-2:] == ["--format", "json"]:
        args = args[:-2]
    root = _project_root()
    if args == ["jeton"]:
        refresh = refresh_install_token(
            root,
            FIRE_TOOL,
            OMEGA_FIRE_VERSION,
            contracts=FIRE_CONTRACTS,
            offers=FIRE_OFFERS,
            wants=FIRE_WANTS,
        )
        if refresh.token is None:
            print(
                f"omega-fire: installation token not written ({refresh.path}): {refresh.reason}",
                file=sys.stderr,
            )
            return 1
        print(dumps(token_to_dict(refresh.token)), end="")
        return 0
    if args == ["fiche"]:
        token = read_install_token(root)
        installation_id = (
            token.value.installation_id if token.ok and token.value is not None else ""
        )
        sheet = build_fire_sheet(
            _probes(os.geteuid() == 0),
            OMEGA_FIRE_VERSION,
            installation_id,
            datetime.now(timezone.utc),
        )
        print(dumps(sheet_to_dict(sheet)), end="")
        return 0
    if args == ["bans"]:
        return _sync_bans()
    print(USAGE, file=sys.stderr)
    return 2


def _sync_bans() -> int:
    """Etat initial du journal des bans (plan omega-connect, phase 3) : bans reellement en place dans le
    pare-feu, ecarts publies dans la zone omega-synchro. Root obligatoire (omega-fire.sh demande sudo)."""
    import json

    from omega_fire.infrastructure.backends.ip6tables.adapter import Ip6tablesAdapter
    from omega_fire.infrastructure.backends.iptables.adapter import IptablesAdapter
    from omega_fire.infrastructure.backends.nftables.adapter import NftablesAdapter
    from omega_fire.infrastructure.synchro.ban_journal import resync_ban_state

    if os.geteuid() != 0:
        print("omega-fire: synchro bans requires root", file=sys.stderr)
        return 1
    outcome = resync_ban_state([NftablesAdapter(), IptablesAdapter(), Ip6tablesAdapter()])
    print(json.dumps({"status": outcome.status.value, "events": outcome.events, "active": outcome.active,
                      "detail": outcome.detail}))
    return 0 if outcome.ok else 1
