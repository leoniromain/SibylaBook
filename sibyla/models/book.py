from __future__ import annotations
from typing import Optional
from pydantic import BaseModel


class Book(BaseModel):
    id: str
    title: str
    author: str = ""
    format: str          # "pdf" | "epub"
    path: str
    cover_path: str = ""
    language: str = ""
    added_at: str
    translated: bool = False
    tags: list[str] = []
    pages: Optional[int] = None
    size_mb: Optional[float] = None
    rating: int = 0                        # 0 = unrated, 1-5 stars
    read_status: str = "unread"            # "unread" | "reading" | "read"
    translation_status: str = "none"       # "none" | "in_progress" | "done"
    series: str = ""
    series_index: Optional[float] = None


class BookImport(BaseModel):
    path: str
    copy_to_library: bool = False


class BookUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    language: Optional[str] = None
    tags: Optional[list[str]] = None
    translated: Optional[bool] = None
    rating: Optional[int] = None
    read_status: Optional[str] = None
    translation_status: Optional[str] = None
    series: Optional[str] = None
    series_index: Optional[float] = None


class LibraryConfig(BaseModel):
    library_path: str
