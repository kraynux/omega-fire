# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Capability mapper.

Transforms raw probe results into Capability objects that can be
registered in the capability registry. Maps probe outcomes to
appropriate CapabilityStatus values (AVAILABLE, DEGRADED, MISSING, DISQUALIFIED).

This module is in infrastructure/ because it processes technical
probe results, but it produces domain-agnostic Capability objects
that can be consumed by any layer.
"""
from typing import Any
from omega_fire.core.capability import Capability, create_capability
from omega_fire.core.enums import CapabilityStatus
from omega_fire.shared.i18n import N_, _, lazy


class CapabilityMapper:
    """Maps probe results to Capability objects.
    
    Transforms raw probe results (from command_probe, service_probe, etc.)
    into Capability objects with appropriate status, reason, and details.
    """
    
    def map_command_probe_result(
        self,
        capability_id: str,
        probe_result: dict[str, Any],
        category: str = "backend",
    ) -> Capability:
        """Map a command probe result to a Capability."""
        present = probe_result.get("present", False)
        functional = probe_result.get("functional", False)
        path = probe_result.get("path")
        message = probe_result.get("message", "")
        
        if not present:
            return create_capability(
                capability_id=capability_id,
                status=CapabilityStatus.MISSING,
                reason=lazy(N_("Composant non installé : {message}"), message=message) if message else lazy(N_("Binaire introuvable sur le système")),
                detail={"path": path, "message": message},
                category=category,
            )
        
        if not functional:
            return create_capability(
                capability_id=capability_id,
                status=CapabilityStatus.DISQUALIFIED,
                reason=lazy(N_("Binaire présent mais non fonctionnel : {message}"), message=message),
                detail={"path": path, "message": message},
                category=category,
            )
        
        return create_capability(
            capability_id=capability_id,
            status=CapabilityStatus.AVAILABLE,
            reason=lazy(N_("Binaire opérationnel ({path})"), path=path),
            detail={"path": path, "message": message},
            category=category,
        )
    
    def map_service_probe_result(
        self,
        capability_id: str,
        probe_result: dict[str, Any],
        category: str = "service",
    ) -> Capability:
        """Map a service probe result to a Capability."""
        available = probe_result.get("available", False)
        exists = probe_result.get("exists", False)
        active = probe_result.get("active", False)
        enabled = probe_result.get("enabled", False)
        state = probe_result.get("state", "unknown")
        message = probe_result.get("message", "")
        
        # 1. Gestionnaire de services indisponible sur la machine
        if not available:
            return create_capability(
                capability_id=capability_id,
                status=CapabilityStatus.MISSING,
                reason=lazy(N_("Gestionnaire de services indisponible : {message}"), message=message),
                detail={"state": state, "message": message},
                category=category,
            )
        
        # 2. Service non installé / Introuvable
        if not exists:
            return create_capability(
                capability_id=capability_id,
                status=CapabilityStatus.MISSING,
                reason=lazy(N_("Service non installé sur le système ({message})"), message=message) if message else lazy(N_("Service introuvable")),
                detail={"state": state, "message": message},
                category=category,
            )
        
        # 3. Service installé mais INACTIF (arrêté)
        if not active:
            return create_capability(
                capability_id=capability_id,
                status=CapabilityStatus.DEGRADED,
                reason=lazy(N_("Service installé mais INACTIF (arrêté) : {message}"), message=message),
                detail={
                    "state": state,
                    "active": active,
                    "enabled": enabled,
                    "message": message,
                },
                category=category,
            )
        
        # 4. Service actif mais NON activé au démarrage (enabled = False)
        if not enabled:
            return create_capability(
                capability_id=capability_id,
                status=CapabilityStatus.AVAILABLE,
                reason=lazy(N_("Service actif (attention : désactivé au démarrage) : {message}"), message=message),
                detail={
                    "state": state,
                    "active": active,
                    "enabled": enabled,
                    "message": message,
                },
                category=category,
            )
        
        # 5. Service actif ET activé au démarrage (Opérationnel à 100%)
        return create_capability(
            capability_id=capability_id,
            status=CapabilityStatus.AVAILABLE,
            reason=lazy(N_("Service actif et activé au démarrage : {message}"), message=message),
            detail={
                "state": state,
                "active": active,
                "enabled": enabled,
                "message": message,
            },
            category=category,
        )
    
    def map_kernel_probe_result(
        self,
        capability_id: str,
        probe_result: dict[str, Any],
        category: str = "kernel",
    ) -> Capability:
        """Map a kernel probe result to a Capability."""
        available = probe_result.get("available", False)
        modules = probe_result.get("modules", [])
        message = probe_result.get("message", "")
        
        if not available:
            return create_capability(
                capability_id=capability_id,
                status=CapabilityStatus.MISSING,
                reason=lazy(N_("Modules noyau indisponibles : {message}"), message=message),
                detail={"modules": modules, "message": message},
                category=category,
            )
        
        return create_capability(
            capability_id=capability_id,
            status=CapabilityStatus.AVAILABLE,
            reason=lazy(N_("Modules noyau disponibles : {value}"), value=', '.join(modules)),
            detail={"modules": modules, "message": message},
            category=category,
        )


def map_command_to_capability(
    capability_id: str,
    probe_result: dict[str, Any],
    category: str = "backend",
) -> Capability:
    mapper = CapabilityMapper()
    return mapper.map_command_probe_result(capability_id, probe_result, category)


def map_service_to_capability(
    capability_id: str,
    probe_result: dict[str, Any],
    category: str = "service",
) -> Capability:
    mapper = CapabilityMapper()
    return mapper.map_service_probe_result(capability_id, probe_result, category)


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Transforme les résultats bruts des probes en objets Capability
# - Mappe les résultats techniques (présent/fonctionnel/actif) vers des statuts métier
#   (AVAILABLE, DEGRADED, MISSING, DISQUALIFIED)
# - Produit des objets Capability consommables par le registre de capacités
# Pourquoi dans infrastructure/ (charte) :
# - C'est un composant technique qui traite des résultats de probes système
# - Mais il produit des objets domain-agnostic (Capability) consommables par toute couche
# - Fait le pont entre infrastructure/ (probes) et core/ (registry)
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier (pas de règles firewall/fail2ban)
# ❌ Pas d'appels système (reçoit des résultats déjà collectés)
# ❌ Pas de dépendance vers domain/ ou interfaces/
# Points clés :
# - CapabilityMapper : classe principale avec 3 méthodes de mapping
# - map_command_probe_result() : mappe les résultats de CommandProbe
#   - present=False → MISSING
#   - present=True, functional=False → DISQUALIFIED
#   - present=True, functional=True → AVAILABLE
# - map_service_probe_result() : mappe les résultats de ServiceProbe
#   - available=False → MISSING (pas de gestionnaire)
#   - exists=False → MISSING (service introuvable)
#   - active=False → DEGRADED (service existe mais pas actif)
#   - active=True → AVAILABLE
# - map_kernel_probe_result() : mappe les résultats de kernel probe
#   - available=False → MISSING
#   - available=True → AVAILABLE
# - Chaque Capability contient :
#   - id : identifiant unique
#   - status : AVAILABLE/DEGRADED/MISSING/DISQUALIFIED
#   - reason : message lisible expliquant le statut
#   - detail : dict avec détails techniques (path, modules, etc.)
#   - category : catégorie (backend, service, kernel)
# - Fonctions de convenance : map_command_to_capability(), map_service_to_capability()
# Comment il sera utilisé (aperçu) :
# - infrastructure/probe/scanner.py l'utilisera pour mapper tous les résultats de probes
# - Les Capability produits seront enregistrés dans core/capability_registry
# - application/pipeline/guards/ consultera le registre pour autoriser/bloquer les actions
# - Les tests vérifieront que les mappings sont corrects pour différents scénarios
#---------------------------------------------------------------------->
