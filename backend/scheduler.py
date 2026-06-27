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
import os
import logging
import time
from datetime import datetime, timezone

# ── Path bootstrap ───────────────────────────────────────────────────────────
_backend_dir = os.path.dirname(os.path.abspath(__file__))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger("raphael.scheduler")

# ── APScheduler ──────────────────────────────────────────────────────────────
try:
