from contextlib import contextmanager
import fcntl
import logging
import os
from pathlib import Path
from typing import Iterator

from .exception import LockError

logger = logging.getLogger(__name__)


@contextmanager
def process_lock(
    lock_path: Path = Path("/tmp/frappe_backup_manager.lock"),
) -> Iterator[None]:
    lock_file = open(lock_path, mode="w", encoding="utf-8")

    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock_file.write(f"{os.getpid()}\n")
        lock_file.flush()
        logger.debug("Acquired process lock at %s (PID %d)", lock_path, os.getpid())
        yield
    except BlockingIOError as exc:
        raise LockError(
            f"Another instance of backup_manager is currently running (lock held: {lock_path})."
        ) from exc
    finally:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
        lock_file.close()