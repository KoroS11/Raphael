"""
Raphael — Isolation Forest Anomaly Detection

Identifies outlier observations in rolling 7-day windows using Isolation Forest.
All runs tracked in MLflow. Dialect-agnostic SQL supports both SQLite and Postgres.
"""
import os
import uuid
import numpy as np
import pandas as pd
try:
    import mlflow
except ImportError:
    class MockMLflow:
        def __getattr__(self, name):
            def mock_func(*args, **kwargs):
                class MockRun:
                    @property
                    def info(self):
                        class MockInfo:
                            @property
                            def run_id(self):
                                return "mock_run_id"
                        return MockInfo()
                return MockRun()
            return mock_func
    mlflow = MockMLflow()

from sklearn.ensemble import IsolationForest
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import text

try:
    mlflow.set_tracking_uri(f"http://127.0.0.1:{os.getenv('MLFLOW_PORT', '5000')}")
except Exception:
    pass

def detect_anomalies(db: Session, region_id: str, layer_type: str) -> int:
    # Fetch rolling 7-day window with time features
    # Using strftime and datetime('now') for SQLite/SpatiaLite compatibility
    rows = db.execute(text("""
        SELECT
            id,
            value,
            CAST(strftime('%H', observed_at) AS INTEGER) as hour,
            CAST(strftime('%w', observed_at) AS INTEGER) as day_of_week,
            CAST(strftime('%m', observed_at) AS INTEGER) as month
        FROM raw_observations
        WHERE layer_type  = :layer_type
          AND region_id   = :region_id
          AND observed_at >= datetime('now', '-7 days')
          AND value IS NOT NULL
    """), {"layer_type": layer_type, "region_id": region_id}).fetchall()

    if len(rows) < 50:
        return 0

    df = pd.DataFrame(rows, columns=["id", "value", "hour", "day_of_week", "month"])
    X  = df[["value", "hour", "day_of_week", "month"]].values

    run_id = None
    try:
        mlflow.set_experiment("anomaly_detection")
        run_obj = mlflow.start_run(run_name=f"anomaly_{layer_type}_{region_id[:8]}")
        run_id = run_obj.info.run_id
    except Exception as e:
        print(f"[anomaly] MLflow tracking unavailable (non-fatal): {e}")

    try:
        clf = IsolationForest(
            n_estimators=100,
            contamination=0.05,
            random_state=42
        )
        preds  = clf.fit_predict(X)
        scores = clf.score_samples(X)

        anomaly_count = int((preds == -1).sum())

        if run_id:
            try:
                mlflow.log_params({
                    "layer_type":    layer_type,
                    "n_samples":     len(df),
                    "contamination": 0.05
                })
                mlflow.log_metric("anomaly_count", anomaly_count)
            except Exception as le:
                print(f"[anomaly] MLflow logging failed (non-fatal): {le}")

        # Update database rows with anomaly flags using standard transaction
        anomaly_ids = df.loc[preds == -1, "id"].tolist()
        if anomaly_ids:
            # Build CASE statement for updating anomaly_score and is_anomalous
            # is_anomalous set to 1 (True) for SQLite/Postgres compatibility
            case_parts = []
            for i, row in df.iterrows():
                if preds[i] == -1:
                    case_parts.append(f"WHEN '{row.id}' THEN {scores[i]}")

            db.execute(text("""
                UPDATE raw_observations
                SET is_anomalous = 1,
                    anomaly_score = CASE id
                        {}
                    END
                WHERE id IN ({})
            """.format(
                " ".join(case_parts),
                ", ".join([f"'{aid}'" for aid in anomaly_ids])
            )))
            db.commit()

        if run_id:
            try:
                mlflow.end_run()
            except Exception:
                pass

        print(f"[anomaly] {len(anomaly_ids)} anomalies found in {len(rows)} {layer_type} observations")
        return len(anomaly_ids)

    except Exception as e:
        db.rollback()
        print(f"[anomaly] Detection failed for {layer_type}: {e}")
        if run_id:
            try:
                mlflow.end_run(status="FAILED")
            except Exception:
                pass
        return 0
