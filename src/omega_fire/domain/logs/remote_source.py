# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Source distante (SSH) de la Bibliotheque de logs, reprise d'omega-serv
(OMEGA-SERV_ETUDE-FAISABILITE_LOGS_DISTANTS.md, 2026-10-15) : recupere a la demande le log
d'une machine du reseau via `scp`. Aucun mot de passe : l'authentification est celle du
`ssh` du systeme (agent, ~/.ssh/config) ; `identity_file` n'est qu'un CHEMIN de cle."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

_SLUG_RE = re.compile(r"[^a-z0-9]+")
_MAX_SLUG_LENGTH = 60


@dataclass(frozen=True, slots=True)
class RemoteLogSource:
    label: str
    host: str
    remote_path: str
    user: str | None = None
    port: int | None = None
    identity_file: str | None = None


def build_scp_command(source: RemoteLogSource, local_dest: Path) -> list[str]:
    """argv de `scp` en LISTE, jamais une chaine shell : aucune injection possible par
    l'hote ou le chemin saisis."""
    target_host = f"{source.user}@{source.host}" if source.user else source.host
    command = ["scp"]
    if source.port is not None:
        command += ["-P", str(source.port)]
    if source.identity_file:
        command += ["-i", source.identity_file]
    command += ["-o", "ConnectTimeout=10", "-o", "BatchMode=yes",
                f"{target_host}:{source.remote_path}", str(local_dest)]
    return command


def safe_cache_filename(label: str, *, suffix: str = ".log") -> str:
    """Nom de fichier local derive du label, jamais le label brut (aucune traversee de
    chemin). Deterministe : re-recuperer ecrase sa propre copie."""
    slug = _SLUG_RE.sub("-", label.strip().lower()).strip("-")[:_MAX_SLUG_LENGTH] or "source"
    digest = hashlib.sha256(label.encode("utf-8")).hexdigest()[:8]
    return f"{slug}-{digest}{suffix}"
