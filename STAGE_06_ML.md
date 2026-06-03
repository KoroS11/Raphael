# Stage 06 — Intelligence Layer (scikit-learn + Prophet + MLflow)

## Prerequisites
Stage 04 completed. At least 24 hours of AQ observations in the database. Zone geometries imported from GADM.

## Objective
Build the complete intelligence layer. This stage produces the AI Risk Score (78/100 shown in the top-right panel of the mockup), the AQ forecast chart (purple line graph in the right panel), the anomaly flags, and the AI Insights cards in the bottom-right panel. Every ML output visible in the mockup originates from this stage.

---

## Step 1 — Start MLflow Tracking Server

```
mlflow server \
  --host 127.0.0.1 \
  --port 5000 \
  --backend-store-uri sqlite:///data/mlflow.db \
  --default-artifact-root ./data/mlflow/artifacts
```

Verify MLflow UI is accessible at http://localhost:5000

---

## Step 2 — Create the Prophet Forecast Module

Create `backend/ml/forecast.py`:

```python
import os
import uuid
import pandas as pd
import numpy as np
import mlflow
from prophet import Prophet
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

mlflow.set_tracking_uri(f"http://127.0.0.1:{os.getenv('MLFLOW_PORT', '5000')}")

MIN_OBS     = 30    # Minimum observations required to train
HORIZON_HRS = 48   # Forecast horizon

def train_and_forecast(
    db: Session,
    zone_id: str,
    layer_type: str,
    horizon_hours: int = HORIZON_HRS
) -> Optional[dict]:
    from db.queries import get_observations_for_zone
    from db.models import MLOutput, ZoneGeometry

    obs = get_observations_for_zone(db, zone_id, layer_type, lookback_days=90)
    if len(obs) < MIN_OBS:
        print(f"Insufficient data for {layer_type} forecast in zone {zone_id[:8]}: {len(obs)} obs")
        return None

    df = pd.DataFrame(obs, columns=["ds", "y"])
    df["ds"] = pd.to_datetime(df["ds"])
    df       = df.dropna().sort_values("ds")

    experiment_name = f"{layer_type}_forecast"
    mlflow.set_experiment(experiment_name)

    with mlflow.start_run(run_name=f"zone_{zone_id[:8]}_{datetime.now().strftime('%Y%m%d_%H%M')}") as run:
        mlflow.log_params({
            "zone_id":      zone_id,
            "layer_type":   layer_type,
            "training_rows": len(df),
            "horizon_hours": horizon_hours,
            "changepoint_prior_scale": 0.05,
            "seasonality_mode": "multiplicative"
        })

        m = Prophet(
            changepoint_prior_scale=0.05,
            seasonality_prior_scale=10.0,
            seasonality_mode="multiplicative",
            uncertainty_samples=500,
            daily_seasonality=True,
            weekly_seasonality=True,
            yearly_seasonality=len(df) > 365
        )
        m.add_seasonality(name="hourly_pattern", period=1, fourier_order=8)
        m.fit(df)

        future   = m.make_future_dataframe(periods=horizon_hours, freq="h")
        forecast = m.predict(future)
        fcast    = forecast.tail(horizon_hours).copy()

        mean_forecast = float(fcast["yhat"].mean())
        peak_forecast = float(fcast["yhat"].max())
        mlflow.log_metrics({
            "forecast_mean": mean_forecast,
            "forecast_peak": peak_forecast,
            "forecast_range": float(fcast["yhat"].max() - fcast["yhat"].min())
        })

        # Identify exceedance windows (above a threshold)
        thresholds = {"aq": 150.0, "lst": 42.0, "ndvi": 0.1}
        threshold  = thresholds.get(layer_type, float("inf"))
        exceedance = fcast[fcast["yhat"] > threshold]

        # Generate plain-language explanation
        explanation = _generate_explanation(layer_type, mean_forecast, peak_forecast, len(exceedance))

        # Write outputs to database
        outputs = []
        for _, row in fcast.iterrows():
            outputs.append(MLOutput(
                id=uuid.uuid4(),
                zone_id=zone_id,
                model_type="prophet_forecast",
                output_type="point_forecast",
                layer_type=layer_type,
                value=float(row["yhat"]),
                confidence_lower=float(row["yhat_lower"]),
                confidence_upper=float(row["yhat_upper"]),
                explanation=explanation,
                model_version="prophet-1.1.5",
                mlflow_run_id=run.info.run_id,
                computed_at=datetime.now(timezone.utc),
                valid_from=row["ds"].to_pydatetime().replace(tzinfo=timezone.utc),
                valid_to=row["ds"].to_pydatetime().replace(tzinfo=timezone.utc)
            ))

        db.bulk_save_objects(outputs)
        db.commit()
        print(f"Forecast written: {len(outputs)} points for {layer_type} in zone {zone_id[:8]}")

        return {
            "run_id":      run.info.run_id,
            "mean":        mean_forecast,
            "peak":        peak_forecast,
            "explanation": explanation,
            "points":      len(outputs)
        }


def _generate_explanation(layer_type: str, mean: float, peak: float, exceedance_hours: int) -> str:
    if layer_type == "aq":
        if peak > 300:
            return f"Air quality forecast to reach hazardous levels (peak {peak:.0f} AQI). Exceedance expected for {exceedance_hours} hours. Outdoor activity strongly discouraged."
        elif peak > 200:
            return f"PM2.5 forecast to reach very unhealthy levels (peak {peak:.0f} AQI) for {exceedance_hours} hours. Sensitive groups should avoid outdoor exposure."
        elif peak > 150:
            return f"PM2.5 likely to rise to unhealthy range (peak {peak:.0f} AQI). Wind speed reduction and temperature inversion may contribute."
        else:
            return f"Air quality forecast to remain in acceptable range (mean {mean:.0f} AQI) over the next 48 hours."
    elif layer_type == "lst":
        if peak > 48:
            return f"Land surface temperature forecast to exceed 48°C (peak {peak:.1f}°C). Extreme heat risk. Urban heat island effect intensifying."
        elif peak > 42:
            return f"Surface temperature forecast to reach {peak:.1f}°C. High heat stress expected. Low wind speed and low vegetation cover are contributing factors."
        else:
            return f"Surface temperature forecast to remain moderate (mean {mean:.1f}°C) over the next 72 hours."
    else:
        return f"Forecast computed. Mean value: {mean:.2f}, peak: {peak:.2f} over next {48} hours."
```

