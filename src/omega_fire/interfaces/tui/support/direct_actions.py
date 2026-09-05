# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Actions sans formulaire ni confirmation — declenchees directement
depuis un bouton de SectionScreen, sans ecran dedie (meme esprit que
interfaces/cli/actions.py::action_7_4_reload_config : aucun champ a
remplir, juste executer et rapporter le resultat)."""
from __future__ import annotations

from typing import Any


def rescan_system(container: Any) -> tuple[bool, str]:
    """1.3 — Re-scanner le systeme (nftables, iptables, fail2ban, systemd),
    peuple directement le registre associe au scanner."""
    try:
        scanner = getattr(container, "scanner", None)
        if scanner is None:
            return False, "Impossible de recuperer la sonde 'CapabilityScanner' depuis le conteneur."
        scan_results = scanner.scan()
        registered = scan_results.get("capabilities_registered", 0)
        available = scan_results.get("capabilities_available", 0)
        degraded = scan_results.get("capabilities_degraded", 0)
        missing = scan_results.get("capabilities_missing", 0)
        disqualified = scan_results.get("capabilities_disqualified", 0)
        scan_errors = scan_results.get("errors", [])

        message = (
            f"Scan effectue : {registered} sonde(s) analysee(s) — "
            f"{available} disponible(s), {degraded} degradee(s), "
            f"{missing} manquante(s), {disqualified} disqualifiee(s)."
        )
        if scan_errors:
            message += f" {len(scan_errors)} erreur(s) partielle(s)."
        return True, message
    except Exception as e:
        return False, f"Echec lors du rescan : {e}"


def _fail2ban_port(container: Any) -> Any:
    try:
        return container.get_fail2ban_port()
    except Exception:
        return None


def fail2ban_service_status(container: Any) -> tuple[bool, str]:
    """4.10[1] — Verifier le statut du service Fail2ban & persistance."""
    port = _fail2ban_port(container)
    if port is None:
        return False, "Port Fail2ban indisponible (conteneur non initialise)."
    active = "ACTIF" if port.is_service_active() else "INACTIF"
    enabled = "ACTIVEE" if port.is_service_enabled() else "NON ACTIVEE"
    return True, f"Service Fail2ban {active} — persistance au demarrage {enabled}."


def fail2ban_service_start(container: Any) -> tuple[bool, str]:
    """4.10[2] — Demarrer le service Fail2ban."""
    return _run_fail2ban_service_op(container, "start_service", "demarre")


def fail2ban_service_stop(container: Any) -> tuple[bool, str]:
    """4.10[3] — Stopper le service Fail2ban (confirmation demandee par SectionItem)."""
    return _run_fail2ban_service_op(container, "stop_service", "arrete")


def fail2ban_service_restart(container: Any) -> tuple[bool, str]:
    """4.10[4] — Redemarrer le service Fail2ban (confirmation demandee par SectionItem)."""
    return _run_fail2ban_service_op(container, "restart_service", "redemarre")


def fail2ban_service_enable(container: Any) -> tuple[bool, str]:
    """4.10[5] — Activer le service Fail2ban au demarrage systeme."""
    return _run_fail2ban_service_op(container, "enable_service", "active au demarrage du systeme")


def fail2ban_service_disable(container: Any) -> tuple[bool, str]:
    """4.10[6] — Desactiver le service Fail2ban au demarrage systeme."""
    return _run_fail2ban_service_op(container, "disable_service", "desactive du demarrage du systeme")


def _run_fail2ban_service_op(container: Any, method_name: str, label: str) -> tuple[bool, str]:
    port = _fail2ban_port(container)
    if port is None:
        return False, "Port Fail2ban indisponible (conteneur non initialise)."
    try:
        getattr(port, method_name)()
        return True, f"Service Fail2ban {label} avec succes."
    except Exception as e:
        return False, f"Echec de la commande de service : {e}"


def reload_config(container: Any) -> tuple[bool, str]:
    """7.4 — Recharger la configuration (re-scan systeme complet, meme
    mecanisme que 1.3 : SystemScanner.scan() via container.scanner)."""
    try:
        scanner = getattr(container, "scanner", None)
        if scanner is None:
            return False, "Impossible de recuperer la sonde systeme depuis le conteneur."
        scan_results = scanner.scan()
        scan_errors = scan_results.get("errors", []) if isinstance(scan_results, dict) else []
        if scan_errors:
            return True, f"Configuration rechargee avec {len(scan_errors)} avertissement(s)."
        return True, "Configuration rechargee."
    except Exception as e:
        return False, f"Echec du rechargement : {e}"
