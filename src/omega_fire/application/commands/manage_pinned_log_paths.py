# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Manage pinned log paths use case.

Orchestrates the persisted list of "pinned" log file paths offered as
quick picks when creating a fail2ban jail (menu 4.4, mode "sur-mesure").
Before this command existed, that list (PRESET_LOGS) was a hardcoded
Python list rebuilt from scratch inside interfaces/cli/actions.py —
never persisted, never editable by the user (referentiel_violations_
actions.md, follow-up dependency noted since Phase 1(B)).

Conforms to Omega-Fire architecture charter:
- No direct file I/O (delegates entirely to JsonStore, received
  already resolved by the caller)
- No subprocess calls
"""
from dataclasses import dataclass, field
from typing import Optional

from omega_fire.infrastructure.storage.files.json_store import JsonStore, JsonStoreError

DEFAULT_PINNED_LOG_PATHS: list[str] = [
    "/var/log/auth.log",
    "/var/log/syslog",
    "/var/log/caddy/access.log",
    "/var/log/caddy/error.log",
    "/var/log/lighttpd/access.log",
    "/var/log/lighttpd/error.log",
    "/var/log/nginx/access.log",
    "/var/log/nginx/error.log",
    "/var/log/apache2/access.log",
    "/var/log/apache2/error.log",
]

RELATIVE_STORE_PATH = "pinned_log_paths.json"


@dataclass
class PinnedLogPathsResult:
    """Output of an add/remove operation on the pinned log paths list."""
    success: bool
    paths: list[str] = field(default_factory=list)
    message: str = ""


class ManagePinnedLogPathsCommand:
    """Use case: list, add to, and remove from the persisted pinned log
    paths list.

    Seeded with DEFAULT_PINNED_LOG_PATHS on first use (no file yet) —
    same defaults previously hardcoded in actions.py, now a starting
    point rather than a fixed list: every entry (default or
    user-added) can be removed.
    """

    def __init__(
        self,
        json_store: JsonStore,
        relative_path: str = RELATIVE_STORE_PATH,
        defaults: Optional[list[str]] = None,
    ):
        self._store = json_store
        self._relative_path = relative_path
        self._defaults = list(defaults if defaults is not None else DEFAULT_PINNED_LOG_PATHS)

    def list_paths(self) -> list[str]:
        """Return the current pinned paths, seeding the store on first use.

        Returns:
            List of path strings. Falls back to the defaults (without
            persisting them) if the stored file is corrupt/unreadable —
            never raises.
        """
        if not self._store.exists(self._relative_path):
            self._store.save(self._relative_path, self._defaults)
            return list(self._defaults)

        try:
            data = self._store.load(self._relative_path)
        except JsonStoreError:
            return list(self._defaults)

        if not isinstance(data, list):
            return list(self._defaults)
        return [str(p) for p in data]

    def add_path(self, path: str) -> PinnedLogPathsResult:
        """Add a path to the pinned list, if not already present.

        Args:
            path: Path string to add (not validated for existence on
                disk — a jail can reasonably be configured to watch a
                log file that doesn't exist yet).

        Returns:
            PinnedLogPathsResult with the updated list either way.
        """
        path = path.strip()
        paths = self.list_paths()
        if not path:
            return PinnedLogPathsResult(success=False, paths=paths, message="Chemin vide.")
        if path in paths:
            return PinnedLogPathsResult(
                success=False, paths=paths, message=f"'{path}' est déjà dans la liste."
            )

        paths.append(path)
        self._store.save(self._relative_path, paths)
        return PinnedLogPathsResult(success=True, paths=paths, message=f"'{path}' ajouté à la liste.")

    def remove_path(self, path: str) -> PinnedLogPathsResult:
        """Remove a path from the pinned list — any entry, default or
        user-added, can be removed (no distinction kept between the two
        once seeded).

        Args:
            path: Exact path string to remove.

        Returns:
            PinnedLogPathsResult with the updated list either way.
        """
        paths = self.list_paths()
        if path not in paths:
            return PinnedLogPathsResult(
                success=False, paths=paths, message=f"'{path}' n'est pas dans la liste."
            )

        paths.remove(path)
        self._store.save(self._relative_path, paths)
        return PinnedLogPathsResult(success=True, paths=paths, message=f"'{path}' retiré de la liste.")


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Gère la liste persistée des chemins de logs épinglés proposés au
#   menu 4.4 (création de jail, mode "sur-mesure") : lister, ajouter,
#   retirer. Remplace PRESET_LOGS, une liste Python codée en dur dans
#   interfaces/cli/actions.py, jamais persistée ni modifiable.
#
# Pourquoi dans application/commands/ (charte) :
# - Orchestration simple : délègue entièrement à JsonStore
#   (infrastructure/storage/files/json_store.py) pour l'I/O.
#
# Ce qu'il ne contient PAS :
# ❌ Pas d'import de infrastructure/storage/ concret autre que JsonStore
#    (reçu en paramètre, jamais instancié ici)
# ❌ Pas de validation d'existence du chemin sur disque (un jail peut
#    surveiller un fichier qui n'existe pas encore — create_jail() s'en
#    charge déjà)
#
# Points clés :
# - DEFAULT_PINNED_LOG_PATHS : les 10 chemins auparavant codés en dur
#   dans actions.py (PRESET_LOGS) — servent uniquement d'amorce
#   (première utilisation), plus une liste figée : chaque entrée,
#   défaut ou ajout utilisateur, peut être retirée sans distinction.
# - list_paths() : amorce le fichier JSON au premier appel s'il
#   n'existe pas encore ; repli silencieux sur les défauts si le
#   fichier stocké est corrompu/illisible (jamais d'exception).
# - add_path() / remove_path() : idempotents côté erreur (ajouter un
#   doublon ou retirer une entrée absente renvoie success=False avec
#   un message clair, pas une exception).
#
# Flux d'exécution :
# interfaces/cli/actions.py : action_4_4_create_jail(ctx)
# application/commands/manage_pinned_log_paths.py : ManagePinnedLogPathsCommand
#   ↓ JsonStore (infrastructure/storage/files/json_store.py), base_dir=var/runtime/
#---------------------------------------------------------------------->
