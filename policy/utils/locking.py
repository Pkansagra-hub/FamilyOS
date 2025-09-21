from __future__ import annotations

import os
from contextlib import contextmanager

# Cross-platform advisory file lock with graceful no-op fallback
try:
    import fcntl  # POSIX
    def _lock(fd):
        fcntl.flock(fd, fcntl.LOCK_EX)
    def _unlock(fd):
        fcntl.flock(fd, fcntl.LOCK_UN)
except Exception:  # pragma: no cover
    try:
        import msvcrt  # Windows
        import time
        def _lock(fd):
            h = msvcrt.get_osfhandle(fd.fileno())
            # lock entire file
            msvcrt.locking(fd.fileno(), msvcrt.LK_LOCK, 1)
        def _unlock(fd):
            msvcrt.locking(fd.fileno(), msvcrt.LK_UNLCK, 1)
    except Exception:
        def _lock(fd):  # best-effort no-op
            return
        def _unlock(fd):
            return

@contextmanager
def file_lock(path: str):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path + ".lock", "a+") as lockf:
        _lock(lockf)
        try:
            yield
        finally:
            _unlock(lockf)
