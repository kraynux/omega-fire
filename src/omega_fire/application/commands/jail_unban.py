# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Jail unban command.

Unbans an IP address from a specific fail2ban jail. Direct call to the
adapter via Fail2banPort — same rationale as jail_ban.py.

Conforms to Omega-Fire architecture charter:
- No direct subprocess calls (delegates entirely to the fail2ban
  adapter, received already resolved by the caller)
- No import of infrastructure/backends/ concrete classes
"""
from dataclasses import dataclass
from typing import Any, Optional

from omega_fire.domain.fail2ban.exceptions import (
    JailNotFoundError,
    IPNotFoundError,
)
from omega_fire.shared.networking import IPAddress


@dataclass
class JailUnbanRequest:
    """Input for the jail unban use case."""
    jail_name: str
    ip: str


@dataclass
class JailUnbanResult:
    """Output of the jail unban use case."""
    success: bool
    message: str = ""


class JailUnbanCommand:
    """Use case: unban an IP from a specific fail2ban jail."""

    def __init__(self, fail2ban_port: Optional[Any]):
        self._port = fail2ban_port

    def execute(self, request: JailUnbanRequest) -> JailUnbanResult:
        if self._port is None:
            return JailUnbanResult(success=False, message="Fail2ban indisponible.")

        try:
            ip = IPAddress(request.ip)
        except ValueError as e:
            return JailUnbanResult(success=False, message=f"Adresse IP invalide : {e}")

        try:
            self._port.unban_ip(request.jail_name, ip)
        except IPNotFoundError:
            return JailUnbanResult(
                success=False,
                message=f"IP {request.ip} absente des bannis de '{request.jail_name}'.",
            )
        except JailNotFoundError:
            return JailUnbanResult(success=False, message=f"Jail '{request.jail_name}' introuvable.")
        except Exception as e:
            return JailUnbanResult(success=False, message=str(e))

        return JailUnbanResult(success=True, message=f"IP {request.ip} débannie de '{request.jail_name}'.")


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Débannit une IP d'un jail fail2ban spécifique (menu 4.2).
#
# Pourquoi dans application/commands/ (charte) :
# - Orchestration simple : délègue entièrement à Fail2banPort
#   (infrastructure/backends/fail2ban/adapter.py::unban_ip()), traduit
#   ses exceptions métier en JailUnbanResult.
#
# Ce qu'il ne contient PAS :
# ❌ Pas d'import de infrastructure/backends/ (port reçu en paramètre)
# ❌ Pas de pattern ExecutionPlan/PipelineStep (abandonné, même
#    rationale que jail_ban.py)
#
# Points clés :
# - JailUnbanRequest : jail_name + ip (str)
# - Appelle fail2ban_port.unban_ip(jail_name, IPAddress) — méthode
#   conforme à Fail2banPort (lève des exceptions), PAS
#   unban_ip_in_jail() (ancienne méthode bool, laissée intacte sur
#   l'adaptateur mais plus appelée d'ici). Même correctif de
#   comportement que jail_ban.py (2026-08-13) :
#   unban_ip_in_jail() retournait toujours True sans vérifier la
#   réponse de fail2ban-client — débannir une IP absente rapportait un
#   faux succès. unban_ip() lève IPNotFoundError dans ce cas, traduite
#   ici en JailUnbanResult(success=False, ...).
# - Construit IPAddress(request.ip) avant l'appel — une IP malformée
#   échoue ici avec un message clair plutôt que de remonter jusqu'au
#   port.
#
# Flux d'exécution :
# interfaces/cli/actions.py : action_4_2_jail_ban_unban(ctx)
# application/commands/jail_unban.py : JailUnbanCommand.execute()
#   ↓ fail2ban_port.unban_ip() (infrastructure/backends/fail2ban/adapter.py)
#---------------------------------------------------------------------->
