# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Contrat pour l'interaction avec Fail2ban (jails, bans, service)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from omega_fire.shared.networking import IPAddress


@dataclass(frozen=True, slots=True)
class JailInfo:
    """Informations sur un jail Fail2ban.

    Attributs:
        name: nom du jail.
        active: True si le jail est actif.
        banned_count: nombre d'IPs actuellement bannies.
        banned_ips: liste des IPs bannies.
        filter: nom du filtre utilisé.
        log_path: chemin du fichier de log surveillé.
        max_retry: nombre maximum de tentatives avant ban.
        ban_time: durée du ban en secondes.
        find_time: fenêtre de détection en secondes.
    """
    name: str
    active: bool
    banned_count: int
    banned_ips: list[IPAddress]
    filter: str
    log_path: str
    max_retry: int
    ban_time: int
    find_time: int


@dataclass(frozen=True, slots=True)
class JailStatus:
    """Statut détaillé d'un jail.

    Attributs:
        name: nom du jail.
        currently_failed: nombre d'échecs actuels.
        total_failed: nombre total d'échecs.
        failed_ips: liste des IPs ayant échoué.
        banned_ips: liste des IPs bannies.
    """
    name: str
    currently_failed: int
    total_failed: int
    failed_ips: list[IPAddress]
    banned_ips: list[IPAddress]


