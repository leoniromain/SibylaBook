from __future__ import annotations
from datetime import datetime, timezone
from sibyla.core.config import AppConfig


def load() -> list[dict]:
    return AppConfig.load().get("historico", [])


def add(entry: dict) -> list[dict]:
    cfg = AppConfig.load()
    historico: list = cfg.get("historico", [])
    historico.insert(0, entry)
    historico = historico[:50]
    cfg.set("historico", historico)
    return historico


def clear() -> None:
    AppConfig.load().set("historico", [])


def record_job(file_path: str, output_path: str, settings: dict, duration_s: int) -> None:
    add({
        "pdf": file_path,
        "saida": output_path,
        "fmt": settings.get("fmt", "docx"),
        "lang_src": settings.get("lang_src", "en"),
        "lang_dst": settings.get("lang_dst", "pt"),
        "pag_ini": settings.get("pag_ini", 1),
        "pag_fim": settings.get("pag_fim", 9999),
        "data_iso": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
        "duracao_s": duration_s,
    })
