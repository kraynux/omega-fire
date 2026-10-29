# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Outils communs aux tests i18n : catalogue .mo minimal ecrit sans msgfmt, reglages en memoire."""
from __future__ import annotations

import struct
from pathlib import Path

from textual.app import App

from omega_fire.app.dependency_container import DependencyContainer
from omega_fire.infrastructure.i18n.gettext_language_catalog import GettextLanguageCatalog
from omega_fire.interfaces.tui.rendering.textual_theme_builder import build_all_textual_themes


def write_mo(path: Path, messages: dict[str, str], status: str | None = None) -> None:
    """Catalogue GNU .mo minimal (format documente de gettext), sans msgfmt."""
    header = "Content-Type: text/plain; charset=UTF-8\nPlural-Forms: nplurals=2; plural=(n != 1);\n"
    if status:
        header += f"X-Omega-Status: {status}\n"
    entries = sorted({"": header, **messages}.items())
    ids = b"".join(k.encode() + b"\0" for k, _v in entries)
    strs = b"".join(v.encode() + b"\0" for _k, v in entries)
    key_start = 28 + 16 * len(entries)
    offsets: list[int] = []
    pos = 0
    for key, _v in entries:
        offsets += [len(key.encode()), key_start + pos]
        pos += len(key.encode()) + 1
    pos = 0
    for _k, value in entries:
        offsets += [len(value.encode()), key_start + len(ids) + pos]
        pos += len(value.encode()) + 1
    table = struct.pack("Iiiiiii", 0x950412DE, 0, len(entries), 28, 28 + 8 * len(entries), 0, 0)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(table + struct.pack(f"{len(offsets)}i", *offsets) + ids + strs)


class MemorySettings:
    def __init__(self, values: dict[str, str] | None = None) -> None:
        self.values = dict(values or {})

    def get(self, key: str, default: str | None = None) -> str | None:
        return self.values.get(key, default)

    def set(self, key: str, value: str) -> None:
        self.values[key] = value

    def all(self) -> dict[str, str]:
        return dict(self.values)


class FakeContainer(DependencyContainer):
    """Vrai conteneur, mais reglages en memoire et dossiers dans un repertoire temporaire."""

    def __init__(self, settings: MemorySettings, root: Path, locale: Path | None = None) -> None:
        super().__init__()
        self._settings = settings
        self._root = root
        self._locale = locale if locale is not None else root / "locale"

    @property
    def settings_store(self):  # type: ignore[override]
        return self._settings

    @property
    def language_catalog(self):  # type: ignore[override]
        return GettextLanguageCatalog(self._locale)

    @property
    def project_root(self) -> Path:  # type: ignore[override]
        return self._root

    @property
    def default_exports_dir(self) -> Path:  # type: ignore[override]
        return self._root / "var" / "exports"

    @property
    def default_screenshots_dir(self) -> Path:  # type: ignore[override]
        return self._root / "var" / "screenshots"


class HostApp(App[None]):
    """Application minimale qui ouvre un ecran, avec les themes omega-* enregistres."""

    def __init__(self, screen) -> None:
        super().__init__()
        for theme in build_all_textual_themes():
            self.register_theme(theme)
        self.theme = "omega-base"
        self._first = screen
        self.pending_restart = None
        self.messages: list[str] = []

    def on_mount(self) -> None:
        self.push_screen(self._first)

    def notify(self, message, **kwargs) -> None:  # type: ignore[override]
        self.messages.append(str(message))
