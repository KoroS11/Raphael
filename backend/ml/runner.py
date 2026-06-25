"""
Raphael — Intelligence Cycle Runner (Five-Stage Orchestrator)

Orchestrates the full intelligence pipeline:
  Stage 1 — DETECT    (IsolationForest anomaly detection)
  Stage 2 — ATTRIBUTE (Rule-based + RandomForest hybrid)
  Stage 3 — FORECAST  (Prophet per zone per layer)
  Stage 4 — DECIDE    (Risk scorer + action recommender)
  Stage 5 — DISPERSE  (Gaussian Plume dispersion model)

Every stage emits WebSocket events (type: trace, anomaly, forecast,
risk_score, plume) so the frontend reasoning trace panel shows live ML
activity.
"""
import sys
import os
import asyncio

# Windows DLL overrides for MKL/OMP and Stan compiler
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
conda_prefix = os.environ.get("CONDA_PREFIX") or r"C:\Users\harsh\anaconda3\envs\raphael-env"
lib_bin = os.path.join(conda_prefix, "Library", "bin")
if os.path.exists(lib_bin) and lib_bin not in os.environ["PATH"]:
    os.environ["PATH"] = lib_bin + os.pathsep + os.environ["PATH"]

from datetime import datetime, timezone
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from sqlalchemy import text
from db.connection import SessionLocal
from db.models import Region, RawObservation, MLOutput

# CRITICAL: Force SpatiaLite DLL loading before scikit-learn/prophet imports to prevent Windows DLL conflict crash
_preloaded_db = SessionLocal()
try:
    _preloaded_db.query(Region).first()
except Exception:
    pass

from ml.anomaly import detect_anomalies
from ml.attribution import AnomalyAttributor
from ml.forecast import train_and_forecast
from ml.clustering import cluster_zones
from ml.risk_score import compute_all_risk_scores
from ml.explainer import generate_ai_insights
from ml.plume import run_gaussian_plume
from api.routes.ws import broadcast
import structlog

log = structlog.get_logger()

# Singleton attributor — retrained periodically
attributor = AnomalyAttributor()


def broadcast_sync(event: dict):
    """
    Broadcast event to the active event loop if one is running.
    Allows synchronous ML code to dispatch events to FastAPI websockets.
    """
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            loop.create_task(broadcast(event))
    except RuntimeError:
        # No running event loop (e.g. running from CLI or Prefect)
        pass


