# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""List banned IPs query.

This query provides read-only access to the list of banned IPs.
It retrieves the current state of all banned IPs across all backends.
"""
from omega_fire.core.capability_registry import CapabilityRegistry
from omega_fire.domain.ip_blacklist.models import BanEntry, BanStatus


def list_all_banned_ips(registry: CapabilityRegistry) -> str:
    """2.5: List all banned IPs across all backends.
    
    Args:
        registry: The capability registry to check backend availability
    
    Returns:
        Formatted string with all banned IPs
    """
    # Check which backends are available
    available_backends = []
    if registry.is_available("nftables"):
        available_backends.append("nftables")
    if registry.is_available("iptables"):
        available_backends.append("iptables")
    if registry.is_available("fail2ban_client"):
        available_backends.append("fail2ban")
    
    if not available_backends:
        return "⚠️ Aucun backend disponible. Impossible de lister les IPs bannies."
    
    # In a real implementation, this would call infrastructure adapters
    # For now, return a placeholder message
    lines = ["═══ IPs BANNIES ═══", ""]
    lines.append(f"Backends disponibles : {', '.join(available_backends)}")
    lines.append("")
    lines.append("⚠️ Liste des IPs bannies à implémenter via infrastructure adapters")
    lines.append("")
    lines.append("Implémentation prévue :")
    lines.append("  1. Appeler infrastructure.backends.nftables.adapter.list_bans()")
    lines.append("  2. Appeler infrastructure.backends.iptables.adapter.list_bans()")
    lines.append("  3. Appeler infrastructure.backends.fail2ban.adapter.list_bans()")
    lines.append("  4. Fusionner les résultats")
    lines.append("  5. Formater pour l'affichage")
    
    return "\n".join(lines)


def list_banned_ips_by_backend(registry: CapabilityRegistry, backend: str) -> str:
    """List banned IPs for a specific backend.
    
    Args:
        registry: The capability registry to check backend availability
        backend: Backend name ('nftables', 'iptables', or 'fail2ban')
    
    Returns:
        Formatted string with banned IPs for the specified backend
    """
    if not registry.is_available(backend):
        return f"⚠️ Backend '{backend}' non disponible."
    
    lines = [f"═══ IPs BANNIES ({backend.upper()}) ═══", ""]
    lines.append(f"⚠️ Liste des IPs bannies pour {backend} à implémenter")
    lines.append("")
    lines.append(f"Implémentation prévue :")
    lines.append(f"  Appeler infrastructure.backends.{backend}.adapter.list_bans()")
    
    return "\n".join(lines)


def count_banned_ips(registry: CapabilityRegistry) -> dict[str, int]:
    """Count banned IPs per backend.
    
    Args:
        registry: The capability registry to check backend availability
    
    Returns:
        Dictionary with counts per backend
    """
    counts = {
        "nftables": 0,
        "iptables": 0,
        "fail2ban": 0,
        "total": 0,
    }
    
    # In a real implementation, this would call infrastructure adapters
    # For now, return zeros
    
    return counts

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Fournit des queries read-only pour lister les IPs bannies
# - Utilisé par l'interface pour afficher la liste des IPs (Section 2.5)
# - Ne modifie pas le registre, seulement lecture
#
# Pourquoi dans application/queries/ (charte) :
# - C'est une query (lecture seule), pas une command (modification)
# - Dépend de core/capability_registry.py pour vérifier la disponibilité des backends
# - Retourne des strings formatées pour l'interface
#
# Ce qu'il ne contient PAS :
# ❌ Pas de modification du registre
# ❌ Pas d'appels système directs (délégué à infrastructure)
# ❌ Pas de logique métier (domain/)
# ❌ Pas de rendu (interfaces/)
#
# Points clés :
# - list_all_banned_ips() : affiche toutes les IPs bannies (tous backends)
# - list_banned_ips_by_backend() : affiche les IPs pour un backend spécifique
# - count_banned_ips() : retourne les compteurs par backend
# - Vérifie la disponibilité des backends via CapabilityRegistry
#
# Comment il sera utilisé (aperçu) :
# - interfaces/cli/handlers/blacklist_handlers.py wrappera ces queries
# - Menu 2.5 appellera list_all_banned_ips()
# - Les tests mockeront les adapters infrastructure
#---------------------------------------------------------------------->
