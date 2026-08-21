# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Command probe.

Tests the presence and basic functionality of system commands/binaries.
Uses shutil.which() to check if a binary is in PATH, and optionally
runs a simple test command to verify it works.

This module performs real system I/O (binary checks, subprocess calls)
and is therefore in infrastructure/.
"""
import shutil
import subprocess
from typing import Optional
from omega_fire.infrastructure.probe.exceptions import (
    ProbeExecutionError,
    ProbeTimeoutError,
)


class CommandProbe:
    """Probes the presence and functionality of system commands.
    
    Checks if a binary is available in PATH and optionally runs
    a test command to verify it works correctly.
    """
    
    def __init__(self, timeout_seconds: float = 5.0):
        """Initialize the command probe.
        
        Args:
            timeout_seconds: Maximum time to wait for test commands (default: 5s)
        """
        self._timeout = timeout_seconds
    
    def check_presence(self, binary_name: str) -> bool:
        """Check if a binary is present in PATH.
        
        Args:
            binary_name: Name of the binary to check (e.g., "nft", "iptables")
        
        Returns:
            True if the binary is found in PATH, False otherwise
        """
        return shutil.which(binary_name) is not None
    
    def get_binary_path(self, binary_name: str) -> Optional[str]:
        """Get the full path to a binary.
        
        Args:
            binary_name: Name of the binary to locate
        
        Returns:
            Full path to the binary if found, None otherwise
        """
        return shutil.which(binary_name)
    
    def check_functionality(
        self,
        binary_name: str,
        test_command: Optional[list[str]] = None,
    ) -> tuple[bool, str]:
        """Check if a binary is present and functional.
        
        Args:
            binary_name: Name of the binary to check
            test_command: Optional test command to run (e.g., ["nft", "--version"])
                         If None, only checks presence
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        # Check presence
        binary_path = self.get_binary_path(binary_name)
        if binary_path is None:
            return False, f"Binary '{binary_name}' not found in PATH"
        
        # If no test command, just check presence
        if test_command is None:
            return True, f"Binary '{binary_name}' found at {binary_path}"
        
        # Run test command
        try:
            result = subprocess.run(
                test_command,
                capture_output=True,
                text=True,
                timeout=self._timeout,
                check=False,
            )
            
            if result.returncode == 0:
                return True, f"Binary '{binary_name}' is functional"
            else:
                error_msg = result.stderr.strip() or f"Exit code {result.returncode}"
                return False, f"Binary '{binary_name}' test failed: {error_msg}"
        
        except subprocess.TimeoutExpired:
            return False, f"Binary '{binary_name}' test timed out after {self._timeout}s"
        except FileNotFoundError:
            return False, f"Binary '{binary_name}' disappeared during test"
        except Exception as e:
            return False, f"Binary '{binary_name}' test error: {e}"
    
    def probe_command(
        self,
        binary_name: str,
        test_command: Optional[list[str]] = None,
    ) -> dict:
        """Probe a command and return detailed results.
        
        Args:
            binary_name: Name of the binary to probe
            test_command: Optional test command to run
        
        Returns:
            Dictionary with probe results:
            - present: bool
            - functional: bool
            - path: Optional[str]
            - message: str
        """
        present = self.check_presence(binary_name)
        path = self.get_binary_path(binary_name)
        
        if not present:
            return {
                "present": False,
                "functional": False,
                "path": None,
                "message": f"Binary '{binary_name}' not found in PATH",
            }
        
        functional, message = self.check_functionality(binary_name, test_command)
        
        return {
            "present": True,
            "functional": functional,
            "path": path,
            "message": message,
        }


def probe_command(
    binary_name: str,
    test_command: Optional[list[str]] = None,
    timeout_seconds: float = 5.0,
) -> dict:
    """Convenience function to probe a command.
    
    Args:
        binary_name: Name of the binary to probe
        test_command: Optional test command to run
        timeout_seconds: Maximum time to wait for test commands
    
    Returns:
        Dictionary with probe results
    """
    probe = CommandProbe(timeout_seconds=timeout_seconds)
    return probe.probe_command(binary_name, test_command)


def is_command_available(binary_name: str) -> bool:
    """Check if a command is available in PATH.
    
    Args:
        binary_name: Name of the binary to check
    
    Returns:
        True if the binary is found
    """
    probe = CommandProbe()
    return probe.check_presence(binary_name)


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Teste la présence et la fonctionnalité des commandes/binaires système
# - Utilise shutil.which() pour vérifier si un binaire est dans PATH
# - Optionnellement exécute une commande de test pour vérifier le fonctionnement
# - Retourne des résultats détaillés (présent, fonctionnel, chemin, message)
# Pourquoi dans infrastructure/ (charte) :
# - C'est une détection technique qui nécessite des I/O système réels
#   (vérification de binaires via shutil.which, subprocess pour les tests)
# - Le résultat est utilisé par capability_mapper pour créer des Capability
# - Aucun autre module ne doit recoder cette détection (clause omega-fire)
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier (pas de règles firewall/fail2ban)
# ❌ Pas de mapping vers Capability (c'est le rôle de capability_mapper)
# ❌ Pas de dépendance vers domain/ ou interfaces/
# Points clés :
# - CommandProbe : classe principale avec timeout configurable
# - check_presence() : vérifie si un binaire est dans PATH
# - get_binary_path() : retourne le chemin complet du binaire
# - check_functionality() : exécute une commande de test optionnelle
#   - Retourne (success, message)
#   - Gère les timeouts, erreurs, binaires disparus
# - probe_command() : méthode principale qui retourne un dict détaillé
#   - present : bool (binaire trouvé)
#   - functional : bool (test réussi)
#   - path : Optional[str] (chemin complet)
#   - message : str (description du résultat)
# - Fonctions de convenance : probe_command(), is_command_available()
# - Timeout par défaut : 5 secondes pour éviter les blocages
# Comment il sera utilisé (aperçu) :
# - infrastructure/probe/scanner.py l'utilisera pour tester nft, iptables, fail2ban-client
# - infrastructure/probe/capability_mapper.py transformera les résultats en Capability
# - Les tests mockeront shutil.which et subprocess pour simuler différents états
#---------------------------------------------------------------------->
