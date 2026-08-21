# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Kernel probe.
Tests the presence of kernel modules required for firewall backends.
Checks /proc/net/nf_tables for nftables support and /proc/net/ip_tables
for iptables support.
This module performs real system I/O (reading /proc filesystem) and is
therefore in infrastructure/.
"""
import os
from typing import Optional
from omega_fire.infrastructure.probe.exceptions import ProbeExecutionError


class KernelProbe:
    """Probes the presence of kernel modules for firewall backends.
    
    Checks /proc filesystem for netfilter module availability.
    """
    
    def __init__(self):
        """Initialize the kernel probe."""
        self._proc_net_path = "/proc/net"
    
    def check_nftables_support(self) -> dict:
        """Check if nftables kernel support is available.
        
        Returns:
            Dictionary with probe results:
            - available: bool
            - modules: list[str] (detected modules)
            - message: str
        """
        modules = []
        
        # Check /proc/net/nf_tables
        nf_tables_path = os.path.join(self._proc_net_path, "nf_tables")
        if os.path.exists(nf_tables_path):
            modules.append("nf_tables")
        
        # Check for specific nftables modules
        nft_modules = ["nf_tables", "nft_chain_nat", "nft_compat"]
        for module in nft_modules:
            module_path = f"/sys/module/{module}"
            if os.path.exists(module_path):
                if module not in modules:
                    modules.append(module)
        
        if modules:
            return {
                "available": True,
                "modules": modules,
                "message": f"nftables kernel support detected: {', '.join(modules)}",
            }
        else:
            return {
                "available": False,
                "modules": [],
                "message": "nftables kernel support not detected",
            }
    
    def check_iptables_support(self) -> dict:
        """Check if iptables kernel support is available.
        
        Returns:
            Dictionary with probe results:
            - available: bool
            - modules: list[str] (detected modules)
            - message: str
        """
        modules = []
        
        # Check /proc/net/ip_tables_names (iptables legacy)
        ip_tables_path = os.path.join(self._proc_net_path, "ip_tables_names")
        if os.path.exists(ip_tables_path):
            modules.append("ip_tables")
        
        # Check for iptables modules
        ipt_modules = ["ip_tables", "iptable_filter", "iptable_nat", "iptable_mangle"]
        for module in ipt_modules:
            module_path = f"/sys/module/{module}"
            if os.path.exists(module_path):
                if module not in modules:
                    modules.append(module)
        
        if modules:
            return {
                "available": True,
                "modules": modules,
                "message": f"iptables kernel support detected: {', '.join(modules)}",
            }
        else:
            return {
                "available": False,
                "modules": [],
                "message": "iptables kernel support not detected",
            }
    
    def check_netfilter_support(self) -> dict:
        """Check if netfilter kernel support is available (generic).
        
        Returns:
            Dictionary with probe results:
            - available: bool
            - modules: list[str] (detected modules)
            - message: str
        """
        modules = []
        
        # Check /proc/net/netfilter
        netfilter_path = os.path.join(self._proc_net_path, "netfilter")
        if os.path.exists(netfilter_path):
            modules.append("netfilter")
        
        # Check for core netfilter modules
        nf_modules = ["netfilter", "nf_conntrack", "nf_nat"]
        for module in nf_modules:
            module_path = f"/sys/module/{module}"
            if os.path.exists(module_path):
                if module not in modules:
                    modules.append(module)
        
        if modules:
            return {
                "available": True,
                "modules": modules,
                "message": f"netfilter kernel support detected: {', '.join(modules)}",
            }
        else:
            return {
                "available": False,
                "modules": [],
                "message": "netfilter kernel support not detected",
            }
    
    def probe_kernel(self, backend: str = "netfilter") -> dict:
        """Probe kernel support for a specific backend.
        
        Args:
            backend: Backend to probe ("nftables", "iptables", or "netfilter")
        
        Returns:
            Dictionary with probe results
        """
        if backend == "nftables":
            return self.check_nftables_support()
        elif backend == "iptables":
            return self.check_iptables_support()
        elif backend == "netfilter":
            return self.check_netfilter_support()
        else:
            return {
                "available": False,
                "modules": [],
                "message": f"Unknown backend: {backend}",
            }


def probe_kernel(backend: str = "netfilter") -> dict:
    """Convenience function to probe kernel support.
    
    Args:
        backend: Backend to probe ("nftables", "iptables", or "netfilter")
    
    Returns:
        Dictionary with probe results
    """
    probe = KernelProbe()
    return probe.probe_kernel(backend)


def is_nftables_supported() -> bool:
    """Check if nftables kernel support is available.
    
    Returns:
        True if nftables is supported
    """
    probe = KernelProbe()
    result = probe.check_nftables_support()
    return result["available"]


def is_iptables_supported() -> bool:
    """Check if iptables kernel support is available.
    
    Returns:
        True if iptables is supported
    """
    probe = KernelProbe()
    result = probe.check_iptables_support()
    return result["available"]


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Teste la présence des modules noyau requis pour les backends firewall
# - Vérifie /proc/net/nf_tables pour nftables
# - Vérifie /proc/net/ip_tables_names pour iptables
# - Vérifie /proc/net/netfilter pour le support générique netfilter
# - Retourne des résultats détaillés (disponible, modules détectés, message)
#
# Pourquoi dans infrastructure/ (charte) :
# - C'est une détection technique qui nécessite des I/O système réels
#   (lecture de /proc et /sys)
# - Le résultat est utilisé par capability_mapper pour créer des Capability
# - Aucun autre module ne doit recoder cette détection (clause omega-fire)
#
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier (pas de règles firewall/fail2ban)
# ❌ Pas de mapping vers Capability (c'est le rôle de capability_mapper)
# ❌ Pas de dépendance vers domain/ ou interfaces/
#
# Points clés :
# - KernelProbe : classe principale
# - check_nftables_support() : vérifie /proc/net/nf_tables et /sys/module/nf_tables
# - check_iptables_support() : vérifie /proc/net/ip_tables_names et /sys/module/ip_tables
# - check_netfilter_support() : vérifie /proc/net/netfilter et modules génériques
# - probe_kernel(backend) : méthode principale qui retourne un dict détaillé
#   - available : bool (support détecté)
#   - modules : list[str] (modules détectés)
#   - message : str (description du résultat)
# - Fonctions de convenance : probe_kernel(), is_nftables_supported(), is_iptables_supported()
#
# Comment il sera utilisé (aperçu) :
# - infrastructure/probe/scanner.py l'utilisera pour tester le support noyau
# - infrastructure/probe/capability_mapper.py transformera les résultats en Capability
# - Les tests mockeront os.path.exists pour simuler différents états
#---------------------------------------------------------------------->
