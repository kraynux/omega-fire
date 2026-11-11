# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Adresses jamais bannies par un transfert en masse (correctif 2026-11-10).

Memes reseaux par defaut que omega-serv (`never_auto_block`) et omega-waf : hote local, Tailscale,
reseaux locaux. Un transfert jail -> pare-feu est semi-automatique (des centaines d'IP d'un coup) :
avant, une adresse du reseau local ou de Tailscale bannie par un jail devenait bannie definitivement
au niveau du pare-feu, sans liste protegee. Un ban MANUEL d'une seule adresse reste possible (choix
explicite de l'administrateur)."""
from __future__ import annotations

import ipaddress

PROTECTED_NETWORKS: tuple[str, ...] = (
    "127.0.0.0/8", "::1/128",                      # hote local
    "100.64.0.0/10", "fd7a:115c:a1e0::/48",        # Tailscale (CGNAT, ULA Tailscale)
    "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "169.254.0.0/16",  # reseaux locaux IPv4
    "fc00::/7", "fe80::/10",                       # reseaux locaux IPv6
)

_NETWORKS = tuple(ipaddress.ip_network(n) for n in PROTECTED_NETWORKS)


def is_protected(address: str) -> bool:
    """Vrai si l'adresse (ou le reseau) appartient a un reseau protege. Forme IPv4-mappee-IPv6 comparee
    comme l'IPv4 qu'elle represente. Une valeur illisible n'est jamais protegee (elle sera refusee plus
    loin par la validation habituelle)."""
    try:
        network = ipaddress.ip_network(address.strip(), strict=False)
    except ValueError:
        return False
    addr = network.network_address
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is not None:
        addr = addr.ipv4_mapped
    return any(addr.version == n.version and addr in n for n in _NETWORKS)


def split_protected(addresses: list[str]) -> tuple[list[str], list[str]]:
    """(adresses a traiter, adresses protegees ecartees), ordre conserve."""
    kept: list[str] = []
    protected: list[str] = []
    for address in addresses:
        (protected if is_protected(address) else kept).append(address)
    return kept, protected
