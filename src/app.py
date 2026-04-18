import atexit
import csv
import os
import signal
import subprocess
import sys
import threading
from datetime import date, datetime
from pathlib import Path

import objc
import rumps
from AppKit import NSWorkspace
from Foundation import NSObject

WORK_SECONDS = 20 * 60
BREAK_SECONDS = 25
SNOOZE_SECONDS = 1 * 60

LOCKFILE = Path("/tmp/eye-strain-timer.lock")
LOG_FILE = Path.home() / ".eye-strain-timer" / "log.csv"


def _cleanup_lock():
    LOCKFILE.unlink(missing_ok=True)


def ensure_singleton():
    if LOCKFILE.exists():
        try:
            pid = int(LOCKFILE.read_text().strip())
            os.kill(pid, 0)
            print(f"Already running (PID {pid}). Exiting.")
            sys.exit(0)
        except (ProcessLookupError, ValueError):
            pass
    LOCKFILE.write_text(str(os.getpid()))
    atexit.register(_cleanup_lock)

    def _sigterm(*_):
        _cleanup_lock()
        os._exit(0)

    signal.signal(signal.SIGTERM, _sigterm)


def log_break(result: str):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a", newline="") as f:
        csv.writer(f).writerow([datetime.now().isoformat(timespec="seconds"), result])


def load_today_counts() -> tuple[int, int]:
    if not LOG_FILE.exists():
        return 0, 0
    today = date.today().isoformat()
    total = successes = 0
    with open(LOG_FILE, newline="") as f:
        for row in csv.reader(f):
            if row and row[0].startswith(today):
                total += 1
                if row[1] == "success":
                    successes += 1
    return successes, total


class SleepWakeObserver(NSObject):
    def initWithApp_(self, app):
        self = objc.super(SleepWakeObserver, self).init()
        if self is not None:
            self._app = app
            nc = NSWorkspace.sharedWorkspace().notificationCenter()
            nc.addObserver_selector_name_object_(
                self, "onSleep:", "NSWorkspaceWillSleepNotification", None
            )
            nc.addObserver_selector_name_object_(
                self, "onWake:", "NSWorkspaceDidWakeNotification", None
            )
        return self

    def onSleep_(self, _notification):
        self._app.on_sleep()

    def onWake_(self, _notification):
        self._app.on_wake()


