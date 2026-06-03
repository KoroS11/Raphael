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
