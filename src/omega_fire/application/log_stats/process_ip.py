# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
# Porte d'omega-log (application/use_cases/process_ip.py) le 2026-11-09 (OMEGA-FIRE_PLAN_LOGS_NIVEAU_SERV_LOG.md) : garder identique a la source.
"""Use cases "Voir et Traiter IP" (plan_omega_log.md §2) :
- Top 10 : ADAPTE depuis omega-serv/top_ips_screen.py (source retenue,
  plan §2) — meme principe (compter les occurrences par IP sur une
  periode), mais generalise a N'IMPORTE QUEL log de la Bibliotheque au
  lieu du seul access log fixe de SERV, via domain/logs/{parser,
  analytics}.py (generiques, Phase 2).
- Retrait d'IP : ADAPTE depuis omega-fire/remove_ip_from_log_screen.py
  (complement, absent de SERV) — meme principe (filtrer les lignes
  contenant l'IP), mais ecriture atomique
  (fichier temporaire + remplacement) plutot qu'un `open(path, "w")`
  direct : une panne au milieu de l'ecriture source laisserait le
  fichier original tronque/corrompu, l'ecriture atomique ne le remplace
  qu'une fois la nouvelle version entierement ecrite avec succes.

`runner` optionnel sur chaque fonction (AJOUTE 2026-10-03, plan §5.1,
elevation sudo ponctuelle) : sans lui, une PermissionError leve
PermissionRequiredError (signal pour l'ecran TUI appelant — voir son
docstring) ; fourni (apres authentification via request_elevation()
cote ecran), elle retombe sur une lecture/ecriture privilegiee."""
from __future__ import annotations

import ipaddress
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from omega_fire.application.log_stats.log_tasks import accumulate_paths
from omega_fire.domain.log_stats.ip_match import ip_line_pattern, line_contains_ip
from omega_fire.domain.log_stats.models import TopIP
from omega_fire.infrastructure.log_stats.elevation import PermissionRequiredError
from omega_fire.infrastructure.log_stats.privileged_file_ops import (
    overwrite_file_privileged,
    read_file_privileged,
)
from omega_fire.shared.i18n import _

if TYPE_CHECKING:
    from omega_fire.ports.log_process_runner import ProcessRunnerPort


def compute_top_ips_for_paths(
    paths: list[str], *, period: str | None = None, n: int = 10, now: datetime | None = None,
    runner: ProcessRunnerPort | None = None,
) -> list[TopIP]:
    """Top N IP toutes sources confondues parmi `paths`. `period` filtre
    sur l'horodatage de chaque ligne ("24h"/"7d"/"30d"/None pour tout)."""
    return accumulate_paths(paths, period=period, now=now, runner=runner).top_ips(n)


@dataclass
class RemoveIpResult:
    success: bool
    occurrences: int = 0
    message: str = ""


def count_ip_occurrences(path: str, ip: str, *, runner: ProcessRunnerPort | None = None) -> int:
    """Compte sans modifier — utilise pour l'apercu avant confirmation."""
    try:
        ipaddress.ip_address(ip)
    except ValueError:
        return 0
    pattern = ip_line_pattern(ip)
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return sum(1 for line in f if line_contains_ip(line, ip, pattern))
    except PermissionError:
        if runner is None:
            raise PermissionRequiredError(path) from None
        result = read_file_privileged(runner, path)
        if not result.success:
            return 0
        return sum(1 for line in result.content.splitlines() if line_contains_ip(line, ip, pattern))
    except OSError:
        return 0


def remove_ip_from_file(path: str, ip: str, *, runner: ProcessRunnerPort | None = None) -> RemoveIpResult:
    """Retire toutes les lignes contenant `ip` (limite de mot, pas une
    sous-chaine d'une autre IP) de `path`. Ecriture atomique dans le cas
    non privilegie : la version filtree est ecrite dans un fichier
    temporaire puis `os.replace()` sur l'original — jamais de fichier
    tronque en cas de panne en cours d'ecriture. Dans le cas privilegie
    (`runner` fourni, PermissionError sur la tentative normale ci-dessus
    OU sur l'ecriture atomique elle-meme — le dossier parent peut etre
    lui aussi non inscriptible, ex. /var/log), retombe sur
    overwrite_file_privileged (sudo cp depuis un fichier temporaire que
    nous possedons) : non atomique, mais c'est `sudo` qui verifie et
    autorise l'acces, jamais une ecriture Python directe sur la cible."""
    try:
        ipaddress.ip_address(ip)
    except ValueError:
        return RemoveIpResult(success=False, message=_("Adresse IP invalide : {ip}").format(ip=ip))

    target = Path(path)
    if not target.is_file():
        return RemoveIpResult(success=False, message=_("Fichier introuvable : {path}").format(path=path))

    pattern = ip_line_pattern(ip)
    try:
        with target.open(encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except PermissionError:
        if runner is None:
            raise PermissionRequiredError(path) from None
        result = read_file_privileged(runner, path)
        if not result.success:
            return RemoveIpResult(success=False, message=_("Lecture privilégiée impossible : "
                                                           "{message}").format(message=result.message))
        lines = result.content.splitlines(keepends=True)
    except OSError as exc:
        return RemoveIpResult(success=False, message=_("Lecture impossible : {exc}").format(exc=exc))

    kept = [line for line in lines if not line_contains_ip(line, ip, pattern)]
    occurrences = len(lines) - len(kept)
    if occurrences == 0:
        return RemoveIpResult(success=True, occurrences=0, message=_("Aucune occurrence de {ip} trouvée.").format(ip=ip))

    new_content = "".join(kept)
    tmp_path = target.with_suffix(target.suffix + ".omega-log-tmp")
    try:
        with tmp_path.open("w", encoding="utf-8") as f:
            f.write(new_content)
        try:
            tmp_stat = os.stat(target)
            os.chmod(tmp_path, tmp_stat.st_mode)
        except OSError:
            pass
        os.replace(tmp_path, target)
    except PermissionError:
        tmp_path.unlink(missing_ok=True)
        if runner is None:
            raise PermissionRequiredError(path) from None
        priv_result = overwrite_file_privileged(runner, path, new_content)
        if not priv_result.success:
            return RemoveIpResult(success=False, message=_("Écriture privilégiée impossible : "
                                                           "{message}").format(message=priv_result.message))
    except OSError as exc:
        tmp_path.unlink(missing_ok=True)
        return RemoveIpResult(success=False, message=_("Écriture impossible : {exc}").format(exc=exc))

    return RemoveIpResult(success=True, occurrences=occurrences, message=_("{occurrences} occurrence(s) de {ip} "
                                                                           "retirée(s).").format(occurrences=occurrences, ip=ip))