class EyeStrainTimer(rumps.App):
    def __init__(self, work_seconds=WORK_SECONDS, break_seconds=BREAK_SECONDS):
        super().__init__("👁", quit_button=None)
        self._work_seconds = work_seconds
        self._break_seconds = break_seconds
        self.remaining = work_seconds
        self.on_break = False
        self.pending_break = False  # waiting for user to confirm break start
        self._popup_response = None  # set by popup thread: 'done', 'snooze'
        self.paused = False
        self._sleeping = False
        self._stats = load_today_counts()

        self.status_item = rumps.MenuItem("", callback=None)
        self.stats_item = rumps.MenuItem("", callback=None)
        self.pause_item = rumps.MenuItem("Pause", callback=self.toggle_pause)
        self.start_break_item = rumps.MenuItem("Start Break", callback=self.start_break)
        self.snooze_item = rumps.MenuItem("Snooze 1 min", callback=self.snooze)
        self.menu = [
            self.status_item,
            self.stats_item,
            None,
            self.start_break_item,
            self.snooze_item,
            self.pause_item,
            rumps.MenuItem("Reset", callback=self.reset),
            None,
            rumps.MenuItem("Quit", callback=self._quit),
        ]

        self._observer = SleepWakeObserver.alloc().initWithApp_(self)
        self._update_display()
        rumps.Timer(self.tick, 1).start()

    def on_sleep(self):
        self._sleeping = True

    def on_wake(self):
        self._sleeping = False
        if not self.on_break:
            self.pending_break = False
            self.remaining = self._work_seconds
            self._update_display()

    def tick(self, _sender):
        if self._popup_response:
            response, self._popup_response = self._popup_response, None
            if response == "done":
                self.pending_break = False
                self._end_break()
            elif response == "snooze":
                self.snooze(None)
            return
        if self.paused or self._sleeping or self.pending_break:
            return
        self.remaining -= 1
        if self.remaining <= 0:
            if self.on_break:
                self._end_break()
            else:
                self._prompt_break()
        else:
            self._update_display()

    def _prompt_break(self):
        self.pending_break = True
        self._update_display()
        threading.Thread(target=self._show_break_popup, daemon=True).start()

    def _show_break_popup(self):
        confirm = (
            'display dialog "Time for an eye break!" '
            'buttons {"Snooze 1 min", "Start Break"} '
            'default button "Start Break" '
            'with title "Eye Strain Timer"'
        )
        result = subprocess.run(["osascript", "-e", confirm], capture_output=True, text=True)
        if not self.pending_break:
            return
        if result.returncode != 0 or "Snooze" in result.stdout:
            self._popup_response = "snooze"
            return

        break_dlg = (
            f'display dialog "Look at something 20 feet away...\\n\\n'
            f'This will close automatically when your break is done." '
            f'buttons {{"End Early"}} '
            f'default button "End Early" '
            f'with title "Eye Break ({self._break_seconds}s)" '
            f'giving up after {self._break_seconds}'
        )
        result2 = subprocess.run(["osascript", "-e", break_dlg], capture_output=True, text=True)
        if not self.pending_break:
            return
        if "gave up:true" in result2.stdout:
            self._popup_response = "done"
        else:
            self._popup_response = "snooze"

    def start_break(self, _sender):
        if not self.pending_break:
            return
        self.pending_break = False
        self.on_break = True
        self.remaining = self._break_seconds
        self._update_display()

    def _end_break(self):
        log_break("success")
        s, t = self._stats
        self._stats = (s + 1, t + 1)
        self.on_break = False
        self.remaining = self._work_seconds
        rumps.notification(
            "Eye Strain Timer",
            "Break over!",
            "Next break in 20 minutes.",
            sound=True,
        )
        self._update_display()

    def _record_skip(self):
        log_break("skipped")
        s, t = self._stats
        self._stats = (s, t + 1)

    def _update_display(self):
        active = self.on_break or self.pending_break
        self.snooze_item.set_callback(self.snooze if active else None)
        self.start_break_item.set_callback(self.start_break if self.pending_break else None)
        s, t = self._stats
        self.stats_item.title = f"Today: {s}/{t}"
        if self.pending_break:
            self.title = "REST?"
            self.status_item.title = "Break time — press Start Break when ready"
        elif self.on_break:
            self.title = f"Break {self.remaining}s"
            self.status_item.title = f"Break: {self.remaining}s remaining"
        else:
            m, s = divmod(self.remaining, 60)
            self.title = f"{m:02d}:{s:02d}"
            self.status_item.title = f"Next break in {m:02d}:{s:02d}"

    def snooze(self, _sender):
        self._record_skip()
        self.pending_break = False
        self.on_break = False
        self.remaining = SNOOZE_SECONDS
        self._update_display()

    def toggle_pause(self, sender):
        self.paused = not self.paused
        sender.title = "Resume" if self.paused else "Pause"
        if self.paused:
            self.title = "⏸"

    def reset(self, _sender):
        if self.on_break or self.pending_break:
            self._record_skip()
        self.paused = False
        self.on_break = False
        self.pending_break = False
        self.remaining = self._work_seconds
        self.pause_item.title = "Pause"
        self._update_display()

    def _quit(self, _sender):
        LOCKFILE.unlink(missing_ok=True)
        rumps.quit_application()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--work", type=int, default=WORK_SECONDS, help="Override initial work timer (seconds)")
    parser.add_argument("--break-time", type=int, default=BREAK_SECONDS, help="Override break duration (seconds)")
    args = parser.parse_args()

    ensure_singleton()
    EyeStrainTimer(work_seconds=args.work, break_seconds=args.break_time).run()