def run_intelligence_cycle(region_id: str = None, db: Session = None):
    """
    Execute the full four-stage intelligence cycle.
    Broadcasts WebSocket events at each step for the frontend trace panel.
    """
    db_created = False
    if not db:
        if '_preloaded_db' in globals() and _preloaded_db:
            db = _preloaded_db
        else:
            db = SessionLocal()
            db_created = True
    try:
        if not region_id:
            region = db.query(Region).filter(
                Region.is_active == True
            ).first()
            if not region:
                log.error("No active region found")
                return {"status": "error", "message": "No active region"}
            region_id = str(region.id)

        # Train RF attributor if not already trained
        if not attributor.is_trained:
            trained = attributor.fit(db)
            if trained:
                broadcast_sync({
                    "type": "trace",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "payload": {
                        "source": "attribution",
                        "message": "RandomForest attributor trained on historical anomalies"
                    }
                })

        broadcast_sync({
            "type": "trace",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "source": "intelligence_runner",
                "message": "Intelligence cycle started — "
                           "Detect \u2192 Attribute \u2192 Forecast \u2192 Decide \u2192 Disperse"
            }
        })

        # ── STAGE 1: DETECT ──────────────────────────────────────
        broadcast_sync({
            "type": "trace",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "source": "intelligence_runner",
                "message": "\u2501\u2501 STAGE 1: DETECT (IsolationForest) \u2501\u2501"
            }
        })

        anomaly_counts = {}
        for layer in ["aq", "lst", "ndvi", "fire"]:
            count = detect_anomalies(db, region_id, layer)
            anomaly_counts[layer] = count

            broadcast_sync({
                "type": "trace",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {
                    "source": "isolation_forest",
                    "message": (
                        f"[{layer.upper()}] {count} anomalies detected "
                        f"in rolling 7-day window"
                    )
                }
            })

        total_anomalies = sum(anomaly_counts.values())
        broadcast_sync({
            "type": "trace",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "source": "intelligence_runner",
                "message": f"Detection complete: {total_anomalies} total anomalies"
            }
        })

        # ── STAGE 1b: PCAD PHYSICS CORROBORATION ─────────────────
        try:
            from ml.pcad import compute_pcad_scores
            pcad_df = compute_pcad_scores(db, region_id=region_id)
            if not pcad_df.empty:
                high_conf = len(pcad_df[pcad_df['confidence']=='HIGH'])
                med_conf = len(pcad_df[pcad_df['confidence']=='MEDIUM'])
                log.info("pcad_complete",
                         high_confidence=high_conf,
                         medium_confidence=med_conf,
                         total_anomalies=int(pcad_df['if_anomaly'].sum()))
                broadcast_sync({
                    "type": "trace",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "payload": {
                        "source": "pcad",
                        "message": (
                            f"PCAD: {high_conf} HIGH, {med_conf} MEDIUM "
                            f"confidence anomalies detected"
                        )
                    }
                })
        except Exception as pe:
            log.error("pcad_failed", error=str(pe))

        # ── STAGE 1e: SYMBOLIC RECONCILIATION + GEMMA EXPLANATION ──
        try:
            from ml.symbolic import run_symbolic_layer
            from ml.explain import generate_explanation

            annotated = run_symbolic_layer(db, region_id=region_id)

            if annotated:
                n_evidence = len(annotated)
                broadcast_sync({
                    "type": "trace",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "payload": {
                        "source": "blue_team",
                        "message": f"Blue Team: {n_evidence} evidence objects aggregated"
                    }
                })

                n_fragile = sum(1 for r in annotated if r["challenge"] and r["challenge"]["robustness"] == "FRAGILE")
                n_robust = n_evidence - n_fragile
                broadcast_sync({
                    "type": "trace",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "payload": {
                        "source": "red_team",
                        "message": f"Red Team: {n_evidence} anomalies reviewed, {n_fragile} FRAGILE, {n_robust} ROBUST"
                    }
                })

                verdict_counts = {}
                for record in annotated:
                    v = record["verdict"]
                    verdict_counts[v] = verdict_counts.get(v, 0) + 1

                log.info(f"symbolic_reconciliation_complete verdict_counts={verdict_counts} n_total={len(annotated)}")

                explained_count = 0
                for record in annotated:
                    if record["verdict"] != "NORMAL":
                        result = generate_explanation(record)
                        if result["status"] == "ok":
                            explained_count += 1
                            log.info(f"gemma_explanation_generated station={record['evidence']['station_name']} verdict={record['verdict']}")

                broadcast_sync({
                    "type": "trace",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "payload": {
                        "source": "symbolic_and_gemma",
                        "message": (
                            f"Symbolic Layer: {verdict_counts}. "
                            f"Gemma: {explained_count} explanations generated"
                        )
                    }
                })
        except Exception as se:
            log.error(f"symbolic_or_gemma_failed error={se}")

        # ── STAGE 2: ATTRIBUTE ───────────────────────────────────
        broadcast_sync({
            "type": "trace",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "source": "intelligence_runner",
                "message": "\u2501\u2501 STAGE 2: ATTRIBUTE (Rule + RF Hybrid) \u2501\u2501"
            }
        })

        # Get recently flagged anomalies
        anomalies = db.execute(text("""
            SELECT id, layer_type, value, anomaly_score,
                   CAST(strftime('%H', observed_at) AS INTEGER) as hour,
                   CAST(strftime('%w', observed_at) AS INTEGER) as day_of_week,
                   CAST(strftime('%m', observed_at) AS INTEGER) as month
            FROM raw_observations
            WHERE is_anomalous = 1
              AND observed_at >= datetime('now', '-24 hours')
        """)).fetchall()

        attributions = []
        # Fetch weather context ONCE before attribution loop
        weather_context = db.execute(text("""
            SELECT station_id, value, unit, station_name
            FROM raw_observations
            WHERE layer_type = 'weather'
              AND observed_at >= datetime('now', '-6 hours')
            ORDER BY observed_at DESC
            LIMIT 20
        """)).fetchall()

        # Extract wind speed once
        wind_speed = next(
            (w.value for w in weather_context
             if w.unit and 'wind' in w.unit.lower()),
            8.0
        )

        # Also fetch NDVI context once
        ndvi_context = db.execute(text("""
            SELECT AVG(value) as avg_ndvi
            FROM raw_observations
            WHERE layer_type = 'ndvi'
              AND observed_at >= datetime('now', '-24 hours')
        """)).scalar() or 0.15

        # Fetch nearby fire count once
        fire_count = db.execute(text("""
            SELECT COUNT(*) FROM raw_observations
            WHERE layer_type = 'fire'
              AND observed_at >= datetime('now', '-24 hours')
        """)).scalar() or 0

        # NOW run attribution loop with pre-fetched context
        for anomaly in anomalies[:20]:
            obs_dict = {
                "layer_type":    anomaly.layer_type,
                "anomaly_score": anomaly.anomaly_score or 0,
                "hour":          anomaly.hour or 12,
                "day_of_week":   anomaly.day_of_week or 0,
                "month":         anomaly.month or 6,
            }
            context_dict = {
                "wind_speed":             wind_speed,
                "lst_value":              anomaly.value
                                          if anomaly.layer_type == "lst" else 38.0,
                "ndvi_value":             ndvi_context,
                "pm10_pm25_ratio":        1.8,
                "zone_industrial":        False,
                "neighbor_anomaly_count": anomaly_counts.get(anomaly.layer_type, 0),
                "fire_count_nearby":      fire_count,
            }

            attribution = attributor.attribute(obs_dict, context_dict)
            attributions.append(attribution)

