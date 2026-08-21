# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Fail2ban system status collection (menu 6.4).

Reuses Fail2banServiceController (already used by menu 4.10) rather
than re-implementing service manager detection.
"""
from __future__ import annotations

from typing import Any

from omega_fire.application.queries.f2b_report.models import SystemStatus


def collect_system_status(
    fail2ban_adapter: Any,
    service_controller: Any,
) -> SystemStatus:
    """Collect fail2ban's system-level status: installed, running,
    enabled at boot.

    Args:
        fail2ban_adapter: Fail2banAdapter instance, used to check if
            fail2ban-client responds at all ("installed").
        service_controller: Fail2banServiceController instance
            (infrastructure/backends/fail2ban/service_controller.py),
            reused from menu 4.10 rather than duplicating service
            manager detection logic.

    Returns:
        SystemStatus. enabled_at_boot is None if it could not be
        determined (e.g. no service manager detected on this system).
    """
    installed = False
    if fail2ban_adapter is not None:
        try:
            installed = fail2ban_adapter.is_available()
        except Exception:
            installed = False

    service_running = False
    enabled_at_boot: bool | None = None

    if service_controller is not None:
        try:
            service_running = service_controller.is_active()
        except Exception:
            service_running = False

        try:
            enabled_at_boot = service_controller.is_enabled()
        except Exception:
            enabled_at_boot = None

    return SystemStatus(
        installed=installed,
        service_running=service_running,
        enabled_at_boot=enabled_at_boot,
    )


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Collecte l'état système de fail2ban (installé, actif, activé au
#   démarrage) pour la section système du rapport 6.4.
#
# Pourquoi dans application/queries/f2b_report/ (charte) :
# - Lecture seule, réutilise Fail2banServiceController existant
#   (menu 4.10) plutôt que de dupliquer la détection systemd/
#   openrc/runit.
#
# Points clés :
# - enabled_at_boot: bool | None — None signifie "impossible à
#   déterminer" (pas de service manager détecté sur ce système),
#   distinct de False ("détecté mais désactivé au démarrage").
#
# Comment il sera utilisé :
# - report_builder.py (application/queries/f2b_report/report_builder.py)
#   appelle cette fonction pour peupler F2bReportData.system.
#----------------------------------------------------------------------