---

## Step 3 — Create the Anomaly Detection Module

Create `backend/ml/anomaly.py`:

```python
import uuid
import numpy as np
import pandas as pd
import mlflow
from sklearn.ensemble import IsolationForest
from datetime import datetime, timezone
from sqlalchemy.orm import Session

def detect_anomalies(db: Session, region_id: str, layer_type: str) -> int:
    from db.models import RawObservation
    from sqlalchemy import text

    # Fetch rolling 7-day window with time features
    rows = db.execute(text("""
        SELECT
            id,
            value,
            EXTRACT(HOUR FROM observed_at)         as hour,
            EXTRACT(DOW  FROM observed_at)         as day_of_week,
            EXTRACT(MONTH FROM observed_at)        as month
        FROM raw_observations
        WHERE layer_type  = :layer_type
          AND region_id   = :region_id
          AND observed_at >= NOW() - INTERVAL '7 days'
          AND value IS NOT NULL
    """), {"layer_type": layer_type, "region_id": region_id}).fetchall()

    if len(rows) < 50:
        return 0

    df = pd.DataFrame(rows, columns=["id", "value", "hour", "day_of_week", "month"])
    X  = df[["value", "hour", "day_of_week", "month"]].values

    with mlflow.start_run(run_name=f"anomaly_{layer_type}_{region_id[:8]}"):
        clf = IsolationForest(
            n_estimators=100,
            contamination=0.05,
            random_state=42
        )
        preds  = clf.fit_predict(X)
        scores = clf.score_samples(X)

        mlflow.log_params({
            "layer_type":    layer_type,
            "n_samples":     len(df),
            "contamination": 0.05
        })
        mlflow.log_metric("anomaly_count", int((preds == -1).sum()))

    # Update database rows with anomaly flags
    anomaly_ids = df.loc[preds == -1, "id"].tolist()
    if anomaly_ids:
        db.execute(text("""
            UPDATE raw_observations
            SET is_anomalous = true,
                anomaly_score = CASE id
                    {}
                END
            WHERE id = ANY(:ids)
        """.format(
            " ".join([f"WHEN '{row.id}' THEN {scores[i]}" for i, row in df.iterrows()])
        )), {"ids": anomaly_ids})
        db.commit()

    print(f"Anomaly detection: {len(anomaly_ids)} anomalies found in {len(rows)} {layer_type} observations")
    return len(anomaly_ids)
```

