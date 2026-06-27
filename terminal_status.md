# RAPHAEL — Background Processes Status
Last Updated: `2026-06-28 19:36:02`

## 1. FastAPI Backend (run.py)
* **Status**: STOPPED

### Recent Output:
```text
Successfully scheduled one-shot timer.
Expected to fire at: 2026-06-28T19:29:26+05:30
Prompt: Check if uvicorn started successfully and test root URL serving

[2026-06-28T19:29:21+05:30] Still waiting. Remaining time: 5s
[2026-06-28T19:29:26+05:30] Timer fired.

```

## 2. Background Scheduler (scheduler.py)
* **Status**: RUNNING
* **Process ID**: `25468`
* **Command**: `C:\Users\harsh\anaconda3\envs\raphael-env\python.exe scheduler.py`
* **Started**: `2026-06-28 17:13:20`

### Recent Output:
```text
[anomaly] Insufficient data for lst: 0 obs (need 10+)
[anomaly] Insufficient data for ndvi: 0 obs (need 10+)
[anomaly] Insufficient data for fire: 0 obs (need 10+)
[forecast] Insufficient data for aq in zone d4ebad59: 5 obs (need 30)
[forecast] Insufficient data for lst in zone d4ebad59: 0 obs (need 30)
[forecast] Insufficient data for aq in zone 2a1ee36f: 4 obs (need 30)
[forecast] Insufficient data for lst in zone 2a1ee36f: 0 obs (need 30)
[forecast] Insufficient data for aq in zone be92136d: 4 obs (need 30)
[forecast] Insufficient data for lst in zone be92136d: 0 obs (need 30)
[clustering] Not enough zones with data: 3 (need 5)
[clustering] Fallback: assigned 6 zones to clusters
[risk] Computed risk scores for 3 zones
2026-06-28 19:13:49 [info     ] Starting rule-based alerts evaluation cycle region_id=98ec65e1-bcf2-487d-95fe-2e68954558d4
2026-06-28 19:13:49 [info     ] No active alert rules to evaluate
2026-06-28 19:13:49 [info     ] gaussian_plume_complete        pg_class=D receptors=48 sources=8 wind_ms=7.7

```

---
*Note: This status file is updated automatically every second by the background status monitor daemon.*
