from __future__ import annotations

import os
import tempfile
from typing import Optional


def atomic_write_text(path: str, text: str, *, encoding: str = "utf-8") -> None:
    atomic_write_bytes(path, text.encode(encoding))


def atomic_write_bytes(path: str, data: bytes) -> None:
    """
    Atomically write bytes to `path` by writing to a temp file in the same directory
    and then os.replace().

    This prevents partially-written files on crash/interruption.
    """
    d = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(d, exist_ok=True)

    fd: Optional[int] = None
    tmp_path: Optional[str] = None
    try:
        fd, tmp_path = tempfile.mkstemp(prefix=".tmp_", dir=d)
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        fd = None
        os.replace(tmp_path, path)
        tmp_path = None
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
        if tmp_path is not None:
            try:
                os.remove(tmp_path)
            except OSError:
                pass