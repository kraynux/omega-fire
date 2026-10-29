# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Detection des instances omega-serv installees sur la machine, pour l'import automatique
de leurs journaux dans la Bibliotheque de logs (menu 5.1, version 3.5).

Lecture seule, deux sources :
1. unites systemd `omega-serv*.service` -> `WorkingDirectory=` (instance principale, qui ne
   figure pas dans le registre : constate 2026-10-28) ;
2. registre d'instances d'omega-serv `~/.config/omega-serv/instances.json` (cle `path`), de
   l'utilisateur qui a lance sudo et de root.
Les journaux d'une instance sont dans `<dossier>/var/log/` (access.log, error.log,
waf-alerts.log du WAF natif d'omega-serv, active-defense-enriched.jsonl). Ceux d'omega-waf
(script Lua execute par l'extra `magnet`) sont aux chemins de `options.waf.magnet.paths` de
la config de l'instance — par defaut aussi sous var/log/, mais deplacables (point 7,
version 3.5 ; meme lecture qu'omega-jail, detect.py)."""
from __future__ import annotations

import json
import os
import pwd
from dataclasses import dataclass
from pathlib import Path

SYSTEMD_DIRS = (Path("/etc/systemd/system"), Path("/lib/systemd/system"), Path("/usr/lib/systemd/system"))
_LOG_PATTERNS = ("*.log", "*.jsonl")


CONFIG_REL_PATH = Path("config") / "omega-serve.json"
_MAGNET_DEFAULT_LOGS = {"alerts_log": "var/log/waf-magnet-alerts.log",
                        "blocklist_log": "var/log/waf-magnet-blocklist.log"}


@dataclass(frozen=True, slots=True)
class OmegaServInstance:
    name: str
    root: Path
    systemd_unit: str = ""     # "omega-serv.service" si l'instance vient d'une unite systemd


@dataclass(frozen=True, slots=True)
class MagnetInfo:
    """Extra `magnet` d'une instance : omega-waf (script Lua) et ses deux journaux."""
    script: Path | None
    logs: tuple[Path, ...]


def _read_config(instance: OmegaServInstance) -> dict:
    try:
        data = json.loads((instance.root / CONFIG_REL_PATH).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def magnet_info(instance: OmegaServInstance) -> MagnetInfo | None:
    """None si l'extra magnet n'est pas active (omega-waf non utilise par cette instance)."""
    options = _read_config(instance).get("options") or {}
    magnet = ((options.get("waf") or {}) if isinstance(options, dict) else {}).get("magnet") or {}
    if not isinstance(magnet, dict) or not magnet.get("enabled", False):
        return None
    paths = magnet.get("paths") or {}
    logs = tuple(instance.root / str(paths.get(key) or default) for key, default in _MAGNET_DEFAULT_LOGS.items())
    script = magnet.get("script")
    return MagnetInfo(script=instance.root / str(script) if script else None, logs=logs)


def _systemd_instances(dirs: tuple[Path, ...]) -> list[OmegaServInstance]:
    found: list[OmegaServInstance] = []
    for directory in dirs:
        try:
            units = sorted(directory.glob("omega-serv*.service"))
        except OSError:
            continue
        for unit in units:
            try:
                lines = unit.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            for line in lines:
                key, _sep, value = line.strip().partition("=")
                if key == "WorkingDirectory" and value.strip():
                    found.append(OmegaServInstance(name=unit.stem, root=Path(value.strip()), systemd_unit=unit.name))
                    break
    return found


def _registry_paths() -> list[Path]:
    homes = [Path.home(), Path("/root")]
    sudo_user = os.environ.get("SUDO_USER")
    if sudo_user:
        try:
            homes.insert(0, Path(pwd.getpwnam(sudo_user).pw_dir))
        except KeyError:
            pass
    return [home / ".config" / "omega-serv" / "instances.json" for home in homes]


def _registry_instances(paths: list[Path]) -> list[OmegaServInstance]:
    found: list[OmegaServInstance] = []
    for path in paths:
        try:
            entries = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for entry in entries if isinstance(entries, list) else []:
            if isinstance(entry, dict) and entry.get("path"):
                found.append(OmegaServInstance(name=str(entry.get("name") or entry["path"]), root=Path(entry["path"])))
    return found


def detect_omega_serv_instances(
    systemd_dirs: tuple[Path, ...] = SYSTEMD_DIRS,
    registry_paths: list[Path] | None = None,
) -> list[OmegaServInstance]:
    """Instances dont le dossier existe, sans doublon (meme dossier reel)."""
    candidates = _systemd_instances(systemd_dirs) + _registry_instances(
        registry_paths if registry_paths is not None else _registry_paths())
    unique: dict[Path, OmegaServInstance] = {}
    for instance in candidates:
        try:
            real = instance.root.resolve()
        except OSError:
            continue
        if real.is_dir() and real not in unique:
            unique[real] = OmegaServInstance(name=instance.name, root=real, systemd_unit=instance.systemd_unit)
    return list(unique.values())


def instance_log_files(instance: OmegaServInstance) -> list[Path]:
    log_dir = instance.root / "var" / "log"
    files: set[Path] = set()
    for pattern in _LOG_PATTERNS:
        try:
            files.update(p for p in log_dir.glob(pattern) if p.is_file())
        except OSError:
            continue
    # Journaux d'omega-waf, meme places hors de var/log/ par la config magnet.
    magnet = magnet_info(instance)
    for path in (magnet.logs if magnet else ()):
        try:
            if path.is_file():
                files.add(path)
        except OSError:
            continue
    return sorted(files)