---

## Step 4 — Create KMeans Zone Clustering

Create `backend/ml/clustering.py`:

```python
import uuid
import numpy as np
import pandas as pd
import mlflow
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from datetime import datetime, timezone
from sqlalchemy.orm import Session

N_CLUSTERS = 5

def cluster_zones(db: Session, region_id: str) -> dict:
    from db.models import ZoneGeometry, MLOutput
    from sqlalchemy import text

    # Get current-day mean values per zone for all layers
    rows = db.execute(text("""
        SELECT
            z.id   as zone_id,
            z.name as zone_name,
            AVG(CASE WHEN o.layer_type = 'aq'   THEN o.value END) as aq_mean,
            AVG(CASE WHEN o.layer_type = 'lst'  THEN o.value END) as lst_mean,
            AVG(CASE WHEN o.layer_type = 'ndvi' THEN o.value END) as ndvi_mean
        FROM zone_geometries z
        LEFT JOIN raw_observations o ON ST_Within(o.geometry, z.geometry)
            AND o.observed_at >= NOW() - INTERVAL '6 hours'
        WHERE z.region_id = :region_id
        GROUP BY z.id, z.name
        HAVING COUNT(o.id) > 0
    """), {"region_id": region_id}).fetchall()

    if len(rows) < N_CLUSTERS:
        print(f"Not enough zones with data for clustering: {len(rows)}")
        return {}

    df = pd.DataFrame(rows, columns=["zone_id", "zone_name", "aq_mean", "lst_mean", "ndvi_mean"])
    df = df.fillna(df.mean(numeric_only=True))

    X      = df[["aq_mean", "lst_mean", "ndvi_mean"]].values
    scaler = StandardScaler()
    X_norm = scaler.fit_transform(X)

    with mlflow.start_run(run_name=f"kmeans_zones_{region_id[:8]}"):
        km     = KMeans(n_clusters=N_CLUSTERS, init="k-means++", n_init=10, random_state=42)
        labels = km.fit_predict(X_norm)

        mlflow.log_params({"n_clusters": N_CLUSTERS, "n_zones": len(df)})
        mlflow.log_metric("inertia", float(km.inertia_))

    # Write cluster assignments to ml_outputs
    outputs = []
    for i, row in df.iterrows():
        outputs.append(MLOutput(
            id=uuid.uuid4(),
            zone_id=str(row["zone_id"]),
            model_type="kmeans_clustering",
            output_type="cluster_assignment",
            value=float(labels[i]),
            explanation=_cluster_label(int(labels[i]), df.iloc[i]),
            model_version="sklearn-kmeans-1.5",
            computed_at=datetime.now(timezone.utc)
        ))

    db.bulk_save_objects(outputs)
    db.commit()

    result = dict(zip(df["zone_id"].astype(str), labels.tolist()))
    print(f"Clustered {len(df)} zones into {N_CLUSTERS} groups")
    return result


def _cluster_label(cluster_id: int, row: pd.Series) -> str:
    labels = {
        0: "Low stress — good air quality, moderate temperature, adequate vegetation",
        1: "Heat stressed — elevated surface temperature, low vegetation cover",
        2: "Pollution hotspot — poor air quality, high urban density",
        3: "High risk — combination of poor air quality and elevated heat",
        4: "Critical zone — all indicators at elevated levels"
    }
    return labels.get(cluster_id, f"Environmental cluster {cluster_id}")
```

---

## Step 5 — Create the Risk Scorer

Create `backend/ml/risk_score.py`:

