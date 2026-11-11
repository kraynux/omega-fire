# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Jeton d'installation et fiche d'omega-fire (contrats d'interconnexion, omega-lib D-017, etape 2 du
2026-11-10 ; spec ~/DEV/CONNECT/SPEC_ETAPE2_CONTRATS_OMEGA_LIB.md).

- Jeton : `var/omega-jeton.json`, ecrit par `omega-fire.sh synchro jeton` (install.sh), toujours sous le
  compte proprietaire du dossier : omega-fire tourne en root, le jeton n'est donc jamais rafraichi par
  l'interface elle-meme (omega-lib refuse d'ecrire en root).
- Fiche : `omega-fire.sh synchro fiche --format json`, lecture seule. Sans root, fail2ban, nftables et
  iptables ne sont pas tous verifiables : la fiche est alors marquee `partial`."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from omega_lib.synchro.models import CapabilityState, InstanceSheet
from omega_lib.synchro.policies import format_utc

FIRE_TOOL = "omega-fire"
FIRE_CONTRACTS: dict[str, tuple[int, ...]] = {"omega-fiche": (1,)}
FIRE_OFFERS = ("fail2ban", "nftables", "iptables", "log-library")
FIRE_WANTS = ("blocklist", "waf-logs", "riposte-decisions")


@dataclass(frozen=True)
class BinaryProbe:
    present: bool
    functional: bool


@dataclass(frozen=True)
class FireProbes:
    nft: BinaryProbe
    iptables: BinaryProbe
    fail2ban_client: BinaryProbe
    fail2ban_service_state: str
    """active, inactive, failed, not_found, no_manager, error..."""
    jail_d_present: bool
    as_root: bool


def _binary_state(probe: BinaryProbe, as_root: bool) -> CapabilityState:
    if not probe.present:
        return CapabilityState.ABSENT
    if probe.functional:
        return CapabilityState.ACTIVE
    return CapabilityState.DISABLED if as_root else CapabilityState.UNKNOWN


def _fail2ban_state(probes: FireProbes) -> CapabilityState:
    if not probes.fail2ban_client.present:
        return CapabilityState.ABSENT
    state = probes.fail2ban_service_state
    if state == "active":
        return CapabilityState.ACTIVE
    if state in ("inactive", "failed", "dead", "stopped"):
        return CapabilityState.DISABLED
    return CapabilityState.UNKNOWN


def build_fire_sheet(probes: FireProbes, version: str, installation_id: str, now: datetime) -> InstanceSheet:
    capabilities = {
        "fail2ban": _fail2ban_state(probes),
        "nftables": _binary_state(probes.nft, probes.as_root),
        "iptables": _binary_state(probes.iptables, probes.as_root),
        "log-library": CapabilityState.ACTIVE,
    }
    partial = not probes.as_root
    extra: dict[str, object] = {
        "backends": {name: capabilities[name].value for name in ("fail2ban", "nftables", "iptables")},
        "fail2ban_jail_d": "/etc/fail2ban/jail.d" if probes.jail_d_present else None,
    }
    return InstanceSheet(
        tool=FIRE_TOOL, version=version, installation_id=installation_id, instance=FIRE_TOOL,
        generated_at=format_utc(now), capabilities=capabilities, service=None, files={},
        partial=partial, extra=extra,
    )
