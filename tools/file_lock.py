"""跨线程、跨进程的非阻塞文件锁；进程退出后由操作系统释放。"""

from contextlib import contextmanager
import os
from pathlib import Path
import threading

_registry_guard = threading.Lock()
_locks: dict[str, threading.Lock] = {}


class FileLockBusy(RuntimeError):
    pass


@contextmanager
def exclusive_file_lock(path: str | Path):
    path = Path(path)
    key = str(path.resolve())
    with _registry_guard:
        lock = _locks.setdefault(key, threading.Lock())
    if not lock.acquire(blocking=False):
        raise FileLockBusy("会话正在处理另一个请求，请稍后重试。")
    handle = None
    acquired = False
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        handle = path.open("a+b")
        if os.fstat(handle.fileno()).st_size == 0:
            handle.write(b"\0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            acquired = True
        except OSError:
            raise FileLockBusy("会话正在另一进程中处理，请稍后重试。") from None
        yield
    finally:
        if handle is not None:
            if acquired:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            handle.close()
        lock.release()
