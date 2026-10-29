# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Libelles traduits de l'origine d'un jail (domain/fail2ban/definitions.py), communs a 4.1
(etat des jails) et 4.5 (suppression) — version 3.5, point 7."""
from __future__ import annotations

from omega_fire.domain.fail2ban.definitions import (
    ORIGIN_MAIN_CONFIG,
    ORIGIN_OMEGA_FIRE,
    ORIGIN_OMEGA_JAIL,
)
from omega_fire.shared.i18n import _


def origin_label(origin: str | None) -> str:
    labels = {
        ORIGIN_OMEGA_FIRE: _("Omega-Fire"),
        ORIGIN_OMEGA_JAIL: _("omega-jail"),
        ORIGIN_MAIN_CONFIG: _("jail.local / jail.conf"),
    }
    return labels.get(origin or "", _("autre"))
