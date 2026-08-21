# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Conntrack backend adapter.

Implements the concrete conntrack operations: list connections, get count,
kill connections. Uses subprocess to execute conntrack commands.

This is the only module that directly calls conntrack via subprocess.
"""
import subprocess
from typing import Optional
from omega_fire.domain.monitoring.conntrack import Connection, ConnectionState, ConnectionProtocol
from omega_fire.infrastructure.backends.conntrack.parser import ConntrackParser
from omega_fire.infrastructure.backends.conntrack.exceptions import (
    ConntrackCommandError,
    ConntrackPermissionError,
)


class ConntrackAdapter:
    """Concrete adapter for conntrack operations.

    Executes conntrack commands via subprocess and transforms results
    into domain models using parser.
    """

    def __init__(self, timeout: float = 10.0):
        """Initialize the conntrack adapter.

        Args:
            timeout: Maximum time for command execution (seconds)
        """
        self._parser = ConntrackParser()
        self._timeout = timeout

    def _run_command(self, cmd: list[str]) -> str:
        """Execute a conntrack command and return stdout.

        Args:
            cmd: Command as list of arguments

        Returns:
            Command stdout as string

        Raises:
            ConntrackCommandError: If the command fails
            ConntrackPermissionError: If permission is denied
        """
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self._timeout,
                check=False,
            )

            if result.returncode != 0:
                stderr = result.stderr.strip()
                if "Permission denied" in stderr or "Operation not permitted" in stderr:
                    raise ConntrackPermissionError(operation=" ".join(cmd[:3]))
                raise ConntrackCommandError(
                    command=" ".join(cmd),
                    returncode=result.returncode,
                    stderr=stderr,
                )

            return result.stdout

        except subprocess.TimeoutExpired:
            raise ConntrackCommandError(
                command=" ".join(cmd),
                returncode=-1,
                stderr=f"Command timed out after {self._timeout}s",
            )
        except FileNotFoundError:
            raise ConntrackCommandError(
                command=" ".join(cmd),
                returncode=-1,
                stderr="conntrack binary not found",
            )

    def list_connections(self) -> list[dict]:
        """List all tracked connections.

        Returns:
            List of connection dictionaries
        """
        output = self._run_command(["conntrack", "-L"])
        return self._parser.parse_connection_list(output)

    def get_connection_count(self) -> int:
        """Get the total number of tracked connections.

        Returns:
            Number of connections
        """
        output = self._run_command(["conntrack", "-C"])
        return self._parser.parse_connection_count(output)

    def kill_connection(
        self,
        source_ip: str,
        source_port: int,
        destination_ip: str,
        destination_port: int,
        protocol: str = "tcp",
    ) -> bool:
        """Kill a specific connection.

        Args:
            source_ip: Source IP address
            source_port: Source port
            destination_ip: Destination IP address
            destination_port: Destination port
            protocol: Protocol (tcp, udp, icmp)

        Returns:
            True if the connection was killed successfully
        """
        cmd = [
            "conntrack", "-D",
            "-s", source_ip,
            "--sport", str(source_port),
            "-d", destination_ip,
            "--dport", str(destination_port),
            "-p", protocol,
        ]
        self._run_command(cmd)
        return True

    def kill_connections_by_ip(self, ip: str) -> int:
        """Kill all connections involving a specific IP.

        Args:
            ip: IP address (source or destination)

        Returns:
            Number of connections killed
        """
        count = 0

        # Kill connections where IP is source
        try:
            cmd = ["conntrack", "-D", "-s", ip]
            self._run_command(cmd)
            count += 1
        except ConntrackCommandError:
            pass

        # Kill connections where IP is destination
        try:
            cmd = ["conntrack", "-D", "-d", ip]
            self._run_command(cmd)
            count += 1
        except ConntrackCommandError:
            pass

        return count

    def is_available(self) -> bool:
        """Check if conntrack is available on the system.

        Returns:
            True if conntrack is installed and functional
        """
        try:
            self._run_command(["conntrack", "--version"])
            return True
        except (ConntrackCommandError, ConntrackPermissionError):
            return False


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Implémente les opérations concrètes conntrack via subprocess
# - Point d'entrée unique pour toutes les interactions avec conntrack
# - Retourne des dicts structurés ou des compteurs
# Pourquoi dans infrastructure/ (charte) :
# - C'est le SEUL module autorisé à appeler conntrack via subprocess
# - Implémente les contrats que l'application/ utilisera via les ports
# - L'application/ ne doit JAMAIS importer ce module directement
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier (pas de filtrage avancé, pas de politiques)
# ❌ Pas de dépendance vers application/ ou interfaces/
# ❌ Pas de décision de grisage ou d'autorisation
# Points clés :
# - ConntrackAdapter : classe principale avec timeout configurable
# - _run_command() : exécute une commande conntrack via subprocess.run()
#   - Gère les timeouts, permissions, binaires manquants
#   - Lève ConntrackCommandError ou ConntrackPermissionError
# - list_connections() : retourne la liste des connexions sous forme de dicts
# - get_connection_count() : retourne le nombre total de connexions
# - kill_connection() : tue une connexion spécifique par IP:port
# - kill_connections_by_ip() : tue toutes les connexions impliquant une IP
# - is_available() : vérifie que conntrack est installé
# - Composition : utilise ConntrackParser pour le parsing
# Note : les exceptions conntrack/exceptions.py n'existent pas encore dans l'arborescence
#        mais suivront le même pattern que les autres backends
# Comment il sera utilisé (aperçu) :
# - ports/monitoring.py définira le contrat que cet adapter implémente
# - app/bootstrap.py instanciera cet adapter et l'injectera via les ports
# - application/queries/ utilisera le port (pas cet adapter directement)
# - Les tests mockeront subprocess.run pour simuler différents états
#---------------------------------------------------------------------->
