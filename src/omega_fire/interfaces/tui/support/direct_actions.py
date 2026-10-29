# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Actions sans formulaire ni confirmation — declenchees directement
depuis un bouton de SectionScreen, sans ecran dedie (meme esprit que
interfaces/cli/actions.py::action_7_4_reload_config : aucun champ a
remplir, juste executer et rapporter le resultat)."""
from __future__ import annotations

import time
from typing import Any, Callable

from omega_fire.shared.i18n import _

# Demarrer / arreter / redemarrer change l'etat lu par le registre des capacites (et donc
# le tableau de bord) : retour utilisateur 2026-10-28, fail2ban demarre restait « inactif »
# au tableau de bord jusqu'au prochain 1.3. On attend que le serveur reponde (ou plus)
# a `fail2ban-client ping`, puis on re-scanne.
_STATE_CHANGING = {"start_service": True, "restart_service": True, "stop_service": False}
_READY_TIMEOUT = 15.0
_READY_POLL = 0.5


def rescan_system(container: Any) -> tuple[bool, str]:
    """1.3 — Re-scanner le systeme (nftables, iptables, fail2ban, systemd),
    peuple directement le registre associe au scanner."""
    try:
        scanner = getattr(container, "scanner", None)
        if scanner is None:
            return False, _("Impossible de récupérer la sonde 'CapabilityScanner' depuis le conteneur.")
        scan_results = scanner.scan()
        registered = scan_results.get("capabilities_registered", 0)
        available = scan_results.get("capabilities_available", 0)
        degraded = scan_results.get("capabilities_degraded", 0)
        missing = scan_results.get("capabilities_missing", 0)
        disqualified = scan_results.get("capabilities_disqualified", 0)
        scan_errors = scan_results.get("errors", [])

        message = (
            _("Scan effectué : {registered} sonde(s) analysée(s) — {available} disponible(s), {degraded} dégradée(s), {missing} manquante(s), {disqualified} disqualifiée(s).").format(registered=registered, available=available, degraded=degraded, missing=missing, disqualified=disqualified)
        )
        if scan_errors:
            message += _(" {count} erreur(s) partielle(s).").format(count=len(scan_errors))
        return True, message
    except Exception as e:
        return False, _("Échec lors du rescan : {e}").format(e=e)


def _fail2ban_port(container: Any) -> Any:
    try:
        return container.get_fail2ban_port()
    except Exception:
        return None


def fail2ban_service_status(container: Any) -> tuple[bool, str]:
    """4.10[1] — Verifier le statut du service Fail2ban & persistance."""
    port = _fail2ban_port(container)
    if port is None:
        return False, _("Port Fail2ban indisponible (conteneur non initialisé).")
    active = _("ACTIF") if port.is_service_active() else _("INACTIF")
    enabled = _("ACTIVÉE") if port.is_service_enabled() else _("NON ACTIVÉE")
    return True, _("Service Fail2ban {active} — persistance au démarrage {enabled}.").format(active=active, enabled=enabled)


def fail2ban_service_start(container: Any) -> tuple[bool, str]:
    """4.10[2] — Demarrer le service Fail2ban."""
    return _run_fail2ban_service_op(container, "start_service", _("démarré"))


def fail2ban_service_stop(container: Any) -> tuple[bool, str]:
    """4.10[3] — Stopper le service Fail2ban (confirmation demandee par SectionItem)."""
    return _run_fail2ban_service_op(container, "stop_service", _("arrêté"))


def fail2ban_service_restart(container: Any) -> tuple[bool, str]:
    """4.10[4] — Redemarrer le service Fail2ban (confirmation demandee par SectionItem)."""
    return _run_fail2ban_service_op(container, "restart_service", _("redémarré"))


def fail2ban_service_enable(container: Any) -> tuple[bool, str]:
    """4.10[5] — Activer le service Fail2ban au demarrage systeme."""
    return _run_fail2ban_service_op(container, "enable_service", _("active au démarrage du système"))


def fail2ban_service_disable(container: Any) -> tuple[bool, str]:
    """4.10[6] — Desactiver le service Fail2ban au demarrage systeme."""
    return _run_fail2ban_service_op(container, "disable_service", _("désactivé du démarrage du système"))


def _run_fail2ban_service_op(container: Any, method_name: str, label: str) -> tuple[bool, str]:
    port = _fail2ban_port(container)
    if port is None:
        return False, _("Port Fail2ban indisponible (conteneur non initialisé).")
    try:
        getattr(port, method_name)()
    except Exception as e:
        return False, _("Échec de la commande de service : {e}").format(e=e)
    message = _("Service Fail2ban {label} avec succès.").format(label=label)
    if method_name in _STATE_CHANGING:
        message += " " + _refresh_registry_after(container, port, expect_up=_STATE_CHANGING[method_name])
    return True, message


def wait_for_fail2ban(port: Any, expect_up: bool, timeout: float = _READY_TIMEOUT,
                      poll: float = _READY_POLL, sleep: Callable[[float], None] = time.sleep,
                      clock: Callable[[], float] = time.monotonic) -> bool:
    """Attend que `fail2ban-client ping` reponde (expect_up) ou plus (arret). Le service
    systemd est « actif » avant que le serveur ait ouvert sa socket."""
    deadline = clock() + timeout
    while True:
        try:
            up = bool(port.is_available())
        except Exception:
            up = False
        if up == expect_up:
            return True
        if clock() >= deadline:
            return False
        sleep(poll)


def _refresh_registry_after(container: Any, port: Any, *, expect_up: bool) -> str:
    ready = wait_for_fail2ban(port, expect_up)
    scanner = getattr(container, "scanner", None)
    if scanner is None:
        return _("Registre des capacités non mis à jour : relancez 1.3.")
    try:
        scanner.scan()
    except Exception as e:
        return _("Registre des capacités non mis à jour ({e}) : relancez 1.3.").format(e=e)
    if not ready:
        return _("Registre des capacités mis à jour, mais Fail2ban ne répondait pas encore : "
                 "relancez 1.3 dans quelques secondes.")
    return _("Registre des capacités et tableau de bord mis à jour.")


def reload_config(container: Any) -> tuple[bool, str]:
    """7.4 — Recharger la configuration (re-scan systeme complet, meme
    mecanisme que 1.3 : SystemScanner.scan() via container.scanner)."""
    try:
        scanner = getattr(container, "scanner", None)
        if scanner is None:
            return False, _("Impossible de récupérer la sonde système depuis le conteneur.")
        scan_results = scanner.scan()
        scan_errors = scan_results.get("errors", []) if isinstance(scan_results, dict) else []
        if scan_errors:
            return True, _("Configuration rechargée avec {count} avertissement(s).").format(count=len(scan_errors))
        return True, _("Configuration rechargée.")
    except Exception as e:
        return False, _("Échec du rechargement : {e}").format(e=e)
