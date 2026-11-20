#!/usr/bin/env python3
"""
scheduler.py  —  Autonomous Job Agent Scheduler
Roz subah automatically job agent run karta hai.
Run: python job-agent/scheduler.py
"""

import schedule
import time
import subprocess
import sys
import os
import datetime

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
APP_SCRIPT  = os.path.join(SCRIPT_DIR, "app.py")
LOG_FILE    = os.path.join(SCRIPT_DIR, "data", "scheduler.log")

# ────────────────────────────────────────────────
# Kitne baje run karna hai?  (24-hour format)
RUN_TIMES = ["09:00", "15:00"]   # Subah 9 baje aur dopahar 3 baje
# ────────────────────────────────────────────────


def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def run_agent():
    log("=" * 60)
    log("🚀 Scheduled run starting...")
    try:
        result = subprocess.run(
            [sys.executable, APP_SCRIPT],
            cwd=SCRIPT_DIR,
            capture_output=False,   # output terminal mein dikhega
        )
        log(f"✅ Agent finished. Exit code: {result.returncode}")
    except Exception as e:
        log(f"❌ Agent crashed: {e}")
    log("=" * 60)


def main():
    log("🕐 Scheduler started!")
    log(f"📅 Will run at: {', '.join(RUN_TIMES)} every day")

    for t in RUN_TIMES:
        schedule.every().day.at(t).do(run_agent)

    # Also run immediately on first start
    log("▶️  Running immediately on startup...")
    run_agent()

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
