import atexit
import os
import signal
import sys
from pathlib import Path


class SingletonLock:
    """File-based process lock. Can be replaced with socket-based or fcntl-based locking."""

    def __init__(self, lockfile: Path):
        self.lockfile = lockfile

    def acquire(self) -> bool:
        """
        Acquire the lock. If already held by a running process, exit.
        Returns True if acquired, False if already held.
        """
        if self.lockfile.exists():
            try:
                pid = int(self.lockfile.read_text().strip())
                os.kill(pid, 0)  # check process exists
                print(f"Already running (PID {pid}). Exiting.")
                return False
            except ProcessLookupError:
                pass  # process doesn't exist, stale lock — continue to acquire
            except PermissionError:
                # process exists but we can't signal it — treat as running
                pid = int(self.lockfile.read_text().strip())
                print(f"Already running (PID {pid}). Exiting.")
                return False
            except ValueError:
                pass  # invalid PID in lockfile, treat as stale

        self.lockfile.write_text(str(os.getpid()))
        atexit.register(self.release)

        def _sigterm(*_):
            self.release()
            os._exit(0)

        signal.signal(signal.SIGTERM, _sigterm)
        return True

    def release(self):
        """Remove the lockfile."""
        self.lockfile.unlink(missing_ok=True)
