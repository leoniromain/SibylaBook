from __future__ import annotations
import json
import os
from pathlib import Path

# Armazena config em ~/.sibyla/config.json (junto com sidebar_groups.json)
_CONFIG_FILE = str(Path.home() / ".sibyla" / "config.json")


class AppConfig:
    def __init__(self, data: dict | None = None):
        self._data: dict = data or {}

    @classmethod
    def load(cls) -> "AppConfig":
        try:
            with open(_CONFIG_FILE, "r", encoding="utf-8") as f:
                return cls(json.load(f))
        except Exception:
            return cls({})

    def save(self) -> None:
        os.makedirs(os.path.dirname(_CONFIG_FILE), exist_ok=True)
        try:
            with open(_CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def set(self, key: str, value) -> None:
        self._data[key] = value
        self.save()

    def set_many(self, data: dict) -> None:
        self._data.update(data)
        self.save()

    def all(self) -> dict:
        return dict(self._data)
