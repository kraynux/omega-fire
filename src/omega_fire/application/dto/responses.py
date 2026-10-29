# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Shared response DTOs for the application layer.

These dataclasses represent structured results returned by use cases.
They are consumed by interfaces/ for rendering.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional
from omega_fire.shared.i18n import _


@dataclass(slots=True)
class CommandResponse:
    """Generic response for any command execution."""
    success: bool
    command_name: str = ""
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def is_success(self) -> bool:
        return self.success

    def to_display(self) -> str:
        if self.success:
            return f"✅ {self.message}"
        return f"❌ {self.error or self.message}"


@dataclass(slots=True)
class PlanResponse:
    """Response wrapping an ExecutionPlan result."""
    success: bool
    command_name: str = ""
    executed_steps: list[str] = field(default_factory=list)
    skipped_steps: list[str] = field(default_factory=list)
    failed_step: Optional[str] = None
    error_message: Optional[str] = None
    degraded_mode: bool = False
    duration_seconds: float = 0.0

    def to_display(self) -> str:
        lines: list[str] = []
        if self.success:
            lines.append(_("✅ {command_name} exécuté avec succès").format(command_name=self.command_name))
        else:
            lines.append(_("❌ {command_name} échoué").format(command_name=self.command_name))
        if self.executed_steps:
            lines.append(_("   Steps exécutés : {value}").format(value=', '.join(self.executed_steps)))
        if self.skipped_steps:
            lines.append(_("   Steps ignorés : {value}").format(value=', '.join(self.skipped_steps)))
        if self.failed_step:
            lines.append(_("   Step en erreur : {failed_step}").format(failed_step=self.failed_step))
        if self.error_message:
            lines.append(_("   Erreur : {error_message}").format(error_message=self.error_message))
        if self.degraded_mode:
            lines.append(_("   ⚠️ Mode dégradé actif"))
        return "\n".join(lines)


@dataclass(slots=True)
class QueryResponse:
    """Generic response for any query execution."""
    success: bool
    data: Any = None
    message: str = ""
    error: Optional[str] = None
    count: int = 0

    def to_display(self) -> str:
        if self.success:
            return self.message
        return f"❌ {self.error or self.message}"


@dataclass(slots=True)
class BanOperationResponse:
    """Specific response for ban/unban operations."""
    success: bool
    ip: str = ""
    backend: str = ""
    action: str = ""  # "ban" or "unban"
    message: str = ""
    already_exists: bool = False

    def to_display(self) -> str:
        if self.already_exists:
            return _("⚠️ {ip} est déjà {value}").format(ip=self.ip, value=_('bannie') if self.action == 'ban' else _('débannie'))
        if self.success:
            symbol = "🚫" if self.action == "ban" else "✅"
            return _("{symbol} {ip} {action} sur {backend}").format(symbol=symbol, ip=self.ip, action=self.action, backend=self.backend)
        return _("❌ Échec du {action} de {ip} : {message}").format(action=self.action, ip=self.ip, message=self.message)


@dataclass(slots=True)
class SyncOperationResponse:
    """Specific response for backend sync operations."""
    success: bool
    direction: str = ""
    source: str = ""
    destination: str = ""
    ips_synced: int = 0
    dry_run: bool = False
    message: str = ""

    def to_display(self) -> str:
        prefix = "🔍 [DRY RUN] " if self.dry_run else ""
        if self.success:
            return _("{prefix}✅ Sync {source} → {destination} : {ips_synced} IPs").format(prefix=prefix, source=self.source, destination=self.destination, ips_synced=self.ips_synced)
        return _("❌ Échec sync : {message}").format(message=self.message)


@dataclass(slots=True)
class ValidationResponse:
    """Response for request validation results."""
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_display(self) -> str:
        if self.is_valid:
            return _("✅ Validation réussie")
        lines = [_("❌ Erreurs de validation :")]
        for err in self.errors:
            lines.append(f"   • {err}")
        for warn in self.warnings:
            lines.append(f"   ⚠️ {warn}")
        return "\n".join(lines)

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - DTOs de réponse partagés entre plusieurs cas d'usage applicatifs
# - Structure les résultats pour consommation par interfaces/
# - Chaque DTO a une méthode to_display() pour le rendu texte
#
# Pourquoi dans application/dto/ (charte) :
# - Objets de transfert entre application/ et interfaces/
# - Pas de logique métier
# - Pas d'I/O
# - Pas de rendu Rich (juste du texte brut)
#
# Ce qu'il ne contient PAS :
# ❌ Pas d'import depuis infrastructure/
# ❌ Pas d'import depuis interfaces/
# ❌ Pas de Rich, subprocess, sqlite3
#
# Points clés :
# - CommandResponse : réponse générique pour toute commande
# - PlanResponse : réponse spécifique aux ExecutionPlan
# - QueryResponse : réponse générique pour toute query
# - BanOperationResponse : réponse spécifique ban/unban
# - SyncOperationResponse : réponse spécifique sync
# - ValidationResponse : réponse de validation
# - to_display() : retourne une string formatée pour l'UI
#---------------------------------------------------------------------->
