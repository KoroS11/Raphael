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
