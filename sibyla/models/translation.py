from __future__ import annotations
from typing import Optional
from pydantic import BaseModel


class TranslationConfig(BaseModel):
    pdf: str
    pag_ini: int
    pag_fim: int
    modo: str = "novo"
    base: Optional[str] = None
    saida: str
    lang_src: str = "en"
    lang_dst: str = "pt"
    fmt: str = "docx"
    glossario: list[str] = []
    alinhamento: str = "original"
    tamanho_fonte: Optional[int] = None
    fonte: Optional[str] = None
    modo_traducao: str = "pagina"
    engine: str = "google"
    engine_api_key: Optional[str] = None


class JobStatus(BaseModel):
    job_id: str
    status: str
    output_path: Optional[str] = None
    error: Optional[str] = None


class PdfInfo(BaseModel):
    pages: int
    size_mb: float
    detected_lang: Optional[str] = None


class HistoryEntry(BaseModel):
    pdf: str
    saida: str
    fmt: str
    lang_src: str
    lang_dst: str
    pag_ini: int
    pag_fim: int
    data_iso: str
    duracao_s: Optional[int] = None
