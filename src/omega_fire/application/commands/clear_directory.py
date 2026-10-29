# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Cas d'usage : vider le dossier d'exports ou de captures d'ecran (ecran Reglages, meme
fonction que dans le reste de la suite omega-*).

Difference voulue avec omega-serv : omega-fire tourne en ROOT et le dossier est un champ
modifiable - un chemin mal saisi (`/`, `/etc`, le dossier personnel, la racine du projet)
viderait le systeme. Le dossier lui-meme est conserve, seul son CONTENU est supprime, et les
emplacements systeme ou contenant le projet sont refuses. Un lien symbolique place dans le
dossier est supprime sans suivre sa cible. Aucune elevation de droits (pas de sudo) : omega-fire
est deja root, et une demande de mot de passe dans la TUI la figerait."""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from omega_fire.application.exceptions import UnsafeDirectoryError
from omega_fire.shared.i18n import _

_SYSTEM_DIRS = frozenset(Path(p) for p in (
    "/", "/bin", "/boot", "/dev", "/etc", "/home", "/lib", "/lib32", "/lib64", "/media", "/mnt",
    "/opt", "/proc", "/root", "/run", "/sbin", "/srv", "/sys", "/tmp", "/usr", "/var",
    "/var/lib", "/var/log", "/usr/local",
))


def check_clearable(directory: Path, project_root: Path) -> Path:
    """Chemin reel du dossier a vider, ou UnsafeDirectoryError s'il ne doit jamais l'etre."""
    target = directory.resolve()
    project = project_root.resolve()
    if target in _SYSTEM_DIRS or target.parent == Path("/home"):
        raise UnsafeDirectoryError(str(target), _("dossier système ou personnel"))
    if target == project or target in project.parents:
        raise UnsafeDirectoryError(str(target), _("contient l'installation d'omega-fire"))
    if target.exists() and not target.is_dir():
        raise UnsafeDirectoryError(str(target), _("ce n'est pas un dossier"))
    return target


@dataclass(frozen=True)
class ClearResult:
    directory: Path
    removed: int
    failed: tuple[str, ...]
    """Elements qui ont resiste (droits, attribut immuable, systeme de fichiers en lecture
    seule) : signales a l'ecran, jamais de nouvelle tentative avec elevation de droits - un
    `sudo` demande dans la TUI lirait le mot de passe sur un terminal encore tenu par Textual
    et figerait l'application."""


def clear_directory(directory: Path, project_root: Path) -> ClearResult:
    """Supprime tout le contenu du dossier (cree s'il n'existe pas) ; continue apres un echec
    pour vider tout ce qui peut l'etre. Peut etre long : a appeler hors du thread de l'interface
    (OmegaScreen.run_blocking)."""
    target = check_clearable(directory, project_root)
    target.mkdir(parents=True, exist_ok=True)
    removed = 0
    failed: list[str] = []
    for entry in sorted(target.iterdir()):
        try:
            if entry.is_dir() and not entry.is_symlink():
                shutil.rmtree(entry)
            else:
                entry.unlink()
        except OSError as exc:
            failed.append(f"{entry.name} ({exc.strerror or exc})")
        else:
            removed += 1
    return ClearResult(target, removed, tuple(failed))
