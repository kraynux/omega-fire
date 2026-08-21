# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Fail2ban report assembly (menu 6.4): orchestrates all section
collectors into a single F2bReportData.

Pure query orchestration — never writes anything. Writing the file and
any audit trail entry is the responsibility of the caller
(application/commands/export_f2b_report.py).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from omega_fire.application.queries.f2b_report.models import F2bReportData
from omega_fire.application.queries.f2b_report.system_section import (
    collect_system_status,
)
from omega_fire.application.queries.f2b_report.jails_section import (
    collect_jails_detail,
)
from omega_fire.application.queries.f2b_report.duplicates_section import (
    collect_duplicate_ips,
)


def build_f2b_report(
    fail2ban_adapter: Any,
    service_controller: Any,
    history_reader: Any,
) -> F2bReportData:
    """Assemble the complete fail2ban detail report (menu 6.4).

    Args:
        fail2ban_adapter: Fail2banAdapter instance.
        service_controller: Fail2banServiceController instance.
        history_reader: Fail2banHistoryReader instance.

    Returns:
        Fully assembled F2bReportData, ready for export (TXT/HTML).
    """
    system = collect_system_status(fail2ban_adapter, service_controller)

    # Un seul appel list_jails_info() (bulk SQLite + disque, ~pas de
    # fail2ban-client par jail dans le cas nominal) partagé entre les
    # deux collecteurs suivants — auparavant chacun refaisait sa propre
    # boucle get_jail_status()/get_jail_config() par jail (2026-08-16,
    # cf. notes perf de jails_section.py/duplicates_section.py).
    try:
        jails_info = fail2ban_adapter.list_jails_info() if fail2ban_adapter is not None else []
    except Exception:
        jails_info = []

    jails = collect_jails_detail(fail2ban_adapter, jails_info, history_reader)
    duplicates = collect_duplicate_ips(jails_info)

    return F2bReportData(
        generated_at=datetime.now(),
        system=system,
        total_jails=len(jails),
        jails=jails,
        duplicate_ips=duplicates,
    )


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Point d'entrée unique du rapport détaillé fail2ban (menu 6.4) :
#   orchestre system_section.py, jails_section.py,
#   duplicates_section.py et assemble un F2bReportData complet.
#
# Pourquoi dans application/queries/f2b_report/ (charte) :
# - Reste une query pure malgré son rôle d'orchestrateur.
#
# Comment il sera utilisé :
# - application/commands/export_f2b_report.py appelle
#   build_f2b_report(), passe le résultat aux exporters TXT/HTML.
#----------------------------------------------------------------------
