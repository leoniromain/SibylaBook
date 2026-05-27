from __future__ import annotations
import json
import os
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from PySide6.QtCore import QObject, Signal

from sibyla.core.config import AppConfig
from sibyla.core import library as lib_svc
from sibyla.core import history as hist_svc
from sibyla.core.core import processar
from sibyla.core import capture as cap_module


def _library_path() -> str:
    cfg = AppConfig.load()
    return cfg.get("library_path", str(Path.home() / "Sibyla Library"))


def _state_file() -> Path:
    p = Path.home() / ".sibyla"
    p.mkdir(exist_ok=True)
    return p / "queue_state.json"


@dataclass
class TranslationJob:
    id: str
    file_path: str
    output_path: str
    settings: dict
    book_id: str | None = None
    file_name: str = ""
    status: Literal["queued", "running", "paused", "done", "error"] = "queued"
    page: int = 0
    total: int = 0
    message: str = ""
    log_lines: list[str] = field(default_factory=list)
    last_page: int = 0
    _cancel_event: threading.Event = field(default_factory=threading.Event, repr=False, compare=False)

    def progress_pct(self) -> int:
        return int(self.page / self.total * 100) if self.total else 0

    def status_label(self) -> str:
        if self.status == "queued":
            return "Na fila"
        if self.status == "running":
            return f"Traduzindo… {self.page}/{self.total}" if self.total else "Iniciando…"
        if self.status == "paused":
            return f"Pausado (pág. {self.last_page}/{self.total or '?'})"
        if self.status == "done":
            return "Concluído"
        return "Erro"