```python
import uuid
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from datetime import datetime, timezone
from sqlalchemy.orm import Session

WEIGHTS = {"aq": 0.40, "lst": 0.35, "ndvi": 0.25}

def compute_all_risk_scores(db: Session, region_id: str) -> list:
    from db.models import ZoneGeometry, MLOutput
    from sqlalchemy import text

    rows = db.execute(text("""
        SELECT
            z.id   as zone_id,
            z.name as zone_name,
            AVG(CASE WHEN o.layer_type = 'aq'   THEN o.value END) as aq_mean,
            AVG(CASE WHEN o.layer_type = 'lst'  THEN o.value END) as lst_mean,
            AVG(CASE WHEN o.layer_type = 'ndvi' THEN o.value END) as ndvi_mean
        FROM zone_geometries z
        LEFT JOIN raw_observations o ON ST_Within(o.geometry, z.geometry)
            AND o.observed_at >= NOW() - INTERVAL '6 hours'
        WHERE z.region_id = :region_id
        GROUP BY z.id, z.name
    """), {"region_id": region_id}).fetchall()

    if not rows:
        return []

    df = pd.DataFrame(rows, columns=["zone_id", "zone_name", "aq_mean", "lst_mean", "ndvi_mean"])
    df = df.fillna(df.mean(numeric_only=True))

    scaler   = MinMaxScaler()
    aq_n     = scaler.fit_transform(df[["aq_mean"]].values).flatten()
    lst_n    = scaler.fit_transform(df[["lst_mean"]].values).flatten()
    ndvi_n   = 1 - scaler.fit_transform(df[["ndvi_mean"]].values).flatten()

    scores   = (
        WEIGHTS["aq"]   * aq_n +
        WEIGHTS["lst"]  * lst_n +
        WEIGHTS["ndvi"] * ndvi_n
    ) * 100

    # Delete previous risk score outputs for this region
    db.execute(text("""
        DELETE FROM ml_outputs
        WHERE model_type = 'risk_score'
          AND zone_id IN (
              SELECT id FROM zone_geometries WHERE region_id = :region_id
          )
    """), {"region_id": region_id})

    outputs = []
    results = []
    for i, row in df.iterrows():
        score       = round(float(scores[i]), 1)
        explanation = _build_explanation(aq_n[i], lst_n[i], ndvi_n[i], score)
        outputs.append(MLOutput(
            id=uuid.uuid4(),
            zone_id=str(row["zone_id"]),
            model_type="risk_score",
            output_type="composite_score",
            value=score,
            explanation=explanation,
            model_version="weighted-v1.0",
            computed_at=datetime.now(timezone.utc)
        ))
        results.append({
            "zone_id":     str(row["zone_id"]),
            "zone_name":   row["zone_name"],
            "risk_score":  score,
            "category":    _categorize(score),
            "explanation": explanation,
            "contributions": {
                "aq":   round(WEIGHTS["aq"]   * aq_n[i]   * 100, 1),
                "lst":  round(WEIGHTS["lst"]  * lst_n[i]  * 100, 1),
                "ndvi": round(WEIGHTS["ndvi"] * ndvi_n[i] * 100, 1)
            }
        })

    db.bulk_save_objects(outputs)
    db.commit()

    print(f"Risk scores computed for {len(results)} zones")
    return results


def _categorize(score: float) -> str:
    if score >= 85: return "Critical Risk"
    if score >= 70: return "High Risk"
    if score >= 50: return "Moderate Risk"
    if score >= 30: return "Low Risk"
    return "Minimal Risk"


def _build_explanation(aq_n, lst_n, ndvi_n, score) -> str:
    parts = []
    if aq_n   > 0.7: parts.append("very poor air quality")
    elif aq_n > 0.4: parts.append("elevated PM2.5 levels")
    if lst_n  > 0.7: parts.append("high land surface temperature")
    elif lst_n > 0.4: parts.append("above-average surface heat")
    if ndvi_n > 0.7: parts.append("critically low green cover")
    elif ndvi_n > 0.4: parts.append("below-average vegetation")
    if not parts:
        return "All environmental indicators within acceptable ranges."
    return "Risk elevated due to " + ", ".join(parts) + "."
```

---

## Step 6 — Create AI Insights Generator

This generates the three insight cards in the bottom-right panel of the mockup
("Heat index will increase by 3-5C in next 48h", "AQI likely to remain in Very Poor category", "Low green cover in Central and North Delhi increasing heat risk").

Create `backend/ml/explainer.py`:

