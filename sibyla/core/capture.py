from __future__ import annotations
import sys
import io
import queue
import threading
from contextlib import contextmanager

_queues: dict[str, queue.Queue] = {}
_lock = threading.Lock()


def create_job(job_id: str) -> None:
    with _lock:
        _queues[job_id] = queue.Queue()


def remove_job(job_id: str) -> None:
    with _lock:
        _queues.pop(job_id, None)


def put_log(job_id: str, line: str) -> None:
    with _lock:
        q = _queues.get(job_id)
    if q is not None:
        q.put(line)


def drain(job_id: str, timeout: float = 0.5) -> list[str]:
    with _lock:
        q = _queues.get(job_id)
    if q is None:
        return []
    lines = []
    try:
        while True:
            lines.append(q.get_nowait())
    except queue.Empty:
        pass
    return lines


class _JobWriter(io.TextIOBase):
    def __init__(self, job_id: str, original: io.TextIOBase):
        self._job_id = job_id
        self._original = original

    def write(self, s: str) -> int:
        if s and s.strip():
            put_log(self._job_id, s.rstrip("\n"))
        if self._original:
            try:
                self._original.write(s)
            except (UnicodeEncodeError, UnicodeDecodeError):
                # stdout do exe Windows usa cp1252 por padrão; ignora silenciosamente
                try:
                    self._original.write(s.encode("ascii", errors="replace").decode("ascii"))
                except Exception:
                    pass
        return len(s)

    def flush(self):
        if self._original:
            self._original.flush()


@contextmanager
def capture_stdout(job_id: str):
    original = sys.stdout
    sys.stdout = _JobWriter(job_id, original)
    try:
        yield
    finally:
        sys.stdout = original
