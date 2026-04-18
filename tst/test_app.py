import csv
import sys
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Stub out Cocoa/rumps with minimal fakes before importing src
# ---------------------------------------------------------------------------

class _FakeApp:
    def __init__(self, *args, **kwargs):
        self.title = ""
        self.menu = []

class _FakeMenuItem:
    def __init__(self, title="", callback=None):
        self.title = title
        self._cb = callback
    def set_callback(self, cb):
        self._cb = cb

class _FakeTimer:
    def __init__(self, *a, **kw): pass
    def start(self): pass

_rumps = MagicMock()
_rumps.App = _FakeApp
_rumps.MenuItem = _FakeMenuItem
_rumps.Timer = _FakeTimer
_rumps.notification = MagicMock()

for _mod in ("AppKit", "Foundation", "objc"):
    sys.modules[_mod] = MagicMock()
sys.modules["rumps"] = _rumps

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import app as _app
from app import SNOOZE_SECONDS, load_today_counts, log_break


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_timer(work=10, brk=5):
    with patch.object(_app, "SleepWakeObserver"), \
         patch.object(_app, "load_today_counts", return_value=(0, 0)):
        t = _app.EyeStrainTimer(work_seconds=work, break_seconds=brk)
    t._update_display = MagicMock()
    return t


# ---------------------------------------------------------------------------
# log_break / load_today_counts
# ---------------------------------------------------------------------------

def test_log_break_appends_row(tmp_path):
    with patch.object(_app, "LOG_FILE", tmp_path / "log.csv"):
        log_break("success")
        log_break("skipped")
        rows = list(csv.reader(open(_app.LOG_FILE)))
    assert len(rows) == 2
    assert rows[0][1] == "success"
    assert rows[1][1] == "skipped"


def test_load_today_counts_no_file(tmp_path):
    with patch.object(_app, "LOG_FILE", tmp_path / "log.csv"):
        assert load_today_counts() == (0, 0)


def test_load_today_counts_today_only(tmp_path):
    log = tmp_path / "log.csv"
    today = date.today().isoformat()
    with open(log, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([f"{today}T10:00:00", "success"])
        w.writerow([f"{today}T10:20:00", "success"])
        w.writerow([f"{today}T10:40:00", "skipped"])
        w.writerow(["2000-01-01T10:00:00", "success"])  # old — excluded
    with patch.object(_app, "LOG_FILE", log):
        successes, total = load_today_counts()
    assert successes == 2
    assert total == 3


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------

def test_initial_state():
    t = make_timer(work=300, brk=25)
    assert t.remaining == 300
    assert not t.on_break
    assert not t.pending_break
    assert not t.paused


def test_prompt_break_sets_pending():
    t = make_timer()
    with patch("threading.Thread") as mock_thread:
        mock_thread.return_value = MagicMock()
        t._prompt_break()
    assert t.pending_break
    mock_thread.assert_called_once()


def test_popup_done_ends_break():
    t = make_timer(work=300)
    t.pending_break = True
    t._popup_response = "done"
    with patch.object(_app, "log_break"):
        t.tick(None)
    assert not t.pending_break
    assert not t.on_break
    assert t.remaining == 300


def test_popup_snooze_snoozes():
    t = make_timer(work=300)
    t.pending_break = True
    t._popup_response = "snooze"
    with patch.object(_app, "log_break"):
        t.tick(None)
    assert not t.pending_break
    assert t.remaining == SNOOZE_SECONDS


def test_snooze_records_skip_and_resets():
    t = make_timer(work=300)
    t.pending_break = True
    t._stats = (2, 3)
    with patch.object(_app, "log_break") as mock_log:
        t.snooze(None)
    mock_log.assert_called_once_with("skipped")
    assert t._stats == (2, 4)
    assert t.remaining == SNOOZE_SECONDS
    assert not t.pending_break


def test_end_break_records_success_and_resets():
    t = make_timer(work=300)
    t.on_break = True
    t._stats = (1, 2)
    with patch.object(_app, "log_break") as mock_log:
        t._end_break()
    mock_log.assert_called_once_with("success")
    assert t._stats == (2, 3)
    assert not t.on_break
    assert t.remaining == 300


def test_reset_during_pending_records_skip():
    t = make_timer(work=300)
    t.pending_break = True
    t._stats = (0, 0)
    with patch.object(_app, "log_break") as mock_log:
        t.reset(None)
    mock_log.assert_called_once_with("skipped")
    assert not t.pending_break
    assert t.remaining == 300


def test_tick_counts_down():
    t = make_timer(work=5)
    t.tick(None)
    assert t.remaining == 4


def test_tick_paused_does_not_count():
    t = make_timer(work=5)
    t.paused = True
    t.tick(None)
    assert t.remaining == 5


def test_tick_pending_does_not_count():
    t = make_timer(work=5)
    t.pending_break = True
    t.tick(None)
    assert t.remaining == 5


def test_tick_triggers_prompt_at_zero():
    t = make_timer(work=1)
    with patch.object(t, "_prompt_break") as mock_prompt:
        t.tick(None)
    mock_prompt.assert_called_once()