class Fail2banPort(Protocol):
    """Contrat pour l'interaction avec Fail2ban.

    Définit les opérations attendues pour gérer les jails,
    bannir/débannir des IPs, et contrôler le service.
    """

    @abstractmethod
    def list_jails(self) -> list[JailInfo]:
        """Liste tous les jails configurés.

        Returns:
            Liste de JailInfo.
        """
        ...

    @abstractmethod
    def get_jail_status(self, jail_name: str) -> JailStatus:
        """Récupère le statut détaillé d'un jail.

        Args:
            jail_name: nom du jail.

        Returns:
            JailStatus avec compteurs et listes d'IPs.

        Raises:
            JailNotFoundError: si le jail n'existe pas.
        """
        ...

    @abstractmethod
    def ban_ip(self, jail_name: str, ip: IPAddress) -> None:
        """Bannit une IP dans un jail spécifique.

        Args:
            jail_name: nom du jail.
            ip: adresse IP à bannir.

        Raises:
            JailNotFoundError: si le jail n'existe pas.
            IPAlreadyBannedError: si l'IP est déjà bannie.
        """
        ...

    @abstractmethod
    def unban_ip(self, jail_name: str, ip: IPAddress) -> None:
        """Débannit une IP d'un jail spécifique.

        Args:
            jail_name: nom du jail.
            ip: adresse IP à débannir.

        Raises:
            JailNotFoundError: si le jail n'existe pas.
            IPNotFoundError: si l'IP n'est pas bannie.
        """
        ...

    @abstractmethod
    def flush_jail(self, jail_name: str) -> int:
        """Vide complètement un jail (débannit toutes les IPs).

        Args:
            jail_name: nom du jail.

        Returns:
            Nombre d'IPs débannies.

        Raises:
            JailNotFoundError: si le jail n'existe pas.
        """
        ...

    @abstractmethod
    def flush_all_jails(self) -> int:
        """Vide tous les jails.

        Returns:
            Nombre total d'IPs débannies.
        """
        ...

    @abstractmethod
    def create_jail(
        self,
        name: str,
        filter_name: str,
        log_path: str,
        *,
        max_retry: int | str = 5,
        ban_time: int | str = 3600,
        find_time: int | str = 600,
        port: str | None = None,
    ) -> JailInfo:
        """Crée un nouveau jail.

        Args:
            name: nom du jail.
            filter_name: nom du filtre à utiliser.
            log_path: chemin du fichier de log à surveiller.
            max_retry: nombre maximum de tentatives avant ban.
            ban_time: durée du ban en secondes, ou en syntaxe humaine
                fail2ban (ex: "1h", "24h") — les deux formes sont écrites
                telles quelles dans le jail.d, fail2ban les interprète
                nativement à la lecture (aucune conversion nécessaire ici).
            find_time: fenêtre de détection en secondes, ou en syntaxe
                humaine fail2ban (ex: "10m") — même remarque que ban_time.
            port: port(s) ciblé(s) par l'action de ban (ex: "80,443",
                "ssh") — écrit dans le jail.d généré si fourni ; omis
                (comportement inchangé) si None, laissant fail2ban
                retomber sur le port par défaut du filtre.

        Returns:
            JailInfo du jail créé.

        Raises:
            JailAlreadyExistsError: si le jail existe déjà.
        """
        ...

    @abstractmethod
    def delete_jail(self, jail_name: str) -> None:
        """Supprime un jail.

        Args:
            jail_name: nom du jail à supprimer.

        Raises:
            JailNotFoundError: si le jail n'existe pas.
        """
        ...

    @abstractmethod
    def list_configured_jail_files(self, jail_d_dir: str = "/etc/fail2ban/jail.d") -> dict[str, str]:
        """Liste les jails configurés sur disque (jail_d_dir), indépendamment
        de l'accessibilité du démon fail2ban.

        Contrairement à `list_jails()`/`get_jail_status()`, qui dépendent
        d'un appel `fail2ban-client status` réussi, cette méthode lit
        directement le répertoire de configuration — elle reste utilisable
        pour retrouver un jail orphelin même quand le démon est injoignable.

        Args:
            jail_d_dir: répertoire de configuration des jails (surchargable
                pour les tests).

        Returns:
            Dictionnaire {nom_du_jail: chemin_du_fichier_de_config}.
        """
        ...

    @abstractmethod
    def write_filter(self, filter_name: str, content: str) -> bool:
        """Écrit un fichier de filtre, seulement s'il n'existe pas déjà.

        Le contenu (regex de détection) est fourni par l'appelant —
        générer ce contenu est une décision métier (domain/), pas une
        responsabilité de cet adaptateur (voir domain/fail2ban/filters.py).

        Args:
            filter_name: nom du filtre (écrit en {filter_name}.conf).
            content: contenu complet du fichier de filtre, écrit tel quel.

        Returns:
            True si le fichier a été écrit, False s'il existait déjà
            (laissé inchangé dans ce cas — jamais d'écrasement).
        """
        ...

    @abstractmethod
    def verify_config(self) -> tuple[bool, list[str]]:
        """Vérifie la configuration Fail2ban.

        Returns:
            Tuple (is_valid, errors) où is_valid est True si la config est valide,
            et errors est la liste des erreurs trouvées.
        """
        ...

    @abstractmethod
    def stop_service(self) -> None:
        """Arrête le service Fail2ban.

        Raises:
            ServiceControlError: si l'arrêt échoue.
        """
        ...

    @abstractmethod
    def restart_service(self) -> None:
        """Redémarre le service Fail2ban.

        Raises:
            ServiceControlError: si le redémarrage échoue.
        """
        ...

    @abstractmethod
    def enable_service(self) -> None:
        """Active le service Fail2ban au démarrage.

        Raises:
            ServiceControlError: si l'activation échoue.
        """
        ...

    @abstractmethod
    def start_service(self) -> None:
        """Démarre le service Fail2ban.

        Raises:
            ServiceControlError: si le démarrage échoue.
        """
        ...

    @abstractmethod
    def disable_service(self) -> None:
        """Désactive le service Fail2ban au démarrage.

        Raises:
            ServiceControlError: si la désactivation échoue.
        """
        ...

    @abstractmethod
    def is_service_active(self) -> bool:
        """Indique si le service Fail2ban est actuellement actif.

        Returns:
            True si le service est actif.
        """
        ...

    @abstractmethod
    def is_service_enabled(self) -> bool:
        """Indique si le service Fail2ban est activé au démarrage.

        Returns:
            True si le service est activé au démarrage.
        """
        ...

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit le contrat (Protocol) pour l'interaction avec Fail2ban.
# - Fournit JailInfo et JailStatus (dataclasses frozen).
# - Spécifie les opérations : list_jails(), get_jail_status(), ban_ip(), unban_ip(),
#   flush_jail(), flush_all_jails(), create_jail(), delete_jail(), verify_config(),
#   stop_service(), restart_service(), enable_service(), start_service(),
#   disable_service(), is_service_active(), is_service_enabled().
#
# Pourquoi dans ports/ (charte) :
# - C'est un contrat attendu par le cœur applicatif (application/commands/)
# - Pas d'implémentation concrète (c'est le rôle de infrastructure/backends/fail2ban/)
# - Aucune dépendance vers domain/, application/, infrastructure/, interfaces/
#
# Ce qu'il ne contient PAS :
# ❌ Pas d'implémentation concrète (appels fail2ban-client)
# ❌ Pas d'import depuis domain/
# ❌ Pas d'import depuis application/
# ❌ Pas d'import depuis infrastructure/
# ❌ Pas d'import depuis interfaces/
# ❌ Pas de logique de parsing de sortie fail2ban-client
#
# Points clés :
# - JailInfo : dataclass frozen avec name, active, banned_count, banned_ips, filter,
#   log_path, max_retry, ban_time, find_time
# - JailStatus : dataclass frozen avec name, currently_failed, total_failed,
#   failed_ips, banned_ips
# - Fail2banPort : Protocol définissant toutes les opérations sur jails et service
# - IPAddress importé depuis shared/networking.py
# - Toutes les méthodes sont abstraites (via Protocol)
#
# Comment il sera utilisé (aperçu) :
# - application/commands/jail_ban.py appellera fail2ban_port.ban_ip()
# - application/commands/jail_unban.py appellera fail2ban_port.unban_ip()
# - infrastructure/backends/fail2ban/adapter.py implémentera Fail2banPort
# - interfaces/cli/actions.py appellera fail2ban_port.list_jails() pour menu 4.1
#---------------------------------------------------------------------->        
