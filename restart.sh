#!/bin/bash
# Usage: ./restart.sh [--work SECONDS]
# Defaults to 20 minutes. Example: ./restart.sh --work 60

cd "$(dirname "$0")"

pkill -9 -f "python.*app.py" 2>/dev/null

# Wait until all matching processes are gone
for i in $(seq 1 10); do
    pgrep -f "python.*app.py" > /dev/null 2>&1 || break
    sleep 0.3
done

rm -f /tmp/eye-strain-timer.lock

source .venv/bin/activate
python src/app.py "$@" &
