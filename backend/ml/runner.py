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
