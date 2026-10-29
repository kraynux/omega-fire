# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Probe exceptions.

Technical exceptions specific to the probe subsystem.
These express failures in system detection, capability probing,
or mapping operations. They are caught by the application layer
and translated into capability status updates in the registry.
"""
from omega_fire.core.exceptions import CoreError
from omega_fire.shared.i18n import _


class ProbeError(CoreError):
    """Base exception for probe operations.
    
    All probe-specific exceptions inherit from this class.
    """
    def __init__(self, message: str, probe_name: str = None, context: dict = None):
        super().__init__(message, context)
        self.probe_name = probe_name
        if probe_name:
            self.context["probe_name"] = probe_name


class ProbeExecutionError(ProbeError):
    """Raised when a probe fails to execute.
    
    This is raised when the probe encounters an unexpected error
    during execution (permission denied, binary not found, etc.).
    """
    def __init__(
        self,
        probe_name: str,
        reason: str,
        context: dict = None,
    ):
        super().__init__(
            _("Échec de la sonde « {probe_name} » : {reason}").format(probe_name=probe_name, reason=reason),
            probe_name=probe_name,
            context={**(context or {}), "reason": reason},
        )
        self.reason = reason


class ProbeTimeoutError(ProbeError):
    """Raised when a probe times out.
    
    This is raised when a probe takes too long to complete
    and exceeds the configured timeout.
    """
    def __init__(
        self,
        probe_name: str,
        timeout_seconds: float,
        context: dict = None,
    ):
        super().__init__(
            _("Sonde « {probe_name} » interrompue après {timeout_seconds} s").format(probe_name=probe_name, timeout_seconds=timeout_seconds),
            probe_name=probe_name,
            context={**(context or {}), "timeout_seconds": timeout_seconds},
        )
        self.timeout_seconds = timeout_seconds


class CapabilityMappingError(ProbeError):
    """Raised when mapping probe results to capabilities fails.
    
    This is raised when the capability mapper cannot convert
    raw probe results into valid Capability objects.
    """
    def __init__(
        self,
        probe_name: str,
        reason: str,
        context: dict = None,
    ):
        super().__init__(
            _("Impossible de rattacher la sonde « {probe_name} » à une capacité : {reason}").format(probe_name=probe_name, reason=reason),
            probe_name=probe_name,
            context={**(context or {}), "reason": reason},
        )
        self.reason = reason


class ScannerError(ProbeError):
    """Raised when the scanner encounters a critical error.
    
    This is raised when the scanner cannot complete its scan
    due to a fundamental error (registry unavailable, etc.).
    """
    def __init__(
        self,
        reason: str,
        probes_completed: int = 0,
        probes_failed: int = 0,
        context: dict = None,
    ):
        super().__init__(
            _("Échec du scan : {reason}").format(reason=reason),
            probe_name="scanner",
            context={
                **(context or {}),
                "reason": reason,
                "probes_completed": probes_completed,
                "probes_failed": probes_failed,
            },
        )
        self.reason = reason
        self.probes_completed = probes_completed
        self.probes_failed = probes_failed


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Définit les exceptions techniques spécifiques au sous-domaine probe.
#   Ces exceptions expriment des pannes ou limitations techniques liées à
#   la détection des capacités système (commandes, services, noyau).
# Pourquoi dans infrastructure/ (charte) :
# - Ce sont des erreurs techniques, pas des règles métier
# - Elles encapsulent les pannes système (timeout, mapping échoué, scan incomplet)
# - Elles héritent de CoreError (exception transverse) pour être capturées
#   uniformément par application/
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier (pas de règles firewall/fail2ban)
# ❌ Pas d'appels système (juste des définitions d'exceptions)
# ❌ Pas de dépendance vers domain/ ou interfaces/
# Points clés :
# - Hiérarchie claire : toutes les exceptions héritent de ProbeError
# - 4 exceptions ciblées :
#   - ProbeExecutionError : échec d'exécution d'un probe
#   - ProbeTimeoutError : timeout d'un probe
#   - CapabilityMappingError : échec du mapping probe → capability
#   - ScannerError : échec critique du scanner
# - Contexte riche : chaque exception stocke les données pertinentes
#   (probe_name, reason, timeout_seconds, probes_completed, probes_failed)
# Comment elles seront utilisées (aperçu) :
# - infrastructure/probe/command_probe.py les lèvera lors de l'exécution
# - infrastructure/probe/capability_mapper.py les lèvera lors du mapping
# - infrastructure/probe/scanner.py les lèvera lors du scan global
# - application/ les capturera pour mettre à jour le registre
#---------------------------------------------------------------------->
