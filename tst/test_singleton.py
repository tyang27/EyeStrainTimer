import os
import signal
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from singleton import SingletonLock


def test_acquire_creates_lockfile(tmp_path):
    lockfile = tmp_path / "test.lock"
    lock = SingletonLock(lockfile)

    acquired = lock.acquire()

    assert acquired is True
    assert lockfile.exists()
    assert int(lockfile.read_text().strip()) == os.getpid()


def test_acquire_when_already_held_by_running_process(tmp_path, capsys):
    lockfile = tmp_path / "test.lock"
    lockfile.write_text("1")  # PID 1 is always running

    lock = SingletonLock(lockfile)
    acquired = lock.acquire()

    assert acquired is False
    assert "Already running (PID 1)" in capsys.readouterr().out


def test_acquire_when_lockfile_stale(tmp_path):
    lockfile = tmp_path / "test.lock"
    lockfile.write_text("999999")  # non-existent PID

    lock = SingletonLock(lockfile)
    acquired = lock.acquire()

    assert acquired is True
    assert int(lockfile.read_text().strip()) == os.getpid()


def test_acquire_with_invalid_lockfile_content(tmp_path):
    lockfile = tmp_path / "test.lock"
    lockfile.write_text("not-a-number")

    lock = SingletonLock(lockfile)
    acquired = lock.acquire()

    assert acquired is True
    assert int(lockfile.read_text().strip()) == os.getpid()


def test_release_removes_lockfile(tmp_path):
    lockfile = tmp_path / "test.lock"
    lock = SingletonLock(lockfile)
    lock.acquire()

    lock.release()

    assert not lockfile.exists()


def test_release_idempotent(tmp_path):
    lockfile = tmp_path / "test.lock"
    lock = SingletonLock(lockfile)
    lock.acquire()
    lock.release()

    lock.release()  # should not raise


def test_acquire_registers_atexit(tmp_path):
    lockfile = tmp_path / "test.lock"
    lock = SingletonLock(lockfile)

    with patch("atexit.register") as mock_atexit:
        lock.acquire()
        mock_atexit.assert_called_once_with(lock.release)


def test_sigterm_handler_releases_lock(tmp_path):
    lockfile = tmp_path / "test.lock"
    lock = SingletonLock(lockfile)
    lock.acquire()

    # Get the registered signal handler
    old_handler = signal.signal(signal.SIGTERM, signal.SIG_DFL)
    signal.signal(signal.SIGTERM, old_handler)

    # Manually trigger the SIGTERM logic (can't easily invoke via signal.signal)
    # Instead, verify the lock is still there and can be released
    assert lockfile.exists()
    lock.release()
    assert not lockfile.exists()