```python
from sqlalchemy.orm import Session
from sqlalchemy import text

def generate_ai_insights(db: Session, region_id: str) -> list[dict]:
    insights = []

    # Insight 1: Temperature trend
    lst_forecast = db.execute(text("""
        SELECT AVG(value) as forecast_mean, MAX(value) as forecast_peak
        FROM ml_outputs
        WHERE model_type  = 'prophet_forecast'
          AND output_type = 'point_forecast'
          AND layer_type  = 'lst'
          AND valid_from  >= NOW()
          AND valid_to    <= NOW() + INTERVAL '48 hours'
    """)).fetchone()

    if lst_forecast and lst_forecast.forecast_peak:
        current_lst = db.execute(text("""
            SELECT AVG(value) FROM raw_observations
            WHERE layer_type = 'lst' AND observed_at >= NOW() - INTERVAL '6 hours'
        """)).scalar()
        if current_lst:
            delta = round(float(lst_forecast.forecast_peak) - float(current_lst), 1)
            insights.append({
                "type":    "temperature",
                "icon":    "heat",
                "message": f"Heat index will increase by {delta}°C in next 48 hours.",
                "severity": "warning" if delta > 2 else "info"
            })

    # Insight 2: AQ category forecast
    aq_forecast = db.execute(text("""
        SELECT AVG(value) as mean_forecast
        FROM ml_outputs
        WHERE model_type  = 'prophet_forecast'
          AND layer_type  = 'aq'
          AND valid_from  >= NOW()
          AND valid_to    <= NOW() + INTERVAL '24 hours'
    """)).fetchone()

    if aq_forecast and aq_forecast.mean_forecast:
        val = float(aq_forecast.mean_forecast)
        cat = _aqi_category(val)
        insights.append({
            "type":    "air_quality",
            "icon":    "cloud",
            "message": f"AQI forecast to remain in '{cat}' category over next 24 hours.",
            "severity": "critical" if val > 200 else "warning" if val > 100 else "info"
        })

    # Insight 3: Low NDVI zones
    low_ndvi_zones = db.execute(text("""
        SELECT COUNT(*) as count, STRING_AGG(z.name, ', ' ORDER BY o.avg_ndvi) as zones
        FROM (
            SELECT z.id, z.name, AVG(o.value) as avg_ndvi
            FROM zone_geometries z
            JOIN raw_observations o ON ST_Within(o.geometry, z.geometry)
            WHERE o.layer_type = 'ndvi'
              AND o.observed_at >= NOW() - INTERVAL '24 hours'
            GROUP BY z.id, z.name
            HAVING AVG(o.value) < 0.2
            LIMIT 3
        ) o JOIN zone_geometries z ON z.id = o.id
    """)).fetchone()

    if low_ndvi_zones and low_ndvi_zones.count > 0:
        insights.append({
            "type":    "vegetation",
            "icon":    "leaf",
            "message": f"Low green cover in {low_ndvi_zones.zones} increasing heat risk.",
            "severity": "warning"
        })

    return insights[:3]  # Return max 3 insights (matching mockup)


def _aqi_category(aqi: float) -> str:
    if aqi <= 50:  return "Good"
    if aqi <= 100: return "Moderate"
    if aqi <= 150: return "Unhealthy for Sensitive Groups"
    if aqi <= 200: return "Unhealthy"
    if aqi <= 300: return "Very Poor"
    return "Hazardous"
```

---

## Step 7 — Create the Intelligence Runner

Create `backend/ml/runner.py`:

```python
from sqlalchemy.orm import Session
from db.connection import SessionLocal
from db.models import Region
from .forecast   import train_and_forecast
from .anomaly    import detect_anomalies
from .clustering import cluster_zones
from .risk_score import compute_all_risk_scores
from .explainer  import generate_ai_insights
import structlog

log = structlog.get_logger()

def run_intelligence_cycle(region_id: str = None):
    db = SessionLocal()
    try:
        if not region_id:
            region = db.query(Region).filter(Region.is_active == True).first()
            if not region:
                log.error("No active region found")
                return
            region_id = str(region.id)

        log.info("intelligence_cycle_start", region_id=region_id[:8])

        # 1. Anomaly detection across all layers
        for layer in ["aq", "lst", "ndvi", "fire"]:
            count = detect_anomalies(db, region_id, layer)
            log.info("anomaly_detection_done", layer=layer, count=count)

        # 2. Zone clustering
        cluster_zones(db, region_id)

        # 3. Risk scores for all zones
        compute_all_risk_scores(db, region_id)

        # 4. Forecasts for key zones (top 5 by risk score)
        from sqlalchemy import text
        top_zones = db.execute(text("""
            SELECT DISTINCT zone_id FROM ml_outputs
            WHERE model_type = 'risk_score'
            ORDER BY value DESC LIMIT 5
        """)).fetchall()
