# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Builtin plugin for iptables backend."""
from omega_fire.shared.i18n import _

PLUGIN_NAME = "iptables"
PLUGIN_VERSION = "1.0.0"
PLUGIN_AUTHOR = _("Omega-Fire Team")
PLUGIN_DESCRIPTION = _("Backend iptables pour la gestion du pare-feu")
PLUGIN_CAPABILITIES = ["iptables_backend", "iptables_rules", "iptables_counters"]
PLUGIN_DEPENDENCIES = []
PLUGIN_HOOKS = ["before_ban", "after_ban", "before_unban", "after_unban"]


def activate() -> None:
    pass


def deactivate() -> None:
    pass


def before_ban(ip: str, **kwargs) -> None:
    pass


def after_ban(ip: str, **kwargs) -> None:
    pass


def before_unban(ip: str, **kwargs) -> None:
    pass


def after_unban(ip: str, **kwargs) -> None:
    pass

# <-- INFO DEV ---------------------------------------------------------
# Rôle : Plugin builtin pour le backend iptables.
# Même structure que nftables.py, avec capacités spécifiques à iptables.
#---------------------------------------------------------------------->    
