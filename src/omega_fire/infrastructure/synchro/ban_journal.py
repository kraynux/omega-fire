# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Journal des bans pour les autres outils omega (plan omega-connect, phase 3 ; decision 2026-11-21).

omega-fire ecrit les bans qu'il pose LUI-MEME dans le pare-feu (nftables, iptables, ip6tables), origine
`omega-fire:manual`. Les bans des jails fail2ban, meme pilotes par omega-fire, sont ecrits par l'action
fail2ban d'omega-jail (`fail2ban:<jail>`) : jamais deux fois.

Branche en un seul point : chaque adaptateur de pare-feu cree par le conteneur est enveloppe, si bien que
tous les chemins (Bannir, Debannir, transfert d'un jail, restauration, synchronisation entre backends)
sont couverts. Apres une operation de masse (vidage, profil, chargement d'un jeu de regles) ou un echec
partiel, l'etat est relu dans le pare-feu et les ecarts sont ecrits (resynchronisation).

Sans zone omega-synchro (omega-connect absent), sans root, ou en cas d'erreur : rien n'est ecrit et le
pare-feu n'est jamais affecte (aucune exception ne remonte)."""

from __future__ import annotations

import logging
import os
import re
from collections.abc import Callable, Iterable
from datetime import datetime, timedelta, timezone
from typing import Any

from omega_lib.infrastructure.synchro.ban_writer import (
    WriteOutcome,
    WriteStatus,
    new_ban_event,
    record_ban_events,
    replace_active_bans,
)
from omega_lib.infrastructure.synchro.files import zone_dir
from omega_lib.synchro.constants import ZONE_BANS_DIR
from omega_lib.synchro.models import BanAction

ORIGIN = "omega-fire:manual"
REASON_MAX = 200
_logger = logging.getLogger(__name__)

_RESYNC_AFTER = frozenset({
    "flush", "flush_all", "flush_chain", "flush_table", "delete_table", "load_ruleset", "apply_preset",
    "apply_policy",
})
"""Operations qui retirent ou remplacent des bans en masse : l'etat est relu ensuite."""


def _split(ip: Any) -> list[str]:
    if isinstance(ip, (list, tuple, set)):
        return [str(i).strip() for i in ip if str(i).strip()]
    return [part for part in re.split(r"[,\s]+", str(ip)) if part]


def _events(action: BanAction, ips: Iterable[str], *, reason: str = "",
            expires_at: datetime | None = None) -> list[Any]:
    events = []
    for ip in ips:
        try:
            events.append(new_ban_event(action, ip, ORIGIN, reason=reason[:REASON_MAX], expires_at=expires_at))
        except ValueError:
            continue  # pas une adresse (texte libre d'un vieux script) : rien a publier
    return events


def _is_root() -> bool:
    return os.geteuid() == 0


def _safe(write: Callable[[], WriteOutcome]) -> WriteOutcome:
    if not _is_root():
        return WriteOutcome(WriteStatus.NO_ZONE, "not root")
    try:
        outcome = write()
    except Exception as error:  # noqa: BLE001 - le journal ne doit jamais casser un ban
        _logger.debug("journal des bans non ecrit : %s", error)
        return WriteOutcome(WriteStatus.FAILED, str(error))
    if not outcome.ok:
        _logger.debug("journal des bans non ecrit : %s %s", outcome.status.value, outcome.detail)
    return outcome


def resync_ban_state(adapters: Iterable[Any]) -> WriteOutcome:
    """Etat initial / resynchronisation : bans reellement en place sur tous les backends disponibles.
    Un backend illisible annule tout (sinon ses bans passeraient pour leves)."""
    def write() -> WriteOutcome:
        if not (zone_dir() / ZONE_BANS_DIR).is_dir():
            return WriteOutcome(WriteStatus.NO_ZONE)  # rien a relire dans le pare-feu
        networks: set[str] = set()
        for adapter in adapters:
            inner = getattr(adapter, "inner", adapter)
            if not inner.is_available():
                continue
            networks.update(str(entry.ip) for entry in inner.list_bans())
        return replace_active_bans(ORIGIN, _events(BanAction.BAN, sorted(networks)))

    return _safe(write)


class BanJournalingFirewall:
    """Enveloppe d'un adaptateur de pare-feu : meme interface, plus l'ecriture du journal des bans."""

    def __init__(self, inner: Any, resync: Callable[[], WriteOutcome]) -> None:
        self.inner = inner
        self._resync = resync

    def __getattr__(self, name: str) -> Any:
        value = getattr(self.inner, name)
        if name in _RESYNC_AFTER and callable(value):
            def after(*args: Any, **kwargs: Any) -> Any:
                try:
                    return value(*args, **kwargs)
                finally:
                    self._resync()
            return after
        return value

    def ban_ip(self, ip: Any, *args: Any, **kwargs: Any) -> Any:
        ok = self.inner.ban_ip(ip, *args, **kwargs)
        if ok:
            reason = str(kwargs.get("comment") or "")
            _safe(lambda: record_ban_events(_events(BanAction.BAN, _split(ip), reason=reason)))
        else:
            self._resync()
        return ok

    def unban_ip(self, ip: Any, *args: Any, **kwargs: Any) -> Any:
        ok = self.inner.unban_ip(ip, *args, **kwargs)
        if ok:
            _safe(lambda: record_ban_events(_events(BanAction.UNBAN, _split(ip))))
        else:
            self._resync()
        return ok

    def ban_single_ip(self, ip: Any, *args: Any, **kwargs: Any) -> Any:
        result = self.inner.ban_single_ip(ip, *args, **kwargs)
        seconds = kwargs.get("timeout_seconds")
        expires = datetime.now(timezone.utc) + timedelta(seconds=int(seconds)) if seconds else None
        reason = str(kwargs.get("reason") or "")
        _safe(lambda: record_ban_events(_events(BanAction.BAN, [str(ip)], reason=reason, expires_at=expires)))
        return result

    def unban_single_ip(self, ip: Any, *args: Any, **kwargs: Any) -> Any:
        result = self.inner.unban_single_ip(ip, *args, **kwargs)
        _safe(lambda: record_ban_events(_events(BanAction.UNBAN, [str(ip)])))
        return result
