from __future__ import annotations
from typing import Optional
from pydantic import BaseModel


class Note(BaseModel):
    id: str
    title: str
    content: str = ""           # HTML rich-text (QTextEdit native)
    tags: list[str] = []
    cover_color: str = "#6366f1"
    created_at: str = ""
    updated_at: str = ""


class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[list[str]] = None
    cover_color: Optional[str] = None
