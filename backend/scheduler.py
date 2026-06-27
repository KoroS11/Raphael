"""
Raphael — Background Scheduler (Task 1C)

Runs on APScheduler (BlockingScheduler). No Prefect dependency.
Orchestrates:
  • Every hour  — OpenAQ, WAQI, IQAir, OpenMeteo, GDACS ingestion
  • Every 3h    — FIRMS fire detection ingestion
  • Every 24h   — MODIS LST daily ingestion
  • Every hour  — ML Intelligence Cycle (runs *after* ingestion completes)

Usage:
    python scheduler.py

The scheduler is intended to be launched as a long-running background
process alongside the FastAPI server. On Windows, start it in a second
terminal or wrap in a service manager (e.g. NSSM).
"""

import sys
