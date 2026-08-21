# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Network interface probe.

Detects network interfaces present on the system by reading
/sys/class/net/, a standard Linux virtual filesystem entry.
No subprocess call is needed: this is a plain directory listing.
Same approach for the default gateway, read from /proc/net/route.

This module performs real filesystem I/O and is therefore in
infrastructure/.
"""
import socket
import struct
from pathlib import Path

# Interfaces techniques rarement pertinentes pour une règle firewall,
# exclues par défaut de la liste proposée à l'utilisateur.
_DEFAULT_EXCLUDED = frozenset({"lo"})

_SYS_CLASS_NET = Path("/sys/class/net")


def list_network_interfaces(exclude_loopback: bool = True) -> list[str]:
    """List network interfaces present on the system.

    Reads /sys/class/net/, which contains one directory entry per
    network interface known to the kernel, whether up or down.

    Args:
        exclude_loopback: If True (default), excludes 'lo' from the result.

    Returns:
        Sorted list of interface names. Empty list if the system does
        not expose /sys/class/net/ (non-Linux) or if it cannot be read
        (permissions, unusual environment) — callers should treat an
        empty result as "detection unavailable", not as "no interfaces
        exist", and fall back to free-text entry.
    """
    try:
        if not _SYS_CLASS_NET.is_dir():
            return []

        names = [entry.name for entry in _SYS_CLASS_NET.iterdir() if entry.is_dir() or entry.is_symlink()]

        if exclude_loopback:
            names = [n for n in names if n not in _DEFAULT_EXCLUDED]

        return sorted(names)

    except Exception:
        # Environnement inhabituel ou permissions insuffisantes :
        # on ne bloque jamais l'appelant, on retourne une liste vide
        # pour signaler "détection indisponible".
        return []


_PROC_NET_ROUTE = Path("/proc/net/route")


def get_default_gateway() -> str:
    """Detect the default gateway IP by reading /proc/net/route.

    Kernel-exposed routing table (Linux only) — the default route has
    Destination "00000000". Gateway is a 32-bit hex field in host byte
    order little-endian, decoded the same way as `ip route` internally
    does, without shelling out to it.

    Returns:
        Gateway IP as a dotted string, or "" if unavailable (missing
        file, no default route, non-Linux) — callers should treat an
        empty result as "detection unavailable", not as "no gateway".
    """
    try:
        if not _PROC_NET_ROUTE.is_file():
            return ""

        with _PROC_NET_ROUTE.open("r", encoding="utf-8") as f:
            next(f)  # ligne d'en-tête (noms de colonnes)
            for line in f:
                fields = line.split()
                if len(fields) >= 3 and fields[1] == "00000000":
                    gateway_hex = fields[2]
                    return socket.inet_ntoa(struct.pack("<L", int(gateway_hex, 16)))

        return ""

    except Exception:
        return ""
