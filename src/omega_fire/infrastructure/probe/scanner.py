# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""System scanner.

Orchestrates all system probes and populates the capability registry.
Coordinates command probes, service probes, and kernel probes to
detect what is available on the current system.

This module is the entry point for system detection and is called
during application startup to populate the capability registry.
"""
from typing import Optional, Any
from omega_fire.core.capability_registry import CapabilityRegistry
from omega_fire.core.enums import CapabilityStatus
from omega_fire.infrastructure.probe.command_probe import CommandProbe
from omega_fire.infrastructure.probe.service_probe import ServiceProbe
from omega_fire.infrastructure.probe.capability_mapper import CapabilityMapper
from omega_fire.infrastructure.probe.exceptions import ScannerError


class SystemScanner:
    """Orchestrates system probes and populates the capability registry.
    
    Coordinates all probes (command, service, kernel) to detect
    what is available on the current system and registers the
    results in the capability registry.
    """
    
    def __init__(self, registry: CapabilityRegistry, settings: Optional[Any] = None):
        """Initialize the system scanner.
        
        Args:
            registry: The capability registry to populate
            settings: Optional AppSettings instance for user-defined resources
        """
        self._registry = registry
        self._settings = settings
        self._command_probe = CommandProbe()
        self._service_probe = ServiceProbe()
        self._mapper = CapabilityMapper()
    
    def scan(self) -> dict:
        """Run all system probes and populate the registry.
        
        Returns:
            Dictionary with scan results:
            - capabilities_registered: int
            - capabilities_available: int
            - capabilities_degraded: int
            - capabilities_missing: int
            - capabilities_disqualified: int
            - errors: list[str]
        """
        errors = []
        registered = 0
        available = 0
        degraded = 0
        missing = 0
        disqualified = 0
        
        # Scan backends (nftables, iptables, ip6tables)
        try:
            self._scan_backends()
            registered += 3
        except Exception as e:
            errors.append(f"Backend scan failed: {e}")
        
        # Scan fail2ban
        try:
            self._scan_fail2ban()
            registered += 3  # fail2ban_client + fail2ban_service
        except Exception as e:
            errors.append(f"Fail2ban scan failed: {e}")
        
        # Scan conntrack
        try:
            self._scan_conntrack()
            registered += 1
        except Exception as e:
            errors.append(f"Conntrack scan failed: {e}")
        
        # Scan service manager
        try:
            self._scan_service_manager()
            registered += 1
        except Exception as e:
            errors.append(f"Service manager scan failed: {e}")

        # Scan known services (system, servers, remote desktop, security)
        try:
            known_registered = self._scan_known_services()
            registered += known_registered
        except Exception as e:
            errors.append(f"Known services scan failed: {e}")

        # Scan user-defined resources (NEW)
        try:
            user_registered = self._load_user_config_capabilities()
            registered += user_registered
        except Exception as e:
            errors.append(f"User config scan failed: {e}")
        
        # Count capabilities by status
        for cap in self._registry.list_all():
            if cap.status == CapabilityStatus.AVAILABLE:
                available += 1
            elif cap.status == CapabilityStatus.DEGRADED:
                degraded += 1
            elif cap.status == CapabilityStatus.MISSING:
                missing += 1
            elif cap.status == CapabilityStatus.DISQUALIFIED:
                disqualified += 1
        
        return {
            "capabilities_registered": registered,
            "capabilities_available": available,
            "capabilities_degraded": degraded,
            "capabilities_missing": missing,
            "capabilities_disqualified": disqualified,
            "errors": errors,
        }

    def _scan_known_services(self) -> int:
        """Scan well-known system services/processes via pgrep.
        
        Uses the same process-detection mechanism as
        _load_user_config_capabilities()'s custom_web_servers, but for
        a fixed list of known services (infrastructure/probe/known_services.py)
        rather than user-declared ones.
        
        Returns:
            Number of capabilities registered.
        """
        from omega_fire.core.capability import create_capability
        from omega_fire.infrastructure.probe.known_services import KNOWN_SERVICES
        import subprocess
        
        registered_count = 0
        
        for category, process_names in KNOWN_SERVICES.items():
            for process_name in process_names:
                cap_id = process_name
                try:
                    result = subprocess.run(
                        ["pgrep", "-x", process_name],
                        capture_output=True,
                        timeout=2,
                    )
                    if result.returncode == 0:
                        capability = create_capability(
                            capability_id=cap_id,
                            status=CapabilityStatus.AVAILABLE,
                            reason="Processus détecté sur le système",
                            detail={"process": process_name},
                            category=category,
                        )
                    else:
                        capability = create_capability(
                            capability_id=cap_id,
                            status=CapabilityStatus.MISSING,
                            reason="Processus non détecté sur le système",
                            detail={"process": process_name},
                            category=category,
                        )
                except Exception:
                    capability = create_capability(
                        capability_id=cap_id,
                        status=CapabilityStatus.MISSING,
                        reason="Vérification impossible",
                        detail={"process": process_name},
                        category=category,
                    )
                
                if self._registry.is_registered(cap_id):
                    self._registry.update(capability)
                else:
                    self._registry.register(capability)
                registered_count += 1
        
        return registered_count
    
    
    def _scan_backends(self) -> None:
        """Scan nftables, iptables, and ip6tables backends."""
        # nftables
        nft_result = self._command_probe.probe_command(
            binary_name="nft",
            test_command=["nft", "--version"],
        )
        nft_capability = self._mapper.map_command_probe_result(
            capability_id="nftables",
            probe_result=nft_result,
            category="backend",
        )

        if self._registry.is_registered("nftables"):
            self._registry.update(nft_capability)
        else:
            self._registry.register(nft_capability)

        # iptables
        ipt_result = self._command_probe.probe_command(
            binary_name="iptables",
            test_command=["iptables", "--version"],
        )
        ipt_capability = self._mapper.map_command_probe_result(
            capability_id="iptables",
            probe_result=ipt_result,
            category="backend",
        )

        if self._registry.is_registered("iptables"):
            self._registry.update(ipt_capability)
        else:
            self._registry.register(ipt_capability)

        # ip6tables (référentiel §65, plan IPv6 iptables)
        ipt6_result = self._command_probe.probe_command(
            binary_name="ip6tables",
            test_command=["ip6tables", "--version"],
        )
        ipt6_capability = self._mapper.map_command_probe_result(
            capability_id="ip6tables",
            probe_result=ipt6_result,
            category="backend",
        )

        if self._registry.is_registered("ip6tables"):
            self._registry.update(ipt6_capability)
        else:
            self._registry.register(ipt6_capability)
    
    def _scan_fail2ban(self) -> None:
        """Scan fail2ban client, service, and service control capability."""
        from omega_fire.core.capability import create_capability
        from omega_fire.infrastructure.backends.service_manager.detector import ServiceManagerDetector

        # 1. fail2ban-client (command)
        f2b_client_result = self._command_probe.probe_command(
            binary_name="fail2ban-client",
            test_command=["fail2ban-client", "ping"],
        )
        f2b_client_capability = self._mapper.map_command_probe_result(
            capability_id="fail2ban_client",
            probe_result=f2b_client_result,
            category="backend",
        )
        
        if self._registry.is_registered("fail2ban_client"):
            self._registry.update(f2b_client_capability)
        else:
            self._registry.register(f2b_client_capability)
        
        # 2. fail2ban service (état running du daemon)
        f2b_service_result = self._service_probe.probe_service("fail2ban")
        f2b_service_capability = self._mapper.map_service_probe_result(
            capability_id="fail2ban_service",
            probe_result=f2b_service_result,
            category="service",
        )
        
        if self._registry.is_registered("fail2ban_service"):
            self._registry.update(f2b_service_capability)
        else:
            self._registry.register(f2b_service_capability)

        # 3. fail2ban_service_control (contrôle du service réclamé par le menu 4.10)
        detector = ServiceManagerDetector()
        has_service_manager = detector.get_detected_manager() is not None
        has_fail2ban_installed = f2b_client_capability.status != CapabilityStatus.MISSING

        if has_fail2ban_installed and has_service_manager:
            f2b_control_capability = create_capability(
                capability_id="fail2ban_service_control",
                status=CapabilityStatus.AVAILABLE,
                reason="Gestionnaire de service et Fail2ban détectés sur le système",
                category="service",
            )
        else:
            f2b_control_capability = create_capability(
                capability_id="fail2ban_service_control",
                status=CapabilityStatus.MISSING,
                reason="Fail2ban ou le gestionnaire de service est absent",
                category="service",
            )

        if self._registry.is_registered("fail2ban_service_control"):
            self._registry.update(f2b_control_capability)
        else:
            self._registry.register(f2b_control_capability)
    
    def _scan_conntrack(self) -> None:
        """Scan conntrack command."""
        ct_result = self._command_probe.probe_command(
            binary_name="conntrack",
            test_command=["conntrack", "--version"],
        )
        ct_capability = self._mapper.map_command_probe_result(
            capability_id="conntrack",
            probe_result=ct_result,
            category="backend",
        )
        
        if self._registry.is_registered("conntrack"):
            self._registry.update(ct_capability)
        else:
            self._registry.register(ct_capability)
    
    def _scan_service_manager(self) -> None:
        """Scan service manager availability."""
        from omega_fire.infrastructure.backends.service_manager.detector import ServiceManagerDetector
        
        detector = ServiceManagerDetector()
        detected_type = detector.get_detected_manager()
        
        if detected_type is None:
            # No service manager detected
            from omega_fire.core.capability import create_capability
            sm_capability = create_capability(
                capability_id="service_manager",
                status=CapabilityStatus.MISSING,
                reason="No service manager detected on this system",
                category="service",
            )
        else:
            # Service manager detected
            from omega_fire.core.capability import create_capability
            sm_capability = create_capability(
                capability_id="service_manager",
                status=CapabilityStatus.AVAILABLE,
                reason=f"Service manager detected: {detected_type.value}",
                detail={"type": detected_type.value},
                category="service",
            )
        
        if self._registry.is_registered("service_manager"):
            self._registry.update(sm_capability)
        else:
            self._registry.register(sm_capability)
    
    def _load_user_config_capabilities(self) -> int:
        """Load capabilities declared by the user in omega-fire.conf or environment.
        
        Reads the user configuration from AppSettings.user_resources and adds declared
        resources to the registry as capabilities. This allows users to declare custom
        log paths, web servers, monitoring ports, and backends that the automatic
        scanner cannot detect.
        
        Returns:
            Number of user-defined capabilities registered.
        """
        if self._settings is None or not hasattr(self._settings, 'user_resources'):
            return 0
        
        user_resources = self._settings.user_resources
        
        if user_resources.is_empty():
            return 0
        
        from omega_fire.core.capability import create_capability
        from pathlib import Path
        import subprocess
        import socket
        
        registered_count = 0
        
        # 1. Add custom log paths as capabilities
        for log_path in user_resources.extra_log_paths:
            path = Path(log_path)
            cap_id = f"log_custom_{path.stem}"
            
            if path.exists():
                capability = create_capability(
                    capability_id=cap_id,
                    status=CapabilityStatus.AVAILABLE,
                    reason="Déclaré par l'utilisateur (fichier existant)",
                    detail={"path": str(path)},
                    category="log",
                )
            else:
                capability = create_capability(
                    capability_id=cap_id,
                    status=CapabilityStatus.MISSING,
                    reason="Déclaré par l'utilisateur mais fichier introuvable",
                    detail={"path": str(path)},
                    category="log",
                )
            
            if self._registry.is_registered(cap_id):
                self._registry.update(capability)
            else:
                self._registry.register(capability)
            registered_count += 1
        
        # 2. Add custom web servers as capabilities
        for server_name in user_resources.custom_web_servers:
            cap_id = f"web_server_{server_name}"
            try:
                result = subprocess.run(
                    ["pgrep", "-f", server_name],
                    capture_output=True,
                    timeout=2,
                )
                if result.returncode == 0:
                    capability = create_capability(
                        capability_id=cap_id,
                        status=CapabilityStatus.AVAILABLE,
                        reason="Déclaré par l'utilisateur (processus détecté)",
                        detail={"process": server_name},
                        category="web_server",
                    )
                else:
                    capability = create_capability(
                        capability_id=cap_id,
                        status=CapabilityStatus.MISSING,
                        reason="Déclaré par l'utilisateur mais processus non détecté",
                        detail={"process": server_name},
                        category="web_server",
                    )
            except Exception:
                capability = create_capability(
                    capability_id=cap_id,
                    status=CapabilityStatus.MISSING,
                    reason="Déclaré par l'utilisateur (vérification impossible)",
                    detail={"process": server_name},
                    category="web_server",
                )
            
            if self._registry.is_registered(cap_id):
                self._registry.update(capability)
            else:
                self._registry.register(capability)
            registered_count += 1
        
        # 3. Add custom monitoring ports as capabilities
        for port in user_resources.extra_monitoring_ports:
            cap_id = f"monitoring_port_{port}"
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(("127.0.0.1", port))
                sock.close()
                
                if result == 0:
                    capability = create_capability(
                        capability_id=cap_id,
                        status=CapabilityStatus.AVAILABLE,
                        reason=f"Déclaré par l'utilisateur (port {port} ouvert)",
                        detail={"port": port},
                        category="monitoring",
                    )
                else:
                    capability = create_capability(
                        capability_id=cap_id,
                        status=CapabilityStatus.MISSING,
                        reason=f"Déclaré par l'utilisateur mais port {port} fermé",
                        detail={"port": port},
                        category="monitoring",
                    )
            except Exception:
                capability = create_capability(
                    capability_id=cap_id,
                    status=CapabilityStatus.MISSING,
                    reason=f"Déclaré par l'utilisateur (vérification impossible)",
                    detail={"port": port},
                    category="monitoring",
                )
            
            if self._registry.is_registered(cap_id):
                self._registry.update(capability)
            else:
                self._registry.register(capability)
            registered_count += 1
        
        return registered_count
    
    def rescan(self) -> dict:
        """Clear the registry and run a fresh scan.
        
        Returns:
            Dictionary with scan results
        """
        self._registry.clear()
        return self.scan()
    
    def get_registry_summary(self) -> dict:
        """Get a summary of the current registry state.
        
        Returns:
            Dictionary with registry summary
        """
        return self._registry.get_summary()


def scan_system(registry: CapabilityRegistry, settings: Optional[Any] = None) -> dict:
    """Convenience function to scan the system and populate the registry.
    
    Args:
        registry: The capability registry to populate
        settings: Optional AppSettings instance for user-defined resources
    
    Returns:
        Dictionary with scan results
    """
    scanner = SystemScanner(registry, settings)
    return scanner.scan()


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Orchestre tous les probes système et peuple le registre de capacités
# - Coordonne les probes de commandes, services et noyau
# - Charge les ressources déclarées par l'utilisateur (logs, serveurs, ports)
# - Point d'entrée pour la détection système au démarrage de l'application
# - Retourne un résumé du scan (nombre de capacités par statut, erreurs)
#
# Pourquoi dans infrastructure/ (charte) :
# - C'est l'orchestrateur technique qui lance les probes réels
# - Utilise les autres modules d'infrastructure (command_probe, service_probe, etc.)
# - Peuple le registre de capacités (core/) avec des résultats concrets
# - Aucun autre module ne doit recoder cette orchestration (clause omega-fire)
#
# Ce qu'il ne contient PAS :
# ❌ Pas de logique métier (pas de règles firewall/fail2ban)
# ❌ Pas de dépendance vers domain/ ou interfaces/
# ❌ Pas d'appels directs aux backends (passe par les probes)
#
# Points clés :
# - SystemScanner : classe principale qui prend registry + settings optionnel
# - scan() : méthode principale qui lance tous les probes + user config
#   - _scan_backends() : teste nftables, iptables et ip6tables
#   - _scan_fail2ban() : teste fail2ban_client et fail2ban_service
#   - _scan_conntrack() : teste conntrack
#   - _scan_service_manager() : détecte le gestionnaire de services
#   - _load_user_config_capabilities() : charge les ressources utilisateur (NOUVEAU)
# - Retourne un dict avec :
#   - capabilities_registered : nombre total de capacités enregistrées
#   - capabilities_available/degraded/missing/disqualified : compteurs par statut
#   - errors : liste des erreurs rencontrées
# - rescan() : efface le registre et relance un scan complet
# - get_registry_summary() : retourne un résumé de l'état du registre
# - Gestion des erreurs : capture les exceptions de chaque scan et les ajoute à la liste
#   sans interrompre le scan global
# - Fonctions de convenance : scan_system(registry, settings)
# - Enregistre ou met à jour les capacités dans le registre (register() ou update())
# - _scan_known_services() : teste ~50 services connus (system_services,
#     servers, bureau_distant, security_network) via pgrep, liste définie
#     dans infrastructure/probe/known_services.py
#
# Ressources utilisateur supportées :
# - extra_log_paths : chemins de fichiers de log personnalisés
# - custom_web_servers : noms de processus de serveurs web
# - extra_monitoring_ports : ports TCP à surveiller
#
# Comment il sera utilisé (aperçu) :
# - app/bootstrap.py l'appellera au démarrage avec settings pour peupler le registre
# - interfaces/cli/actions.py proposera un menu "Re-scanner le système" (1.3)
# - interfaces/cli/renderers/capability_view.py consultera le registre pour afficher l'état
# - Les tests mockeront les probes pour simuler différents scénarios système
#---------------------------------------------------------------------->
