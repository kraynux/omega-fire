# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Shared request DTOs for the application layer.

These dataclasses represent validated input payloads that cross
multiple use cases. They are NOT tied to a single command.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class BackendTarget(str, Enum):
    """Target backend for firewall operations."""
    NFTABLES = "nftables"
    IPTABLES = "iptables"
    FAIL2BAN = "fail2ban"
    ALL = "all"


class ExportFormat(str, Enum):
    """Supported export formats."""
    JSON = "json"
    TXT = "txt"
    HTML = "html"
    CSV = "csv"


class SyncDirection(str, Enum):
    """Direction of backend synchronization."""
    NFTABLES_TO_IPTABLES = "nftables_to_iptables"
    IPTABLES_TO_NFTABLES = "iptables_to_nftables"
    NFTABLES_TO_FAIL2BAN = "nftables_to_fail2ban"
    IPTABLES_TO_FAIL2BAN = "iptables_to_fail2ban"


@dataclass(slots=True)
class IPAddressInput:
    """Validated IP address input shared across ban/unban/sync use cases."""
    ip: str
    backend: BackendTarget = BackendTarget.NFTABLES
    comment: str = ""

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.ip:
            errors.append("IP address is required")
        elif not self._is_valid_ipv4(self.ip):
            errors.append(f"Invalid IPv4 format: {self.ip}")
        return errors

    def is_valid(self) -> bool:
        return len(self.validate()) == 0

    @staticmethod
    def _is_valid_ipv4(ip: str) -> bool:
        parts = ip.split(".")
        if len(parts) != 4:
            return False
        try:
            return all(0 <= int(p) <= 255 for p in parts)
        except ValueError:
            return False


@dataclass(slots=True)
class IPListInput:
    """Validated list of IP addresses for bulk operations."""
    ips: list[str] = field(default_factory=list)
    backend: BackendTarget = BackendTarget.NFTABLES
    source_file: Optional[str] = None

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.ips and not self.source_file:
            errors.append("Either ips list or source_file is required")
        for ip in self.ips:
            if not IPAddressInput._is_valid_ipv4(ip):
                errors.append(f"Invalid IPv4 in list: {ip}")
        return errors

    def is_valid(self) -> bool:
        return len(self.validate()) == 0


@dataclass(slots=True)
class RuleInput:
    """Validated rule parameters for create/delete rule use cases."""
    source_ip: str = ""
    target: BackendTarget = BackendTarget.NFTABLES
    action: str = "deny"
    port: Optional[int] = None
    protocol: Optional[str] = None
    comment: Optional[str] = None
    rule_id: Optional[str] = None

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.port is not None and (self.port < 1 or self.port > 65535):
            errors.append(f"Invalid port: {self.port}")
        if self.protocol and self.protocol not in ("tcp", "udp", "icmp", "all"):
            errors.append(f"Invalid protocol: {self.protocol}")
        if self.action not in ("accept", "deny", "drop", "reject"):
            errors.append(f"Invalid action: {self.action}")
        return errors

    def is_valid(self) -> bool:
        return len(self.validate()) == 0


@dataclass(slots=True)
class JailInput:
    """Validated jail parameters for fail2ban operations."""
    jail_name: str = ""
    ip_address: str = ""
    reason: Optional[str] = None
    duration_seconds: Optional[int] = None

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.jail_name:
            errors.append("Jail name is required")
        if not self.ip_address:
            errors.append("IP address is required")
        if self.duration_seconds is not None and self.duration_seconds < 0:
            errors.append("Duration must be non-negative")
        return errors

    def is_valid(self) -> bool:
        return len(self.validate()) == 0


@dataclass(slots=True)
class ExportInput:
    """Validated export parameters shared across export use cases."""
    report_name: str = ""
    format: ExportFormat = ExportFormat.JSON
    destination: Optional[str] = None
    include_metadata: bool = True

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.report_name:
            errors.append("Report name is required")
        return errors

    def is_valid(self) -> bool:
        return len(self.validate()) == 0


@dataclass(slots=True)
class MaintenanceInput:
    """Validated parameters for maintenance operations (backup, rotate, reload)."""
    target: str = "all"
    compress: bool = True
    keep: int = 7
    force: bool = False
    reason: Optional[str] = None
    scope: str = "all"
    destination: Optional[str] = None

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.keep < 1:
            errors.append("Keep must be at least 1")
        return errors

    def is_valid(self) -> bool:
        return len(self.validate()) == 0

# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - DTOs de requête partagés entre plusieurs cas d'usage applicatifs
# - Centralise la validation des entrées utilisateur
# - Utilisé par les commands pour construire leurs Request internes
#
# Pourquoi dans application/dto/ (charte) :
# - Ce sont des objets de transfert de données entre couches
# - Pas de logique métier (domain/)
# - Pas d'I/O (infrastructure/)
# - Pas de rendu (interfaces/)
#
# Ce qu'il ne contient PAS :
# ❌ Pas d'import depuis infrastructure/
# ❌ Pas d'import depuis interfaces/
# ❌ Pas de subprocess, sqlite3, rich
# ❌ Pas de logique métier complexe
#
# Points clés :
# - BackendTarget, ExportFormat, SyncDirection : enums partagées
# - IPAddressInput : validation IPv4 pour ban/unban
# - IPListInput : validation liste d'IPs pour opérations bulk
# - RuleInput : paramètres de création/suppression de règle
# - JailInput : paramètres fail2ban
# - ExportInput : paramètres d'export
# - MaintenanceInput : paramètres de maintenance (backup, rotate, reload)
# - Tous les DTOs ont validate() -> list[str] et is_valid() -> bool
#---------------------------------------------------------------------->
