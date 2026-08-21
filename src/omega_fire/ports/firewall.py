# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Contrat pour les backends firewall (nftables, iptables)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Protocol

from omega_fire.shared.networking import IPAddress


@dataclass(frozen=True, slots=True)
class FirewallStats:
    """Statistiques d'un backend firewall.

    Attributs:
        total_rules: nombre total de règles.
        total_packets: nombre total de paquets traités.
        total_bytes: nombre total d'octets traités.
        dropped_packets: nombre de paquets dropés.
        accepted_packets: nombre de paquets acceptés.
    """
    total_rules: int
    total_packets: int
    total_bytes: int
    dropped_packets: int
    accepted_packets: int


class FirewallPort(Protocol):
    """Contrat pour les backends firewall (nftables, iptables).

    Définit les opérations attendues pour bannir/débannir des IPs,
    consulter les statistiques, et appliquer une politique prédéfinie.

    Ne couvre PAS la gestion individuelle des règles (list/add/delete) —
    ce sous-ensemble a été retiré du contrat : aucun consommateur réel ne
    l'a jamais utilisé (ni les adaptateurs, ni application/), le vrai
    système de gestion de règles s'est construit indépendamment autour de
    domain.rules.models.FirewallRule (persistance SQLite, presets,
    backup/restore, monitoring, rapports — 20+ fichiers), que ce port ne
    peut pas réutiliser sans violer sa propre règle de charte ("aucune
    dépendance vers domain/"). Décision actée explicitement, pas un oubli.
    """

    @abstractmethod
    def ban_ip(self, ip: IPAddress, *, reason: str = "") -> None:
        """Bannit une adresse IP (ajoute une règle DROP).

        Args:
            ip: adresse IP à bannir.
            reason: raison du ban (optionnel, pour traçabilité).

        Raises:
            IPAlreadyBannedError: si l'IP est déjà bannie.
        """
        ...

    @abstractmethod
    def unban_ip(self, ip: IPAddress) -> None:
        """Débannit une adresse IP (supprime la règle DROP).

        Args:
            ip: adresse IP à débannir.

        Raises:
            IPNotFoundError: si l'IP n'est pas bannie.
        """
        ...

    @abstractmethod
    def flush(self) -> int:
        """Vide toutes les règles du backend.

        Returns:
            Nombre de règles supprimées.
        """
        ...

    @abstractmethod
    def get_stats(self) -> FirewallStats:
        """Récupère les statistiques du backend.

        Returns:
            FirewallStats avec compteurs globaux.
        """
        ...

    @abstractmethod
    def apply_policy(self, policy_name: str) -> int:
        """Applique une politique prédéfinie (strict, local, monitoring, etc.).

        Args:
            policy_name: nom de la politique.

        Returns:
            Nombre de règles appliquées.

        Raises:
            PolicyNotFoundError: si la politique n'existe pas.
        """
        ...

    @abstractmethod
    def is_ip_banned(self, ip: IPAddress) -> bool:
        """Vérifie si une IP est bannie.

        Args:
            ip: adresse IP à vérifier.

        Returns:
            True si l'IP est bannie.
        """
        ...

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit le contrat (Protocol) pour les backends firewall (nftables, iptables).
# - Fournit FirewallStats (dataclass frozen).
# - Spécifie les opérations : ban_ip(), unban_ip(), flush(), get_stats(),
#   apply_policy(), is_ip_banned().
#
# Pourquoi dans ports/ (charte) :
# - C'est un contrat attendu par le cœur applicatif (application/commands/)
# - Pas d'implémentation concrète (c'est le rôle de infrastructure/backends/nftables/
#   et infrastructure/backends/iptables/)
# - Aucune dépendance vers domain/, application/, infrastructure/, interfaces/
#
# Ce qu'il ne contient PAS :
# ❌ Pas d'implémentation concrète (appels nft, iptables)
# ❌ Pas d'import depuis domain/
# ❌ Pas d'import depuis application/
# ❌ Pas d'import depuis infrastructure/
# ❌ Pas d'import depuis interfaces/
# ❌ Pas de logique de parsing de sortie nft/iptables
# ❌ Pas de gestion individuelle des règles (list/add/delete) — retiré du
#   contrat, voir docstring de FirewallPort. Cette gestion vit dans
#   domain/rules/models.py::FirewallRule + application/commands/, jamais
#   passée par ce port (aucun consommateur réel ne l'a jamais fait).
#
# Points clés :
# - FirewallStats : dataclass frozen avec total_rules, total_packets, total_bytes,
#   dropped_packets, accepted_packets
# - FirewallPort : Protocol définissant les opérations de ban/unban, statistiques,
#   application de politique — PAS la gestion de règles individuelles
# - IPAddress importé depuis shared/networking.py
# - Toutes les méthodes sont abstraites (via Protocol)
# - Implémenté par NftablesAdapter/IptablesAdapter (infrastructure/backends/{nftables,iptables}/adapter.py) :
#   ban_ip/unban_ip renommées ban_single_ip/unban_single_ip côté adaptateurs
#   (collision de nom avec les méthodes batch préexistantes ban_ip()/unban_ip(),
#   toujours utilisées par BanIpCommand/UnbanIpCommand — voir adapter.py)
#
# Comment il sera utilisé (aperçu) :
# - application/commands/ban_ip.py appellera firewall_port.ban_ip() (à câbler,
#   pas encore fait — les adaptateurs exposent déjà ban_single_ip/unban_single_ip)
# - infrastructure/backends/nftables/adapter.py implémente FirewallPort
# - infrastructure/backends/iptables/adapter.py implémente FirewallPort
#---------------------------------------------------------------------->
