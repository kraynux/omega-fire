# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Networking utilities.

Value objects for IP addresses and CIDR notation.
These are generic, non-business utilities used across multiple domains.
"""
import ipaddress
from dataclasses import dataclass


@dataclass(frozen=True)
class IPAddress:
    """Validated IP address (IPv4 or IPv6).
    
    This is a value object that validates the IP format on construction.
    It does not contain any business logic — just format validation.
    """
    value: str
    
    def __post_init__(self):
        """Validate the IP address format."""
        try:
            ipaddress.ip_address(self.value)
        except ValueError as e:
            raise ValueError(f"Invalid IP address: {self.value}") from e
    
    def __str__(self) -> str:
        return self.value
    
    @property
    def version(self) -> int:
        """Return IP version (4 or 6)."""
        return ipaddress.ip_address(self.value).version


@dataclass(frozen=True)
class CIDR:
    """Validated CIDR notation (e.g., '192.168.1.0/24').
    
    This is a value object that validates the CIDR format on construction.
    It does not contain any business logic — just format validation.
    """
    value: str
    
    def __post_init__(self):
        """Validate the CIDR notation format."""
        try:
            ipaddress.ip_network(self.value, strict=False)
        except ValueError as e:
            raise ValueError(f"Invalid CIDR notation: {self.value}") from e
    
    def __str__(self) -> str:
        return self.value
    
    @property
    def version(self) -> int:
        """Return IP version (4 or 6)."""
        return ipaddress.ip_network(self.value, strict=False).version
    
    @property
    def network_address(self) -> str:
        """Return the network address."""
        return str(ipaddress.ip_network(self.value, strict=False).network_address)
    
    @property
    def broadcast_address(self) -> str:
        """Return the broadcast address."""
        return str(ipaddress.ip_network(self.value, strict=False).broadcast_address)

#--- INFO DEV ----------------------------------------------------------
# Rôle :
# - Fournir des value objects pour la validation d'adresses IP et de notations CIDR. Ce sont des utilitaires transverses non métier (wrapper autour de ipaddress de la stdlib).
# Pourquoi dans shared/ (charte projet) :
# - C'est un utilitaire transverse non métier — utilisé par plusieurs sous-domaines
# - Ne contient pas de logique firewall spécifique
# - Wrapper autour de ipaddress de la stdlib Python
# - Conforme à la règle 8 : "shared/ ne doit contenir que des utilitaires réellement transverses et non métier"
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier (pas de règles de blacklist, pas de validation de politiques)
# ❌ Pas d'import depuis domain/, application/, infrastructure/ ou interfaces/
# ❌ Pas de dépendance externe (juste ipaddress de la stdlib)
# Points clés :
# - IPAddress : value object immutable (frozen=True) qui valide le format IPv4/IPv6
# - CIDR : value object immutable qui valide la notation CIDR
# - Validation au __post_init__ : lève ValueError si le format est invalide
# - Propriétés utilitaires : version, network_address, broadcast_address pour CIDR
# - Aucune logique métier : juste de la validation de format générique
# Comment il sera utilisé :
# - domain/ip_blacklist/service.py l'importe pour valider les IPs avant de les bannir
# - domain/rules/service.py l'utilisera pour valider les CIDR dans les règles firewall
# - domain/fail2ban/service.py l'utilisera pour valider les IPs dans les jails
#---------------------------------------------------------------------->
