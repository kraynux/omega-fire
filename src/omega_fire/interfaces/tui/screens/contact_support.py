# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Aide -> Contact et support : ecrans partages d'omega-lib (D-016, 2026-11-09), repris d'omega-serv /
omega-log. omega-fire n'a pas de service qui enverrait chaque jour : declaration « une seule fois ».
Le navigateur s'ouvre au nom de SUDO_USER (module d'omega-fire 6.5, repris dans omega-lib)."""
from __future__ import annotations

from typing import Any

from omega_lib.interfaces.tui.contact_support import ContactSupportKit
from omega_lib.ports.declaration import ContactSupportServices
from textual.screen import Screen

from omega_fire.interfaces.tui.screens._base import OmegaScreen
from omega_fire.shared.i18n import STATE, _


def contact_support_screen(services: ContactSupportServices) -> Screen[Any]:
    kit = ContactSupportKit(services=services, translate=_, language_code=lambda: STATE.language.code,
                            base_screen=OmegaScreen)
    return kit.screen()
