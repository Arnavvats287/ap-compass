"""Process ownership for one local SQLite database and its run reconciliation."""
from contextlib import contextmanager
import os


@contextmanager
def own_database(database):
    # The inode remains in place: unlinking it could allow a second lock on a new inode.
    lock = database.with_name(database.name + ".instance.lock")
    database.parent.mkdir(parents=True, exist_ok=True)
    with lock.open("a+b") as handle:
        try:
            if os.name == "nt":
                import msvcrt

                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise RuntimeError("AP Compass database already in use or instance lock unavailable") from None
        yield  # Closing the owned descriptor releases its OS lock, including on startup failure.
