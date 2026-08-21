# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Manage jail presets use case.

Orchestrates the persisted list of jail templates ("presets") offered by
menu 4.4, mode "modèle" (Nginx, Apache, SSH...). Before this command
existed, that list was a hardcoded Python list rebuilt from scratch
inside interfaces/cli/actions.py — never persisted, never editable by
the user (referentiel_violations_actions.md, point 4 of the debt
enumeration — same architectural gap as PRESET_LOGS, already fixed the
same way for mode "sur-mesure" by ManagePinnedLogPathsCommand).

Conforms to Omega-Fire architecture charter:
- No direct file I/O (delegates entirely to JsonStore, received
  already resolved by the caller)
- No subprocess calls
"""
from dataclasses import dataclass, field
from typing import Any, Optional

from omega_fire.infrastructure.storage.files.json_store import JsonStore, JsonStoreError

# Champs attendus pour chaque preset — mêmes clés que l'ancienne liste
# Python codée en dur dans actions.py, inchangées pour ne rien casser
# côté consommation (action_4_4_create_jail lit sel_preset["name"] etc.).
PRESET_FIELDS = ("name", "desc", "log", "port", "filter", "retry", "find", "ban")

DEFAULT_JAIL_PRESETS: list[dict[str, str]] = [
    {"name": "sshd-custom", "desc": "SSH — Protection Authentification système (Auth log)", "log": "/var/log/auth.log", "port": "ssh", "filter": "sshd", "retry": "3", "find": "15m", "ban": "24h"},
    {"name": "syslog-custom", "desc": "Syslog — Surveillance des événements système généraux", "log": "/var/log/syslog", "port": "all", "filter": "syslog-errors", "retry": "5", "find": "10m", "ban": "1h"},
    {"name": "caddy-access", "desc": "Caddy — Access Log (Scanners, 404/403, Brute-force)", "log": "/var/log/caddy/access.log", "port": "http,https", "filter": "caddy-custom", "retry": "5", "find": "10m", "ban": "1h"},
    {"name": "caddy-error", "desc": "Caddy — Error Log (Échecs d'authentification & erreurs)", "log": "/var/log/caddy/error.log", "port": "http,https", "filter": "caddy-custom", "retry": "5", "find": "10m", "ban": "1h"},
    {"name": "lighttpd-access", "desc": "Lighttpd — Access Log (Scanners, requêtes abusives)", "log": "/var/log/lighttpd/access.log", "port": "http,https", "filter": "lighttpd-auth", "retry": "5", "find": "10m", "ban": "1h"},
    {"name": "lighttpd-error", "desc": "Lighttpd — Error Log (Échecs d'authentification HTTP)", "log": "/var/log/lighttpd/error.log", "port": "http,https", "filter": "lighttpd-auth", "retry": "5", "find": "10m", "ban": "1h"},
    {"name": "nginx-access", "desc": "Nginx — Access Log (Scanners de failles, bots, 404/403)", "log": "/var/log/nginx/access.log", "port": "http,https", "filter": "nginx-botsearch", "retry": "5", "find": "10m", "ban": "2h"},
    {"name": "nginx-error", "desc": "Nginx — Error Log (Échecs Auth HTTP 401/403 & erreurs)", "log": "/var/log/nginx/error.log", "port": "http,https", "filter": "nginx-http-auth", "retry": "5", "find": "10m", "ban": "2h"},
    {"name": "apache-access", "desc": "Apache — Access Log (Scanners de scripts & bots)", "log": "/var/log/apache2/access.log", "port": "http,https", "filter": "apache-noscript", "retry": "5", "find": "10m", "ban": "1h"},
    {"name": "apache-error", "desc": "Apache — Error Log (Échecs Auth HTTP 401 & refus)", "log": "/var/log/apache2/error.log", "port": "http,https", "filter": "apache-auth", "retry": "4", "find": "10m", "ban": "1h"},
    {"name": "wordpress-auth", "desc": "WordPress — Attaques wp-login / xmlrpc (Access)", "log": "/var/log/nginx/access.log", "port": "http,https", "filter": "wordpress", "retry": "3", "find": "20m", "ban": "24h"},
]

RELATIVE_STORE_PATH = "jail_presets.json"


@dataclass
class JailPresetsResult:
    """Output of an add/remove operation on the jail presets list."""
    success: bool
    presets: list[dict[str, str]] = field(default_factory=list)
    message: str = ""


class ManageJailPresetsCommand:
    """Use case: list, add to, and remove from the persisted jail
    presets list.

    Seeded with DEFAULT_JAIL_PRESETS on first use (no file yet) — same
    defaults previously hardcoded in actions.py, now a starting point
    rather than a fixed list: every entry (default or user-added) can
    be removed.
    """

    def __init__(
        self,
        json_store: JsonStore,
        relative_path: str = RELATIVE_STORE_PATH,
        defaults: Optional[list[dict[str, str]]] = None,
    ):
        self._store = json_store
        self._relative_path = relative_path
        self._defaults = [dict(p) for p in (defaults if defaults is not None else DEFAULT_JAIL_PRESETS)]

    def list_presets(self) -> list[dict[str, str]]:
        """Return the current presets, seeding the store on first use.

        Returns:
            List of preset dicts (name/desc/log/port/filter/retry/find/
            ban). Falls back to the defaults (without persisting them)
            if the stored file is corrupt/unreadable, or if any stored
            entry is missing a required field — never raises.
        """
        if not self._store.exists(self._relative_path):
            self._store.save(self._relative_path, self._defaults)
            return [dict(p) for p in self._defaults]

        try:
            data = self._store.load(self._relative_path)
        except JsonStoreError:
            return [dict(p) for p in self._defaults]

        if not isinstance(data, list):
            return [dict(p) for p in self._defaults]

        presets: list[dict[str, str]] = []
        for entry in data:
            if not isinstance(entry, dict) or not all(f in entry for f in PRESET_FIELDS):
                return [dict(p) for p in self._defaults]
            presets.append({f: str(entry[f]) for f in PRESET_FIELDS})
        return presets

    def add_preset(self, preset: dict[str, Any]) -> JailPresetsResult:
        """Add a preset to the list, if its name isn't already taken.

        Args:
            preset: Dict with all of PRESET_FIELDS (name/desc/log/port/
                filter/retry/find/ban) — values coerced to str.

        Returns:
            JailPresetsResult with the updated list either way.
        """
        presets = self.list_presets()
        missing = [f for f in PRESET_FIELDS if f not in preset]
        if missing:
            return JailPresetsResult(
                success=False, presets=presets,
                message=f"Champ(s) manquant(s) : {', '.join(missing)}.",
            )

        name = str(preset["name"]).strip()
        if not name:
            return JailPresetsResult(success=False, presets=presets, message="Nom de preset vide.")
        if any(p["name"] == name for p in presets):
            return JailPresetsResult(
                success=False, presets=presets, message=f"Un preset nommé '{name}' existe déjà."
            )

        new_preset = {f: str(preset[f]).strip() for f in PRESET_FIELDS}
        new_preset["name"] = name
        presets.append(new_preset)
        self._store.save(self._relative_path, presets)
        return JailPresetsResult(success=True, presets=presets, message=f"Preset '{name}' ajouté à la liste.")

    def remove_preset(self, name: str) -> JailPresetsResult:
        """Remove a preset by name — any entry, default or user-added,
        can be removed (no distinction kept between the two once seeded).

        Args:
            name: Exact preset name to remove.

        Returns:
            JailPresetsResult with the updated list either way.
        """
        presets = self.list_presets()
        match = next((p for p in presets if p["name"] == name), None)
        if match is None:
            return JailPresetsResult(
                success=False, presets=presets, message=f"'{name}' n'est pas dans la liste."
            )

        presets.remove(match)
        self._store.save(self._relative_path, presets)
        return JailPresetsResult(success=True, presets=presets, message=f"Preset '{name}' retiré de la liste.")


# <-- INFO DEV ---------------------------------------------------------
# Rôle :
# - Gère la liste persistée des modèles de jail proposés au menu 4.4
#   (création de jail, mode "modèle") : lister, ajouter, retirer.
#   Remplace la liste `presets` Python codée en dur dans
#   interfaces/cli/actions.py, jamais persistée ni modifiable.
#
# Pourquoi dans application/commands/ (charte) :
# - Orchestration simple : délègue entièrement à JsonStore
#   (infrastructure/storage/files/json_store.py) pour l'I/O.
#
# Ce qu'il ne contient PAS :
# ❌ Pas d'import de infrastructure/storage/ concret autre que JsonStore
#    (reçu en paramètre, jamais instancié ici)
# ❌ Pas de validation métier des champs (filtre existant, log réel...)
#    — la création du jail elle-même s'en charge déjà (create_jail())
#
# Points clés :
# - DEFAULT_JAIL_PRESETS : les 11 modèles auparavant codés en dur dans
#   actions.py — servent uniquement d'amorce (première utilisation),
#   plus une liste figée : chaque entrée, défaut ou ajout utilisateur,
#   peut être retirée sans distinction.
# - PRESET_FIELDS : les 8 clés attendues par preset, mêmes noms que
#   l'ancienne liste Python (name/desc/log/port/filter/retry/find/ban)
#   — zéro changement côté consommation dans actions.py.
# - list_presets() : amorce le fichier JSON au premier appel s'il
#   n'existe pas encore ; repli silencieux sur les défauts si le
#   fichier stocké est corrompu/illisible/mal formé — jamais d'exception.
# - add_preset() / remove_preset() : idempotents côté erreur (ajouter
#   un nom déjà pris ou retirer une entrée absente renvoie
#   success=False avec un message clair, pas une exception).
#
# Flux d'exécution :
# interfaces/cli/actions.py : action_4_4_create_jail(ctx)
# application/commands/manage_jail_presets.py : ManageJailPresetsCommand
#   ↓ JsonStore (infrastructure/storage/files/json_store.py), base_dir=var/runtime/
#---------------------------------------------------------------------->
