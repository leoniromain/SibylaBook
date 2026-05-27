from __future__ import annotations
import json
import uuid
from pathlib import Path

_FILE = Path.home() / ".sibyla" / "sidebar_groups.json"


def load() -> list[dict]:
    try:
        data = json.loads(_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def save(groups: list[dict]) -> None:
    _FILE.parent.mkdir(parents=True, exist_ok=True)
    _FILE.write_text(
        json.dumps(groups, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def new_folder(name: str, color: str) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "type": "folder",
        "name": name,
        "color": color,
        "tag": name,      # books with this tag belong to the folder
        "children": [],   # nested folders / dividers
    }


def new_divider(name: str, color: str) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "type": "divider",
        "name": name,
        "color": color,
        "children": [],
    }
