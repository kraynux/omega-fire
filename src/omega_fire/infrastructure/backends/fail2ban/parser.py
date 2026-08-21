# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Fail2ban output parser.

Parses the output of fail2ban-client commands into structured data.
Handles jail listing, status queries, and ban lists.

This module performs no I/O — it only parses strings. The actual command
execution is done by the adapter.
"""
import re
from typing import Optional


class Fail2banParser:
    """Parses fail2ban-client command output into structured data."""

    def parse_jail_list(self, output: str) -> list[str]:
        """Parse the list of jails from fail2ban-client status.

        Args:
            output: Raw output from 'fail2ban-client status'

        Returns:
            List of jail names
        """
        jails = []
        for line in output.split("\n"):
            stripped = line.strip()
            if "Jail list:" in stripped:
                # Format: "Jail list: sshd, nginx, apache"
                match = re.search(r"Jail list:\s*(.+)", stripped)
                if match:
                    jail_str = match.group(1).strip()
                    if jail_str:
                        jails = [j.strip() for j in jail_str.split(",") if j.strip()]
                break
        return jails

    def parse_jail_status(self, output: str, jail_name: str) -> dict:
        """Parse the status of a specific jail.

        Args:
            output: Raw output from 'fail2ban-client status <jail>'
            jail_name: Name of the jail

        Returns:
            Dictionary with jail status information
        """
        status = {
            "name": jail_name,
            "currently_failed": 0,
            "total_failed": 0,
            "currently_banned": 0,
            "total_banned": 0,
            "banned_ips": [],
        }

        for line in output.split("\n"):
            stripped = line.strip()

            if "Currently failed:" in stripped:
                match = re.search(r"Currently failed:\s*(\d+)", stripped)
                if match:
                    status["currently_failed"] = int(match.group(1))

            elif "Total failed:" in stripped:
                match = re.search(r"Total failed:\s*(\d+)", stripped)
                if match:
                    status["total_failed"] = int(match.group(1))

            elif "Currently banned:" in stripped:
                match = re.search(r"Currently banned:\s*(\d+)", stripped)
                if match:
                    status["currently_banned"] = int(match.group(1))

            elif "Total banned:" in stripped:
                match = re.search(r"Total banned:\s*(\d+)", stripped)
                if match:
                    status["total_banned"] = int(match.group(1))

            elif "Banned IP list:" in stripped:
                match = re.search(r"Banned IP list:\s*(.+)", stripped)
                if match:
                    ip_str = match.group(1).strip()
                    if ip_str:
                        status["banned_ips"] = [ip.strip() for ip in ip_str.split() if ip.strip()]

        return status

    def parse_ban_list(self, output: str) -> list[str]:
        """Parse the list of banned IPs from a jail status.

        Args:
            output: Raw output from 'fail2ban-client status <jail>'

        Returns:
            List of banned IP addresses
        """
        for line in output.split("\n"):
            if "Banned IP list:" in line:
                match = re.search(r"Banned IP list:\s*(.+)", line)
                if match:
                    ip_str = match.group(1).strip()
                    if ip_str:
                        return [ip.strip() for ip in ip_str.split() if ip.strip()]
        return []

    def parse_get_command(self, output: str) -> str:
        """Parse the output of a fail2ban-client get command.

        Args:
            output: Raw output from 'fail2ban-client get <jail> <param>'

        Returns:
            The value as a string
        """
        return output.strip()

    def parse_logpath(self, output: str) -> str:
        """Parse the output of 'fail2ban-client get <jail> logpath'.

        Unlike most 'get' params (e.g. maxretry, bantime), logpath is not
        returned as a raw value — fail2ban-client formats it as a small
        human-readable block, observed in two real forms:
            "No file is currently monitored"
          or
            "Current monitored log file(s):\n`- /var/log/auth.log"
        (possibly several "`- <path>" lines if more than one file is watched).

        Args:
            output: Raw output from 'fail2ban-client get <jail> logpath'

        Returns:
            Comma-separated list of monitored log paths, or "" if none.
        """
        stripped = output.strip()
        if not stripped or "no file is currently monitored" in stripped.lower():
            return ""
        paths = re.findall(r"`-\s*(.+)", stripped)
        return ", ".join(p.strip() for p in paths) if paths else stripped

    def parse_set_ip_result(self, output: str) -> int:
        """Parse the numeric result of 'set <jail> banip/unbanip <ip>'.

        fail2ban-client's documented convention for this command is to
        print the count of IPs actually affected — "1" on a genuine
        ban/unban, "0" if the IP was already in the requested state
        (already banned / not currently banned). Not yet confirmed
        against the real binary at the time this was written — verified
        by the caller's smoke-test (adapter.ban_ip()/unban_ip()).

        Args:
            output: Raw stdout from 'fail2ban-client set <jail> banip/unbanip <ip>'

        Returns:
            The parsed count, or -1 if the output isn't a bare integer
            (unexpected format — callers should treat this conservatively,
            i.e. not assume "already banned"/"not found" from it).
        """
        stripped = output.strip()
        if stripped.lstrip("-").isdigit():
            return int(stripped)
        return -1


def parse_fail2ban_jails(output: str) -> list[str]:
    """Convenience function to parse jail list."""
    return Fail2banParser().parse_jail_list(output)


def parse_fail2ban_status(output: str, jail_name: str) -> dict:
    """Convenience function to parse jail status."""
    return Fail2banParser().parse_jail_status(output, jail_name)


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Parse la sortie textuelle des commandes fail2ban-client en structures de données
# - Gère le parsing de la liste des jails, du statut d'un jail et des IPs bannies
# - Extrait les compteurs (currently_failed, total_banned, etc.)
# Pourquoi dans infrastructure/ (charte) :
# - C'est un parser technique qui traite la sortie brute d'une commande système
# - Le format de sortie fail2ban-client est un détail d'implémentation
# - Produit des dicts/strings bruts qui seront mappés en objets métier
# Ce qu'il ne contient PAS :
# ❌ Pas d'appels système (reçoit la sortie en string, ne lance pas fail2ban-client)
# ❌ Pas de logique métier (pas de validation de jail, pas de politiques)
# ❌ Pas de dépendance vers domain/, application/ ou interfaces/
# Points clés :
# - Fail2banParser : classe principale avec 4 méthodes de parsing
# - parse_jail_list() : parse 'fail2ban-client status' pour extraire les noms de jails
# - parse_jail_status() : parse 'fail2ban-client status <jail>' pour extraire les compteurs
# - parse_ban_list() : extrait les IPs bannies d'un jail
# - parse_get_command() : parse la sortie d'une commande get
# - Utilise des regex pour extraire les champs de la sortie textuelle
# - Ne fait aucun I/O : reçoit des strings, retourne des dicts/lists
# - Fonctions de convenance : parse_fail2ban_jails(), parse_fail2ban_status()
# Comment il sera utilisé (aperçu) :
# - infrastructure/backends/fail2ban/adapter.py l'appellera après chaque commande
# - infrastructure/backends/fail2ban/jail_mapper.py transformera les dicts en objets métier
# - Les tests utiliseront des fixtures de sortie fail2ban pour vérifier le parsing
#---------------------------------------------------------------------->
