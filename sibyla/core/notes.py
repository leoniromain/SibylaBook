from __future__ import annotations
import json
import uuid
from datetime import datetime
from pathlib import Path

from sibyla.models.note import Note

_NOTES_DIR = Path.home() / ".sibyla" / "notes"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _dir() -> Path:
    _NOTES_DIR.mkdir(parents=True, exist_ok=True)
    return _NOTES_DIR


# ── CRUD ─────────────────────────────────────────────────────────────────────

def load_all() -> list[Note]:
    notes: list[Note] = []
    for path in sorted(_dir().glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            notes.append(Note(**data))
        except Exception:
            pass
    return notes


def load_one(note_id: str) -> Note | None:
    path = _dir() / f"{note_id}.json"
    if not path.exists():
        return None
    try:
        return Note(**json.loads(path.read_text(encoding="utf-8")))
    except Exception:
        return None


def save(note: Note) -> None:
    note.updated_at = _now()
    path = _dir() / f"{note.id}.json"
    path.write_text(
        json.dumps(note.model_dump(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def create(
    title: str = "Nova nota",
    content: str = "",
    tags: list[str] | None = None,
    cover_color: str = "#6366f1",
) -> Note:
    now = _now()
    note = Note(
        id=str(uuid.uuid4()),
        title=title,
        content=content,
        tags=tags or [],
        cover_color=cover_color,
        created_at=now,
        updated_at=now,
    )
    save(note)
    return note


def delete(note_id: str) -> None:
    path = _dir() / f"{note_id}.json"
    if path.exists():
        path.unlink()


def all_tags() -> list[str]:
    tags: set[str] = set()
    for note in load_all():
        tags.update(note.tags)
    return sorted(tags)
