# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Log top IPs query.

This query provides read-only access to the top IPs from logs.
"""
from omega_fire.core.capability_registry import CapabilityRegistry


def get_top_ips_from_logs(registry: CapabilityRegistry) -> str:
    """5.2: Get top IPs from logs.
    
    Args:
        registry: The capability registry
    
    Returns:
        Formatted string with top IPs
    """
    lines = ["═══ TOP IPs (Logs) ═══", ""]
    lines.append("⚠️ Top IPs à implémenter via infrastructure adapter")
    lines.append("")
    lines.append("Implémentation prévue :")
    lines.append("  1. Lire les logs via infrastructure.logging")
    lines.append("  2. Analyser et compter les IPs")
    lines.append("  3. Retourner le top N")
    
    return "\n".join(lines)

# <-- INFO DEV ---------------------------------------------------------
# Rôle : Query read-only pour le top IPs des logs
#---------------------------------------------------------------------->
