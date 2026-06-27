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
    from apscheduler.schedulers.blocking import BlockingScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
except ImportError as e:
    log.critical("APScheduler not installed. Run: pip install apscheduler>=3.10.0")
    raise


# ════════════════════════════════════════════════════════════════════════════
# INGESTION JOB WRAPPERS
# Each wrapper imports the flow lazily (avoids import-time side-effects)
# and calls the flow with default parameters (Pune region).
# ════════════════════════════════════════════════════════════════════════════

def _safe_run(label: str, fn, *args, **kwargs):
    """Execute fn with basic error isolation and timing."""
    started = datetime.now(timezone.utc)
    try:
        log.info("[%s] starting", label)
        result = fn(*args, **kwargs)
        elapsed = (datetime.now(timezone.utc) - started).total_seconds()
        log.info("[%s] finished in %.1fs — %s", label, elapsed, result)
        return result
    except Exception as exc:
        elapsed = (datetime.now(timezone.utc) - started).total_seconds()
        log.error("[%s] FAILED after %.1fs: %s", label, elapsed, exc, exc_info=True)


def job_openaq():
    from ingestion.flows.aq_openaq import openaq_flow
    _safe_run("openaq", openaq_flow)


def job_waqi():
    from ingestion.flows.aq_waqi import waqi_flow
    _safe_run("waqi", waqi_flow)


def job_iqair():
