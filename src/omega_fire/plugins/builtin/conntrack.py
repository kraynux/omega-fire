# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Builtin plugin for conntrack monitoring."""

PLUGIN_NAME = "conntrack"
PLUGIN_VERSION = "1.0.0"
PLUGIN_AUTHOR = "Omega-Fire Team"
PLUGIN_DESCRIPTION = "Monitoring des connexions via conntrack"
PLUGIN_CAPABILITIES = ["conntrack_monitoring", "conntrack_stats"]
PLUGIN_DEPENDENCIES = []
PLUGIN_HOOKS = ["on_connection_established", "on_connection_closed"]


def activate() -> None:
    pass


def deactivate() -> None:
    pass


def on_connection_established(**kwargs) -> None:
    pass


def on_connection_closed(**kwargs) -> None:
    pass

# <-- INFO DEV ---------------------------------------------------------
# Rôle : Plugin builtin pour le monitoring conntrack.
# Même structure que nftables.py, avec capacités spécifiques à conntrack.
#---------------------------------------------------------------------->    
