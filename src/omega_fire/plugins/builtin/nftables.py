# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Builtin plugin for nftables backend.

Provides nftables-specific capabilities and hooks.
This is a minimal skeleton; actual implementation will be in infrastructure/.

Conforms to Omega-Fire architecture charter:
- Plugin provides metadata and hooks, not business logic
- No dependency on domain/, application/, or infrastructure/
- Actual nftables operations are delegated to infrastructure/backends/nftables/
"""

# ----------------------------------------------------------------------
# Plugin metadata
# ----------------------------------------------------------------------
PLUGIN_NAME = "nftables"
PLUGIN_VERSION = "1.0.0"
PLUGIN_AUTHOR = "Omega-Fire Team"
PLUGIN_DESCRIPTION = "Backend nftables pour la gestion du pare-feu"
PLUGIN_CAPABILITIES = ["nftables_backend", "nftables_rules", "nftables_counters"]
PLUGIN_DEPENDENCIES = []
PLUGIN_HOOKS = ["before_ban", "after_ban", "before_unban", "after_unban"]


# ----------------------------------------------------------------------
# Plugin lifecycle
# ----------------------------------------------------------------------
def activate() -> None:
    """Activate the nftables plugin."""
    pass  # Actual activation handled by infrastructure adapter


def deactivate() -> None:
    """Deactivate the nftables plugin."""
    pass  # Actual deactivation handled by infrastructure adapter


# ----------------------------------------------------------------------
# Hooks (stubs, actual implementation in infrastructure/)
# ----------------------------------------------------------------------
def before_ban(ip: str, **kwargs) -> None:
    """Hook called before banning an IP."""
    pass


def after_ban(ip: str, **kwargs) -> None:
    """Hook called after banning an IP."""
    pass


def before_unban(ip: str, **kwargs) -> None:
    """Hook called before unbanning an IP."""
    pass


def after_unban(ip: str, **kwargs) -> None:
    """Hook called after unbanning an IP."""
    pass

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Plugin builtin pour le backend nftables.
# - Fournit les métadonnées (nom, version, capacités, hooks).
# - Définit les fonctions de cycle de vie (activate, deactivate).
# - Fournit des stubs pour les hooks (before_ban, after_ban, etc.).
#
# Pourquoi dans plugins/builtin/ (charte) :
# - Plugin officiel fourni avec Omega-Fire.
# - Aucune logique métier (déléguée à infrastructure/backends/nftables/).
# - Aucune dépendance vers domain/, application/, infrastructure/.
# - Respecte le contrat plugin (PLUGIN_NAME, activate, deactivate).
#
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier (c'est le rôle de domain/).
# ❌ Pas d'implémentation nftables (c'est le rôle de infrastructure/).
# ❌ Pas d'appels système (c'est le rôle de infrastructure/).
# ❌ Pas de dépendance vers d'autres couches.
#
# Points clés :
# - PLUGIN_NAME : "nftables" (identifiant unique).
# - PLUGIN_CAPABILITIES : ["nftables_backend", "nftables_rules", "nftables_counters"].
# - PLUGIN_HOOKS : ["before_ban", "after_ban", "before_unban", "after_unban"].
# - activate() / deactivate() : fonctions de cycle de vie (stubs ici).
# - Hooks : stubs vides, implémentation réelle dans infrastructure/.
#---------------------------------------------------------------------->    
