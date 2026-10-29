# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Ou est defini un jail, et par qui (point 7, version 3.5). Donnees pures, sans acces
disque : l'adaptateur fail2ban lit les fichiers, ce module en deduit pour chaque section
`[nom]` ses fichiers, son origine et s'il peut etre supprime sans toucher a autre chose.

Retour utilisateur 2026-10-28 : 4.5 cherchait `jail.d/<nom>.conf` ; omega-jail ecrit
`jail.d/omega-jail-<nom>.conf` — le jail etait arrete puis relance par le rechargement de
fail2ban. Meme chose pour un jail defini dans jail.local (sshd…)."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

ORIGIN_OMEGA_FIRE = "omega-fire"
ORIGIN_OMEGA_JAIL = "omega-jail"
ORIGIN_MAIN_CONFIG = "main-config"     # jail.conf / jail.local
ORIGIN_OTHER = "other"

# Raisons pour lesquelles un jail ne peut pas etre supprime par omega-fire.
BLOCKED_MAIN_CONFIG = "main-config"    # defini (aussi) dans jail.conf / jail.local
BLOCKED_SHARED_FILE = "shared-file"    # son fichier jail.d definit d'autres jails

_NOT_JAILS = {"DEFAULT", "INCLUDES", "Definition", "Init"}
_SECTION = re.compile(r"^\[([^\]\r\n]+)\][ \t]*$", re.MULTILINE)
_FILTER = re.compile(r"^\s*filter\s*=\s*([^\s\[]+)", re.MULTILINE)
_OMEGA_JAIL_PREFIX = "omega-jail-"


@dataclass(frozen=True)
class ConfigFile:
    path: str
    content: str
    main: bool = False          # jail.conf / jail.local (et non un fichier de jail.d)


@dataclass(frozen=True)
class JailDefinition:
    name: str
    files: tuple[str, ...]
    origin: str
    filter_name: str | None = None
    blocked: str | None = None          # None : suppression possible
    shared_with: tuple[str, ...] = field(default_factory=tuple)

    @property
    def deletable(self) -> bool:
        return self.blocked is None


def sections_in(content: str) -> list[str]:
    return [name.strip() for name in _SECTION.findall(content) if name.strip() not in _NOT_JAILS]


def section_block(content: str, name: str) -> str | None:
    match = re.search(rf"^\[{re.escape(name)}\][ \t]*$", content, re.MULTILINE)
    if not match:
        return None
    rest = content[match.end():]
    following = _SECTION.search(rest)
    return rest[:following.start()] if following else rest


def origin_of(config: ConfigFile) -> str:
    if config.main:
        return ORIGIN_MAIN_CONFIG
    base = os.path.basename(config.path)
    head = config.content[:300]
    if base.startswith(_OMEGA_JAIL_PREFIX) or "Genere par Omega-Jail" in head:
        return ORIGIN_OMEGA_JAIL
    if "Généré par Omega-Fire" in head or "Genere par Omega-Fire" in head:
        return ORIGIN_OMEGA_FIRE
    return ORIGIN_OTHER


def build_definitions(configs: list[ConfigFile]) -> dict[str, JailDefinition]:
    """Une definition par jail. Origine : celle du fichier jail.d qui le definit (sinon la
    configuration principale)."""
    by_name: dict[str, list[ConfigFile]] = {}
    for config in configs:
        for name in sections_in(config.content):
            by_name.setdefault(name, []).append(config)
    result: dict[str, JailDefinition] = {}
    for name, files in by_name.items():
        own = [config for config in files if not config.main]
        origin = origin_of(own[0]) if own else ORIGIN_MAIN_CONFIG
        filter_name = None
        for config in files:
            block = section_block(config.content, name) or ""
            match = _FILTER.search(block)
            if match:
                filter_name = match.group(1)
        blocked = None
        shared: list[str] = []
        if any(config.main for config in files):
            blocked = BLOCKED_MAIN_CONFIG
        else:
            for config in own:
                others = [other for other in sections_in(config.content) if other != name]
                if others:
                    blocked = BLOCKED_SHARED_FILE
                    shared.extend(others)
        result[name] = JailDefinition(name=name, files=tuple(config.path for config in files), origin=origin,
                                      filter_name=filter_name, blocked=blocked, shared_with=tuple(shared))
    return result


_ENABLED = re.compile(r"^\s*enabled\s*=\s*(\S+)", re.MULTILINE)


def enabled_jails(contents: list[str]) -> set[str]:
    """Jails actives par ces fichiers (jail.d/*.conf puis *.local, dans l'ordre de lecture de
    fail2ban) : le dernier `enabled` d'une section l'emporte. Tableau de bord, version 3.5 :
    l'alerte « configure mais non charge » comparait les NOMS DE FICHIERS aux jails charges —
    fausse pour chaque jail d'omega-jail (omega-jail-<nom>.conf), pour un fichier a plusieurs
    jails et pour un jail volontairement desactive."""
    state: dict[str, bool] = {}
    for content in contents:
        for name in sections_in(content):
            match = _ENABLED.search(section_block(content, name) or "")
            if match:
                state[name] = match.group(1).lower() in ("true", "yes", "1", "on")
    return {name for name, enabled in state.items() if enabled}


def owned_filter(definition: JailDefinition) -> str | None:
    """Filtre a supprimer avec le jail : seulement celui qui lui est propre (meme nom que le
    jail, ou filtre omega-jail-*), jamais un filtre standard partage (sshd…)."""
    name = definition.filter_name
    if not name:
        return None
    if name == definition.name or name.startswith(_OMEGA_JAIL_PREFIX):
        return name
    return None
