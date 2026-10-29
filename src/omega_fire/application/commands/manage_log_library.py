# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Bibliotheque de logs (5.1), Favoris (5.2) et sources distantes SSH (version 3.5,
reprise d'omega-serv / omega-log). Stockage JSON via JsonStore (var/runtime/), comme les
epingles existantes ; aucune I/O directe hors lecture de l'etat des fichiers.

Decisions utilisateur (2026-10-28) : la Bibliotheque ne fait que l'IMPORT des logs —
automatique depuis les instances omega-serv detectees, epinglage a la main, ou copie d'un
log distant par scp — et alimente 5.2 et 5.3 uniquement."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable

from omega_fire.domain.logs.favorite import Favorite
from omega_fire.domain.logs.library import (
    ACCESS_FILE,
    ACCESS_OMEGA_SERV,
    ACCESS_SSH,
    LibraryRecord,
    LogFile,
)
from omega_fire.domain.logs.remote_source import RemoteLogSource, build_scp_command, safe_cache_filename
from omega_fire.domain.logs.viewer_type import ViewerType, allowed_viewers
from omega_fire.infrastructure.storage.files.json_store import JsonStore, JsonStoreError
from omega_fire.shared.i18n import _

LIBRARY_RELATIVE_PATH = "log_library.json"
IGNORED_RELATIVE_PATH = "log_library_ignored.json"
FAVORITES_RELATIVE_PATH = "log_favorites.json"
REMOTE_SOURCES_RELATIVE_PATH = "log_remote_sources.json"


@dataclass
class LibraryActionResult:
    success: bool
    message: str = ""
    count: int = 0


def _load_list(store: JsonStore, relative_path: str) -> list:
    if not store.exists(relative_path):
        return []
    try:
        data = store.load(relative_path)
    except JsonStoreError:
        return []
    return data if isinstance(data, list) else []


def refresh_log_file(record: LibraryRecord) -> LogFile:
    """Etat REEL du fichier (existe, taille, date), recalcule a chaque affichage."""
    try:
        stat = Path(record.path).stat()
    except OSError:
        return LogFile(path=record.path, access=record.access, source=record.source, exists=False)
    return LogFile(
        path=record.path, access=record.access, source=record.source, exists=True,
        size_bytes=stat.st_size, modified_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
    )


class LogLibraryCommand:
    def __init__(self, store: JsonStore, relative_path: str = LIBRARY_RELATIVE_PATH,
                 ignored_relative_path: str = IGNORED_RELATIVE_PATH) -> None:
        self._store = store
        self._relative_path = relative_path
        self._ignored_path = ignored_relative_path

    def _ignored(self) -> set[str]:
        """Journaux omega-serv retires a la main : l'import automatique (a chaque ouverture de
        5.1) ne les remet pas ; l'import explicite (bouton) les remet."""
        return {str(p) for p in _load_list(self._store, self._ignored_path)}

    def records(self) -> list[LibraryRecord]:
        records: list[LibraryRecord] = []
        for item in _load_list(self._store, self._relative_path):
            if isinstance(item, dict) and item.get("path"):
                records.append(LibraryRecord(path=str(item["path"]), access=str(item.get("access") or ACCESS_FILE),
                                             source=item.get("source")))
        return records

    def list_logs(self) -> list[LogFile]:
        return [refresh_log_file(r) for r in self.records()]

    def _save(self, records: Iterable[LibraryRecord]) -> None:
        self._store.save(self._relative_path, [
            {"path": r.path, "access": r.access, "source": r.source} for r in records
        ])

    def add(self, records: Iterable[LibraryRecord]) -> int:
        """Ajoute les chemins absents (un chemin deja present garde son entree). Renvoie le
        nombre d'ajouts."""
        current = self.records()
        known = {r.path for r in current}
        added = 0
        for record in records:
            if record.path not in known:
                current.append(record)
                known.add(record.path)
                added += 1
        if added:
            self._save(current)
        return added

    def pin_path(self, path: str) -> LibraryActionResult:
        path = path.strip()
        if not path:
            return LibraryActionResult(False, _("Chemin requis."))
        if not Path(path).is_absolute():
            return LibraryActionResult(False, _("Chemin absolu requis (ex. /var/log/nginx/access.log)."))
        if self.add([LibraryRecord(path=path, access=ACCESS_FILE)]):
            return LibraryActionResult(True, _("Ajouté à la Bibliothèque : {path}").format(path=path), 1)
        return LibraryActionResult(True, _("Déjà dans la Bibliothèque : {path}").format(path=path), 0)

    def import_omega_serv(self, instances: Iterable[tuple[str, Iterable[Path]]],
                          *, automatic: bool = False) -> LibraryActionResult:
        """instances : (nom de l'instance, journaux) — detectes par
        infrastructure/probe/omega_serv_detector.py. automatic : import a l'ouverture de 5.1,
        qui saute les journaux retires a la main ; sinon tout est reimporte."""
        records = [LibraryRecord(path=str(path), access=ACCESS_OMEGA_SERV, source=name)
                   for name, paths in instances for path in paths]
        if not records:
            return LibraryActionResult(False, _("Aucune instance omega-serv détectée sur cette machine."))
        if automatic:
            ignored = self._ignored()
            records = [r for r in records if r.path not in ignored]
        elif self._store.exists(self._ignored_path):
            self._store.save(self._ignored_path, [])
        added = self.add(records)
        return LibraryActionResult(
            True, _("{added} journal(aux) omega-serv importé(s), {known} déjà présent(s).").format(
                added=added, known=len(records) - added), added)

    def remove(self, paths: Iterable[str]) -> int:
        targets = set(paths)
        current = self.records()
        kept = [r for r in current if r.path not in targets]
        if len(kept) != len(current):
            self._save(kept)
            removed_serv = {r.path for r in current if r.path in targets and r.access == ACCESS_OMEGA_SERV}
            if removed_serv:
                self._store.save(self._ignored_path, sorted(self._ignored() | removed_serv))
        return len(current) - len(kept)


