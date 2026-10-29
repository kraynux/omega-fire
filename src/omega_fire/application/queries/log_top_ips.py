# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Log top IPs query.

This query provides read-only access to the top IPs from logs.
"""
from omega_fire.core.capability_registry import CapabilityRegistry
from omega_fire.shared.i18n import _


def get_top_ips_from_logs(registry: CapabilityRegistry) -> str:
    """5.2: Get top IPs from logs.
    
    Args:
        registry: The capability registry
    
    Returns:
        Formatted string with top IPs
    """
    lines = [_("═══ TOP IPs (Logs) ═══"), ""]
    lines.append(_("⚠️ Top IPs à implémenter via infrastructure adapter"))
    lines.append("")
    lines.append(_("Implémentation prévue :"))
    lines.append(_("  1. Lire les logs via infrastructure.logging"))
    lines.append(_("  2. Analyser et compter les IPs"))
    lines.append(_("  3. Retourner le top N"))
    
    return "\n".join(lines)

# <-- INFO DEV ---------------------------------------------------------
# Rôle : Query read-only pour le top IPs des logs
#---------------------------------------------------------------------->
