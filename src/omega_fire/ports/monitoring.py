# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Contrat pour le monitoring (conntrack, compteurs, statistiques)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from omega_fire.shared.networking import IPAddress


@dataclass(frozen=True, slots=True)
class ConntrackEntry:
    """Entrée de suivi de connexion immuable.

    Attributs:
        source_ip: adresse IP source.
        source_port: port source.
        destination_ip: adresse IP destination.
        destination_port: port destination.
        protocol: protocole (tcp, udp).
        state: état de la connexion (ESTABLISHED, SYN_SENT, etc.).
        packets: nombre de paquets échangés.
        bytes: nombre d'octets échangés.
        timeout: timeout restant en secondes.
    """
    source_ip: IPAddress
    source_port: int
    destination_ip: IPAddress
    destination_port: int
    protocol: str
    state: str
    packets: int
    bytes: int
    timeout: int


@dataclass(frozen=True, slots=True)
class NetworkCounters:
    """Compteurs réseau globaux.

    Attributs:
        total_connections: nombre total de connexions actives.
        incoming_bytes: octets entrants.
        outgoing_bytes: octets sortants.
        dropped_packets: paquets dropés.
        accepted_packets: paquets acceptés.
    """
    total_connections: int
    incoming_bytes: int
    outgoing_bytes: int
    dropped_packets: int
    accepted_packets: int


@dataclass(frozen=True, slots=True)
class MonitoringSnapshot:
    """Instantané de monitoring.

    Attributs:
        timestamp: date et heure de l'instantané.
        counters: compteurs réseau.
        active_connections: nombre de connexions actives.
        bans_per_minute: nombre de bans par minute (par backend).
    """
    timestamp: datetime
    counters: NetworkCounters
    active_connections: int
    bans_per_minute: dict[str, int]


class MonitoringPort(Protocol):
    """Contrat pour le monitoring (conntrack, compteurs, statistiques).

    Définit les opérations attendues pour surveiller l'activité réseau,
    les connexions actives et les statistiques en temps réel.
    """

    @abstractmethod
    def get_conntrack(self) -> list[ConntrackEntry]:
        """Récupère la liste des connexions actives (conntrack).

        Returns:
            Liste de ConntrackEntry.
        """
        ...

    @abstractmethod
    def get_counters(self) -> NetworkCounters:
        """Récupère les compteurs réseau globaux.

        Returns:
            NetworkCounters avec totaux et distributions.
        """
        ...

    @abstractmethod
    def get_snapshot(self) -> MonitoringSnapshot:
        """Récupère un instantané complet de monitoring.

        Returns:
            MonitoringSnapshot avec compteurs, connexions, bans.
        """
        ...

    @abstractmethod
    def kill_connection(
        self,
        source_ip: IPAddress,
        source_port: int,
        destination_ip: IPAddress,
        destination_port: int,
    ) -> bool:
        """Coupe une connexion spécifique.

        Args:
            source_ip: adresse IP source.
            source_port: port source.
            destination_ip: adresse IP destination.
            destination_port: port destination.

        Returns:
            True si la connexion a été coupée, False sinon.
        """
        ...

    @abstractmethod
    def get_bans_per_minute(self, backend: str, minutes: int = 60) -> list[tuple[datetime, int]]:
        """Récupère le nombre de bans par minute pour un backend.

        Args:
            backend: nom du backend (nftables, iptables, fail2ban).
            minutes: nombre de minutes à remonter.

        Returns:
            Liste de tuples (timestamp, count) triés par timestamp.
        """
        ...

    @abstractmethod
    def get_daily_stats(self, days: int = 7) -> dict[str, dict[str, int]]:
        """Récupère les statistiques quotidiennes.

        Args:
            days: nombre de jours à remonter.

        Returns:
            Dictionnaire {date: {metric: value}} avec bans, packets, bytes.
        """
        ...

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit le contrat (Protocol) pour le monitoring (conntrack, compteurs).
# - Fournit ConntrackEntry, NetworkCounters, MonitoringSnapshot (dataclasses frozen).
# - Spécifie les opérations : get_conntrack(), get_counters(), get_snapshot(),
#   kill_connection(), get_bans_per_minute(), get_daily_stats().
#
# Pourquoi dans ports/ (charte) :
# - C'est un contrat attendu par le cœur applicatif (application/queries/)
# - Pas d'implémentation concrète (c'est le rôle de infrastructure/backends/conntrack/)
# - Aucune dépendance vers domain/, application/, infrastructure/, interfaces/
#
# Ce qu'il ne contient PAS :
# ❌ Pas d'implémentation concrète (appels conntrack -L)
# ❌ Pas d'import depuis domain/
# ❌ Pas d'import depuis application/
# ❌ Pas d'import depuis infrastructure/
# ❌ Pas d'import depuis interfaces/
# ❌ Pas de logique de parsing de sortie conntrack
#
# Points clés :
# - ConntrackEntry : dataclass frozen avec source_ip, source_port, destination_ip,
#   destination_port, protocol, state, packets, bytes, timeout
# - NetworkCounters : dataclass frozen avec total_connections, incoming_bytes,
#   outgoing_bytes, dropped_packets, accepted_packets
# - MonitoringSnapshot : dataclass frozen avec timestamp, counters, active_connections,
#   bans_per_minute
# - MonitoringPort : Protocol définissant toutes les opérations de monitoring
# - IPAddress importé depuis shared/networking.py
# - Toutes les méthodes sont abstraites (via Protocol)
#
# Comment il sera utilisé (aperçu) :
# - application/queries/conntrack_status.py appellera monitoring_port.get_conntrack()
# - application/queries/dashboard_summary.py appellera monitoring_port.get_snapshot()
# - infrastructure/backends/conntrack/adapter.py implémentera MonitoringPort
# - interfaces/cli/renderers/monitoring_live.py appellera monitoring_port.get_snapshot()
#---------------------------------------------------------------------->        