class LogFavoritesCommand:
    def __init__(self, store: JsonStore, relative_path: str = FAVORITES_RELATIVE_PATH) -> None:
        self._store = store
        self._relative_path = relative_path

    def list_favorites(self) -> list[Favorite]:
        favorites: list[Favorite] = []
        for item in _load_list(self._store, self._relative_path):
            try:
                favorites.append(Favorite(name=str(item["name"]), paths=tuple(str(p) for p in item["paths"]),
                                          viewer=ViewerType(item["viewer"])))
            except (KeyError, TypeError, ValueError):
                continue
        return favorites

    def create(self, *, name: str, paths: list[str], viewer: ViewerType) -> LibraryActionResult:
        name = name.strip()
        if not name:
            return LibraryActionResult(False, _("Nom requis."))
        if not paths:
            return LibraryActionResult(False, _("Au moins un log est requis."))
        if viewer not in allowed_viewers(len(paths)):
            return LibraryActionResult(False, _(
                "{count} logs sélectionnés : seul lnav peut les ouvrir ensemble.").format(count=len(paths)))
        favorites = [f for f in self.list_favorites() if f.name != name]
        favorites.append(Favorite(name=name, paths=tuple(paths), viewer=viewer))
        self._store.save(self._relative_path, [
            {"name": f.name, "paths": list(f.paths), "viewer": f.viewer.value} for f in favorites
        ])
        return LibraryActionResult(True, _("Favori « {name} » enregistré.").format(name=name), 1)

    def remove(self, name: str) -> bool:
        favorites = self.list_favorites()
        kept = [f for f in favorites if f.name != name]
        if len(kept) == len(favorites):
            return False
        self._store.save(self._relative_path, [
            {"name": f.name, "paths": list(f.paths), "viewer": f.viewer.value} for f in kept
        ])
        return True


class RemoteLogSourcesCommand:
    """Sources distantes SSH (reprises d'omega-serv) : enregistrer, supprimer, recuperer la
    copie locale (var/log/remote/) puis l'ajouter a la Bibliotheque."""

    def __init__(self, store: JsonStore, relative_path: str = REMOTE_SOURCES_RELATIVE_PATH) -> None:
        self._store = store
        self._relative_path = relative_path

    def list_sources(self) -> list[RemoteLogSource]:
        sources: list[RemoteLogSource] = []
        for item in _load_list(self._store, self._relative_path):
            try:
                sources.append(RemoteLogSource(
                    label=str(item["label"]), host=str(item["host"]), remote_path=str(item["remote_path"]),
                    user=item.get("user"), port=item.get("port"), identity_file=item.get("identity_file")))
            except (KeyError, TypeError):
                continue
        return sources

    def _save(self, sources: list[RemoteLogSource]) -> None:
        self._store.save(self._relative_path, [
            {"label": s.label, "host": s.host, "remote_path": s.remote_path, "user": s.user,
             "port": s.port, "identity_file": s.identity_file} for s in sources
        ])

    def save_source(self, *, label: str, host: str, remote_path: str, user: str = "",
                    port: str = "", identity_file: str = "") -> LibraryActionResult:
        if not label.strip():
            return LibraryActionResult(False, _("Label requis."))
        if not host.strip():
            return LibraryActionResult(False, _("Hôte requis."))
        if not remote_path.strip():
            return LibraryActionResult(False, _("Chemin distant requis."))
        port_value: int | None = None
        if port.strip():
            try:
                port_value = int(port)
            except ValueError:
                port_value = 0
            if not 1 <= port_value <= 65535:
                return LibraryActionResult(False, _("Port invalide (1-65535)."))
        source = RemoteLogSource(label=label.strip(), host=host.strip(), remote_path=remote_path.strip(),
                                 user=user.strip() or None, port=port_value,
                                 identity_file=identity_file.strip() or None)
        sources = [s for s in self.list_sources() if s.label != source.label]
        sources.append(source)
        self._save(sources)
        return LibraryActionResult(True, _("Source « {label} » enregistrée.").format(label=source.label), 1)

    def remove(self, label: str) -> None:
        self._save([s for s in self.list_sources() if s.label != label])

    def fetch(self, source: RemoteLogSource, cache_dir: Path, library: LogLibraryCommand,
              runner: Callable[[list[str]], tuple[bool, str]]) -> LibraryActionResult:
        local_dest = cache_dir / safe_cache_filename(source.label)
        cache_dir.mkdir(parents=True, exist_ok=True)
        ok, detail = runner(build_scp_command(source, local_dest))
        if not ok:
            return LibraryActionResult(False, _("Échec de la récupération : {detail}").format(detail=detail))
        library.add([LibraryRecord(path=str(local_dest), access=ACCESS_SSH, source=source.label)])
        return LibraryActionResult(True, _("Récupéré dans {path} et ajouté à la Bibliothèque.").format(path=local_dest), 1)


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Bibliothèque (5.1) : import des logs (omega-serv auto, épinglage,
#   SSH) ; Favoris (5.2) ; sources distantes.
# - Fichiers : var/runtime/log_library.json, log_favorites.json,
#   log_remote_sources.json ; copies distantes : var/log/remote/.
# Garde-fou : un favori de 2 logs ou plus ne peut utiliser que lnav
# (domain/logs/viewer_type.py), refusé à la création.
#----------------------------------------------------------------------
