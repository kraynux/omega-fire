# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Builtin plugin for fail2ban backend."""

PLUGIN_NAME = "fail2ban"
PLUGIN_VERSION = "1.0.0"
PLUGIN_AUTHOR = "Omega-Fire Team"
PLUGIN_DESCRIPTION = "Backend fail2ban pour la gestion des jails"
PLUGIN_CAPABILITIES = ["fail2ban_backend", "fail2ban_jails", "fail2ban_bans"]
PLUGIN_DEPENDENCIES = []
PLUGIN_HOOKS = ["before_jail_ban", "after_jail_ban", "before_jail_unban", "after_jail_unban"]


def activate() -> None:
    pass


def deactivate() -> None:
    pass


def before_jail_ban(jail: str, ip: str, **kwargs) -> None:
    pass


def after_jail_ban(jail: str, ip: str, **kwargs) -> None:
    pass


def before_jail_unban(jail: str, ip: str, **kwargs) -> None:
    pass


def after_jail_unban(jail: str, ip: str, **kwargs) -> None:
    pass

# <-- INFO DEV ---------------------------------------------------------
# Rôle : Plugin builtin pour le backend fail2ban.
# Même structure que nftables.py, avec capacités spécifiques à fail2ban.
#---------------------------------------------------------------------->    
