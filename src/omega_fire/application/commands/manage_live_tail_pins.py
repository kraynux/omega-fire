# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Manage live-tail pinned sources and history use case.

Orchestrates the pinned log sources and recent-source history shown by
menu 5.1 (Live Tail — sources disponibles / sous-menu [G]). Before this
command existed, that logic (merge defaults + custom pins, soft-hide
defaults, dedupe history) lived directly in interfaces/cli/actions.py
and persisted to /tmp (wiped on every reboot) — both a charter
violation (business logic + file I/O in the interface layer) and a
real usability problem (custom pins/history lost on restart).

Conforms to Omega-Fire architecture charter:
- No direct file I/O (delegates entirely to JsonStore, received
  already resolved by the caller)
- No subprocess calls
"""
from dataclasses import dataclass, field
from typing import Optional

from omega_fire.infrastructure.storage.files.json_store import JsonStore, JsonStoreError

DEFAULT_LIVE_TAIL_PINS: dict[str, str] = {
    "Nginx Access Log": "/var/log/nginx/access.log",
    "Apache Access Log": "/var/log/apache2/access.log",
    "Lighttpd Access Log": "/var/log/lighttpd/access.log",
    "Caddy Access Log": "/var/log/caddy/access.log",
    "Omega-Fire Audit Log": "logs/audit.log",
}

CUSTOM_PINS_RELATIVE_PATH = "live_tail_custom_pins.json"
DISABLED_PINS_RELATIVE_PATH = "live_tail_disabled_pins.json"
HISTORY_RELATIVE_PATH = "live_tail_history.json"

HISTORY_LIMIT = 5


@dataclass
class LiveTailPinResult:
    """Output of an add/remove operation on pins or history."""
    success: bool
    message: str = ""


class ManageLiveTailPinsCommand:
    """Use case: manage the pinned log sources and recent-source
    history for menu 5.1's live tail.

    Semantics preserved 1:1 from the previous /tmp-based implementation
    (this is a storage-layer migration, not a behavior change):
    - Default pins are code (DEFAULT_LIVE_TAIL_PINS), never stored —
      "removing" one records its name in a disabled list (soft-hide,
      reversible via purge or by re-adding a custom pin under the same
      name, which clears the disabled flag).
    - Custom pins are truly deleted on removal (not soft-hidden), and
      their name is also recorded in the disabled list — harmless in
      practice (defaults and custom names don't collide), kept for
      exact parity with the original logic.
    - History is capped at HISTORY_LIMIT entries, most recent first,
      deduplicated on insert.
    """

    def __init__(
        self,
        json_store: JsonStore,
        defaults: Optional[dict[str, str]] = None,
        custom_relative_path: str = CUSTOM_PINS_RELATIVE_PATH,
        disabled_relative_path: str = DISABLED_PINS_RELATIVE_PATH,
        history_relative_path: str = HISTORY_RELATIVE_PATH,
    ):
        self._store = json_store
        self._defaults = dict(defaults if defaults is not None else DEFAULT_LIVE_TAIL_PINS)
        self._custom_path = custom_relative_path
        self._disabled_path = disabled_relative_path
        self._history_path = history_relative_path

    def _load_dict(self, relative_path: str) -> dict[str, str]:
        if not self._store.exists(relative_path):
            return {}
        try:
            data = self._store.load(relative_path)
        except JsonStoreError:
            return {}
        return dict(data) if isinstance(data, dict) else {}

    def _load_list(self, relative_path: str) -> list[str]:
        if not self._store.exists(relative_path):
            return []
        try:
            data = self._store.load(relative_path)
        except JsonStoreError:
            return []
        return [str(item) for item in data] if isinstance(data, list) else []

    def list_custom_pinned(self) -> dict[str, str]:
        """Custom pins only, as persisted (no defaults, no filtering)."""
        return self._load_dict(self._custom_path)

    def list_all_known_paths(self) -> set[str]:
        """Paths of every known pin (defaults + custom), regardless of
        disabled status — used to decide whether a path is "already
        pinned" (and therefore shouldn't also clutter history), the
        same check the original /tmp-based implementation did against
        its pre-filter `all_pinned` dict.
        """
        custom = self._load_dict(self._custom_path)
        return set(self._defaults.values()) | set(custom.values())

    def list_active_pinned(self) -> dict[str, str]:
        """All pins currently shown (defaults + custom, minus disabled).

        Returns:
            {name: path}, defaults first then custom (custom overrides
            a default of the same name, matching the original
            {**default_pinned, **custom_pinned} merge order).
        """
        custom = self._load_dict(self._custom_path)
        disabled = self._load_list(self._disabled_path)
        merged = {**self._defaults, **custom}
        return {name: path for name, path in merged.items() if name not in disabled}

    def list_history(self, limit: int = HISTORY_LIMIT) -> list[str]:
        return self._load_list(self._history_path)[:limit]

    def add_pinned(self, name: str, path: str) -> LiveTailPinResult:
        """Add (or overwrite) a custom pin, and clear it from the
        disabled list if it was previously hidden under this name —
        re-adding a pin is how the user un-hides it.
        """
        name = name.strip()
        path = path.strip()
        if not name or not path:
            return LiveTailPinResult(success=False, message="Nom et chemin requis.")

        custom = self._load_dict(self._custom_path)
        custom[name] = path
        self._store.save(self._custom_path, custom)

        disabled = self._load_list(self._disabled_path)
        if name in disabled:
            disabled.remove(name)
            self._store.save(self._disabled_path, disabled)

        return LiveTailPinResult(success=True, message=f"Épingle '{name}' ajoutée.")

    def remove_pinned(self, name: str) -> LiveTailPinResult:
        """Remove a pin by name — deletes it from custom pins if
        present, and always records the name as disabled (hides a
        default of the same name too, matching the original logic).
        """
        custom = self._load_dict(self._custom_path)
        was_custom = name in custom
        if was_custom:
            del custom[name]
            self._store.save(self._custom_path, custom)

        disabled = self._load_list(self._disabled_path)
        if name not in disabled:
            disabled.append(name)
            self._store.save(self._disabled_path, disabled)

        if not was_custom and name not in self._defaults:
            return LiveTailPinResult(success=False, message=f"'{name}' n'est pas une épingle connue.")
        return LiveTailPinResult(success=True, message=f"Épingle '{name}' supprimée.")

    def record_history(self, path: str) -> None:
        """Insert a path at the front of history, deduplicated, capped."""
        history = self._load_list(self._history_path)
        history = [p for p in history if p != path]
        history.insert(0, path)
        history = history[:HISTORY_LIMIT]
        self._store.save(self._history_path, history)

    def remove_history_entry(self, path: str) -> LiveTailPinResult:
        history = self._load_list(self._history_path)
        if path not in history:
            return LiveTailPinResult(success=False, message="Entrée d'historique introuvable.")
        history.remove(path)
        self._store.save(self._history_path, history)
        return LiveTailPinResult(success=True, message="Entrée d'historique supprimée.")

    def purge_all(self) -> None:
        """Reset to factory state: deletes custom pins, disabled
        markers, and history. Defaults reappear (nothing left hiding
        them); no confirmation here — the caller (interfaces/) owns
        any user confirmation prompt.
        """
        for relative_path in (self._custom_path, self._disabled_path, self._history_path):
            self._store.delete(relative_path)


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Gère les sources épinglées (défauts + perso) et l'historique récent
#   du menu 5.1 (Live Tail) : fusion, masquage réversible des défauts,
#   suppression réelle des épingles perso, historique déduplique/capé.
#   Remplace une logique auparavant écrite directement dans
#   interfaces/cli/actions.py et persistée sous /tmp (perdue à chaque
#   redémarrage).
#
# Pourquoi dans application/commands/ (charte) :
# - Orchestration : délègue entièrement l'I/O à JsonStore
#   (infrastructure/storage/files/json_store.py).
#
# Ce qu'il ne contient PAS :
# ❌ Pas d'import de infrastructure/storage/ concret autre que JsonStore
#    (reçu en paramètre, jamais instancié ici)
# ❌ Pas de rendu/affichage (interfaces/cli/actions.py s'en charge)
# ❌ Pas de confirmation utilisateur (purge_all() ne demande rien —
#    à l'appelant de confirmer avant d'appeler)
#
# Points clés :
# - DEFAULT_LIVE_TAIL_PINS : les 5 épingles auparavant codées en dur.
# - Épingles par défaut : jamais stockées, juste masquables (liste de
#   noms désactivés) — réversible en ré-ajoutant sous le même nom, ou
#   via purge_all().
# - Épingles perso : réellement supprimées (pas juste masquées), mais
#   leur nom est quand même ajouté à la liste des désactivés — parité
#   exacte avec l'ancienne logique (inoffensif en pratique).
# - Historique : 5 dernières sources, dédupliqué, plus récent en tête.
# - Tous les load* silencieux sur erreur (fichier absent/corrompu ->
#   liste/dict vide), jamais d'exception remontée à l'appelant.
#
# Flux d'exécution :
# interfaces/cli/actions.py : action_5_1_live_tail(ctx), sous-menu [G]
# application/commands/manage_live_tail_pins.py : ManageLiveTailPinsCommand
#   ↓ JsonStore (infrastructure/storage/files/json_store.py), base_dir=var/runtime/
#---------------------------------------------------------------------->
