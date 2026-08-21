# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Jail ban command.

Bans an IP address in a specific fail2ban jail. Direct call to the
adapter via Fail2banPort — no ExecutionPlan/PipelineStep (abandoned
pattern in this project, incompatible with parameterized steps, see
application/commands/ban_ip.py for the same architectural decision).

Conforms to Omega-Fire architecture charter:
- No direct subprocess calls (delegates entirely to the fail2ban
  adapter, received already resolved by the caller)
- No import of infrastructure/backends/ concrete classes
"""
from dataclasses import dataclass
from typing import Any, Optional

from omega_fire.domain.fail2ban.exceptions import (
    JailNotFoundError,
    IPAlreadyBannedError,
)
from omega_fire.shared.networking import IPAddress


@dataclass
class JailBanRequest:
    """Input for the jail ban use case."""
    jail_name: str
    ip: str


@dataclass
class JailBanResult:
    """Output of the jail ban use case."""
    success: bool
    message: str = ""


class JailBanCommand:
    """Use case: ban an IP in a specific fail2ban jail."""

    def __init__(self, fail2ban_port: Optional[Any]):
        self._port = fail2ban_port

    def execute(self, request: JailBanRequest) -> JailBanResult:
        if self._port is None:
            return JailBanResult(success=False, message="Fail2ban indisponible.")

        try:
            ip = IPAddress(request.ip)
        except ValueError as e:
            return JailBanResult(success=False, message=f"Adresse IP invalide : {e}")

        try:
            self._port.ban_ip(request.jail_name, ip)
        except IPAlreadyBannedError:
            return JailBanResult(
                success=False,
                message=f"IP {request.ip} déjà bannie dans '{request.jail_name}'.",
            )
        except JailNotFoundError:
            return JailBanResult(success=False, message=f"Jail '{request.jail_name}' introuvable.")
        except Exception as e:
            return JailBanResult(success=False, message=str(e))

        return JailBanResult(success=True, message=f"IP {request.ip} bannie dans '{request.jail_name}'.")


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Bannit une IP dans un jail fail2ban spécifique (menu 4.2).
#
# Pourquoi dans application/commands/ (charte) :
# - Orchestration simple : délègue entièrement à Fail2banPort
#   (infrastructure/backends/fail2ban/adapter.py::ban_ip()), traduit
#   ses exceptions métier en JailBanResult.
#
# Ce qu'il ne contient PAS :
# ❌ Pas d'import de infrastructure/backends/ (port reçu en paramètre)
# ❌ Pas de pattern ExecutionPlan/PipelineStep (abandonné, incompatible
#    avec l'injection de paramètres — remplace l'ancienne version de ce
#    fichier, jamais fonctionnelle : _execute_jail_ban() était un stub
#    vide, et actions.py appelait une signature .execute()/JailBanRequest
#    incompatible avec l'ancienne classe)
#
# Points clés :
# - JailBanRequest : jail_name + ip (str)
# - Appelle fail2ban_port.ban_ip(jail_name, IPAddress) — méthode
#   conforme à Fail2banPort (lève des exceptions), PAS
#   ban_ip_in_jail() (ancienne méthode bool, laissée intacte sur
#   l'adaptateur mais plus appelée d'ici). Migration du 2026-08-13 :
#   ban_ip_in_jail() retournait toujours True sans jamais vérifier la
#   réponse de fail2ban-client — bannir une IP déjà bannie rapportait
#   donc un faux succès. ban_ip() lève IPAlreadyBannedError dans ce
#   cas, traduite ici en JailBanResult(success=False, ...) — plus un
#   simple renommage, un vrai correctif de comportement.
# - Construit IPAddress(request.ip) avant l'appel — une IP malformée
#   échoue ici avec un message clair plutôt que de remonter jusqu'au
#   port.
#
# Flux d'exécution :
# interfaces/cli/actions.py : action_4_2_jail_ban_unban(ctx)
# application/commands/jail_ban.py : JailBanCommand.execute()
#   ↓ fail2ban_port.ban_ip() (infrastructure/backends/fail2ban/adapter.py)
#---------------------------------------------------------------------->