class QueueManager(QObject):
    jobs_changed = Signal()

    _instance: "QueueManager | None" = None

    def __init__(self) -> None:
        super().__init__()
        self._jobs: list[TranslationJob] = []
        self._lock = threading.Lock()
        self.jobs_changed.connect(self._save_state)
        self._load_state()

    @classmethod
    def instance(cls) -> "QueueManager":
        if cls._instance is None:
            cls._instance = QueueManager()
        return cls._instance

    # ── Public API ──────────────────────────────────────────────────────────

    def jobs(self) -> list[TranslationJob]:
        return list(self._jobs)

    def active_count(self) -> int:
        return sum(1 for j in self._jobs if j.status in ("queued", "running"))

    def add(
        self,
        file_path: str,
        output_path: str,
        settings: dict,
        book_id: str | None = None,
        file_name: str = "",
    ) -> TranslationJob:
        job = TranslationJob(
            id=str(uuid.uuid4()),
            file_path=file_path,
            output_path=output_path,
            settings=settings,
            book_id=book_id,
            file_name=file_name or os.path.basename(file_path),
        )
        with self._lock:
            self._jobs.append(job)
        self.jobs_changed.emit()
        self._try_start_next()
        return job

    def pause(self, job_id: str) -> None:
        with self._lock:
            job = next((j for j in self._jobs if j.id == job_id), None)
            if not job or job.status != "running":
                return
            job._cancel_event.set()
            job.status = "paused"
            job.last_page = max(job.page, 1)
        self.jobs_changed.emit()

    def resume(self, job_id: str) -> None:
        with self._lock:
            job = next((j for j in self._jobs if j.id == job_id), None)
            if not job or job.status != "paused":
                return
            settings = {**job.settings, "pag_ini": job.last_page}
            new_job = TranslationJob(
                id=str(uuid.uuid4()),
                file_path=job.file_path,
                output_path=job.output_path,
                settings=settings,
                book_id=job.book_id,
                file_name=job.file_name,
                status="queued",
            )
            self._jobs.remove(job)
            self._jobs.append(new_job)
        self.jobs_changed.emit()
        self._try_start_next()

    def cancel(self, job_id: str) -> None:
        with self._lock:
            job = next((j for j in self._jobs if j.id == job_id), None)
            if not job:
                return
            if job.status in ("queued", "paused"):
                self._jobs.remove(job)
            elif job.status == "running":
                job._cancel_event.set()
            else:
                return
        self.jobs_changed.emit()

    def remove_job(self, job_id: str) -> None:
        with self._lock:
            self._jobs = [j for j in self._jobs if j.id != job_id]
        self.jobs_changed.emit()

    def clear_finished(self) -> None:
        with self._lock:
            self._jobs = [j for j in self._jobs if j.status in ("queued", "running", "paused")]
        self.jobs_changed.emit()

    # ── Persistence ─────────────────────────────────────────────────────────

    def _save_state(self) -> None:
        try:
            jobs = list(self._jobs)
            data = [
                {
                    "id": j.id,
                    "file_path": j.file_path,
                    "output_path": j.output_path,
                    "settings": j.settings,
                    "book_id": j.book_id,
                    "file_name": j.file_name,
                    "status": j.status,
                    "page": j.page,
                    "total": j.total,
                    "last_page": j.last_page,
                    "message": j.message,
                }
                for j in jobs if j.status in ("queued", "paused")
            ]
            with open(_state_file(), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _load_state(self) -> None:
        try:
            with open(_state_file(), encoding="utf-8") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return
        for jd in data:
            status = jd.get("status", "queued")
            if status == "running":
                status = "paused"
            if status not in ("queued", "paused"):
                continue
            self._jobs.append(TranslationJob(
                id=jd["id"],
                file_path=jd["file_path"],
                output_path=jd["output_path"],
                settings=jd["settings"],
                book_id=jd.get("book_id"),
                file_name=jd.get("file_name", ""),
                status=status,
                page=jd.get("page", 0),
                total=jd.get("total", 0),
                last_page=jd.get("last_page", 0),
                message=jd.get("message", ""),
            ))

    # ── Internal ────────────────────────────────────────────────────────────

    def _try_start_next(self) -> None:
        with self._lock:
            if any(j.status == "running" for j in self._jobs):
                return
            next_job = next((j for j in self._jobs if j.status == "queued"), None)
            if not next_job:
                return
            next_job.status = "running"
            next_job._cancel_event = threading.Event()
        self.jobs_changed.emit()
        threading.Thread(target=self._run_job, args=(next_job,), daemon=True).start()

    def _run_job(self, job: TranslationJob) -> None:
        _PAGE_PAT = re.compile(r"\[(\d+)/(\d+)\]")
        cap_id = job.id
        cap_module.create_job(cap_id)

        # Monitor thread: lê stdout capturado e emite progresso
        def _monitor() -> None:
            while True:
                lines = cap_module.drain(cap_id)
                for line in lines:
                    if line == "__DONE__":
                        return
                    with self._lock:
                        job.log_lines.append(line)
                        if len(job.log_lines) > 500:
                            job.log_lines = job.log_lines[-500:]
                        m = _PAGE_PAT.search(line)
                        if m:
                            job.page = int(m.group(1))
                            job.total = int(m.group(2))
                    self.jobs_changed.emit()
                if not lines:
                    time.sleep(0.3)

        mon = threading.Thread(target=_monitor, daemon=True)
        mon.start()

        s = job.settings
        started = time.time()
        try:
            with cap_module.capture_stdout(cap_id):
                processar(
                    pdf_path=job.file_path,
                    pag_ini=s.get("pag_ini", 1),
                    pag_fim=s.get("pag_fim", 9999),
                    saida=job.output_path,
                    modo=s.get("modo", "novo"),
                    arquivo_base=s.get("base"),
                    cancel_event=job._cancel_event,
                    lang_src=s.get("lang_src", "en"),
                    lang_dst=s.get("lang_dst", "pt"),
                    fmt=s.get("fmt", "docx"),
                    glossario=s.get("glossario") or None,
                    alinhamento=s.get("alinhamento", "original"),
                    tamanho_fonte=s.get("tamanho_fonte"),
                    fonte=s.get("fonte"),
                    modo_traducao=s.get("modo_traducao", "pagina"),
                    engine=s.get("engine", "google"),
                    api_key=s.get("engine_api_key"),
                )
            with self._lock:
                if job.status == "running":
                    job.status = "done"
            hist_svc.record_job(job.file_path, job.output_path, s, int(time.time() - started))
            if job.book_id:
                try:
                    lib_svc.update_book(
                        _library_path(), job.book_id,
                        translated=True, translation_status="done"
                    )
                except Exception:
                    pass
        except Exception as e:
            with self._lock:
                if job.status == "running":
                    job.status = "error"
                    job.message = str(e)
        finally:
            cap_module.put_log(cap_id, "__DONE__")
            mon.join(timeout=2)
            cap_module.remove_job(cap_id)

        self.jobs_changed.emit()
        self._try_start_next()
