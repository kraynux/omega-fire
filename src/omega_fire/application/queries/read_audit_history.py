# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Read audit history query.

Read-only access to the audit trail (menu 7.3), backed by AuditPort.
Distinct from application/queries/app_log.py (menu 1.5's narrative
application log, unrelated file/format) — audit entries are always
structured (AuditEntry objects), never a pre-formatted string, so the
caller (interfaces/cli/actions.py) can build a proper Rich table
instead of printing raw text.

Conforms to Omega-Fire architecture charter:
- Read-only query, no side effects
- Consumes ports/audit.py contract (AuditPort), never
  infrastructure/logging/ directly
- No dependency on interfaces/ or infrastructure/ directly
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from omega_fire.ports.audit import AuditEntry


@dataclass
class ReadAuditHistoryRequest:
    """Input for the read-audit-history use case."""
    limit: int = 500
    keyword: str = ""


@dataclass
class ReadAuditHistoryResult:
    """Output of the read-audit-history use case."""
    success: bool
    entries: list[AuditEntry] = field(default_factory=list)
    message: str = ""


class ReadAuditHistoryQuery:
    """Use case: read the audit trail, optionally filtered by keyword."""

    def __init__(self, audit_port: Optional[Any]):
        self._audit_port = audit_port

    def execute(self, request: ReadAuditHistoryRequest) -> ReadAuditHistoryResult:
        if self._audit_port is None:
            return ReadAuditHistoryResult(
                success=False, entries=[], message="Le registre d'audit n'est pas disponible."
            )

        try:
            entries = self._audit_port.get_recent(limit=request.limit)
        except Exception as e:
            return ReadAuditHistoryResult(
                success=False, entries=[], message=f"Erreur lors de la lecture de l'audit : {e}"
            )

        if request.keyword:
            kw = request.keyword.lower()
            entries = [
                e for e in entries
                if kw in e.action.lower()
                or kw in e.actor.lower()
                or kw in (e.target or "").lower()
            ]

        return ReadAuditHistoryResult(success=True, entries=entries)


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Query read-only pour l'historique d'audit (menu 7.3), distincte du
#   journal applicatif narratif (menu 1.5, application/queries/app_log.py).
# - Retourne des AuditEntry structurées (jamais une string pré-formatée) :
#   c'est à interfaces/cli/actions.py de construire l'affichage Rich.
#
# Pourquoi dans application/queries/ (charte) :
# - Lecture seule, aucun effet de bord.
# - Consomme AuditPort (ports/), jamais AuditLogger (infrastructure/)
#   directement.
#
# Ce qu'il ne contient PAS :
# ❌ Pas d'import de infrastructure/logging/ (audit_port reçu en paramètre)
# ❌ Pas de rendu UI, pas de formatage de présentation
# ❌ Pas de logique de suppression (voir menu 7.3, options de purge,
#   qui appellent directement audit_port.clear()/delete_oldest())
#
# Points clés :
# - ReadAuditHistoryRequest : limit (défaut 500, cohérent avec la
#   pagination en mémoire prévue côté actions.py) + keyword optionnel
# - Filtrage par mot-clé sur action/actor/target, appliqué APRÈS
#   get_recent() — cohérent avec le filtrage déjà fait par le code mort
#   de read_app_log() qu'elle remplace pour ce menu
# - ReadAuditHistoryResult.entries : liste d'AuditEntry (ports/audit.py),
#   jamais de string
#
# Flux d'exécution :
# interfaces/cli/actions.py : action_7_3_action_history(ctx)
#   ↓ résout audit_port via ctx.container.get_audit_port()
# application/queries/read_audit_history.py : ReadAuditHistoryQuery.execute()
#   ↓ audit_port.get_recent(limit) (infrastructure/logging/audit_logger.py)
#---------------------------------------------------------------------->
