# Eye Strain Timer

A macOS menu bar app that enforces the 20-20-20 rule to reduce eye strain during screen time.

## Background

The 20-20-20 rule: every 20 minutes, look at something 20 feet away for 20 seconds. This app automates the reminder and tracks compliance over time.

## Product Requirements

- **Countdown**: display a live `MM:SS` countdown in the menu bar
- **Break prompt**: after 20 minutes, notify the user and start a 25-second break countdown (extra 5 seconds to prepare before looking away)
- **Snooze**: if not ready to look away, snooze for 1 minute via the menu; counts as a skip
- **Auto-cycle**: after the break completes, reset and start the next 20-minute work interval automatically
- **Pause / Resume**: manually pause and resume the timer
- **Reset**: cancel current state and restart the work timer; counts as a skip if triggered during a break
- **Sleep awareness**: timer pauses on system sleep; on wake, the work timer resets to 20:00 (screen time didn't accumulate)
- **Break tracking**: log every break to `~/.eye-strain-timer/log.csv` with a timestamp and result (`success` or `skipped`); display today's score as `Today: X/Y` in the menu
- **Singleton**: only one instance runs at a time; launching a second exits immediately

## Implementation

**Language / framework**: Python 3.9+, [`rumps`](https://github.com/jaredks/rumps) for the menu bar UI.

**Sleep / wake detection**: `NSWorkspaceWillSleepNotification` and `NSWorkspaceDidWakeNotification` via `AppKit`/`Foundation` (PyObjC). A `SleepWakeObserver` NSObject subclass registers for these notifications and calls back into the app.

**Singleton**: on launch, writes PID to `/tmp/eye-strain-timer.lock`. If the lockfile exists and the PID is alive, the new process exits. Lockfile is removed on exit via `atexit`.

**Break log**: append-only CSV at `~/.eye-strain-timer/log.csv`. Columns: ISO 8601 timestamp, result. Today's counts are loaded from the file at startup and maintained in memory thereafter to avoid per-second file reads.

**Success vs. skip**:
- Success — break countdown reaches 0 naturally
- Skip — snooze clicked during a break, or reset triggered during a break

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

## Log Format

```
2026-04-17T09:14:00,success
2026-04-17T09:35:22,skipped
2026-04-17T09:57:00,success
```
