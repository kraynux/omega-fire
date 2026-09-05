# Copyright (c) 2026 kraynux - kraynux@proton.me - Licence MIT (voir fichier LICENSE)
"""Implementation JSON du port SettingsStore (omega_lib.ports.settings_store),
meme convention que json_store.py (var/runtime/, non versionne)."""
from __future__ import annotations

import json
from pathlib import Path


class JsonSettingsStore:
    """Implemente omega_lib.ports.settings_store.SettingsStore."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def get(self, key: str, default: str | None = None) -> str | None:
        return self.all().get(key, default)

    def set(self, key: str, value: str) -> None:
        data = self.all()
        data[key] = value
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def all(self) -> dict[str, str]:
        if not self._path.exists():
            return {}
        return dict(json.loads(self._path.read_text(encoding="utf-8")))
