"""
Raphael — Stage 3: FORECAST (Prophet per Zone per Layer)

Trains a Prophet model per zone per layer type and generates 48-hour
forecasts with exceedance windows. All runs tracked in MLflow.
"""
import os
import sys

# Windows DLL overrides for MKL/OMP and Stan compiler
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
conda_prefix = os.environ.get("RAPHAEL_CONDA_PREFIX") or os.environ.get("CONDA_PREFIX") or r"C:\Users\harsh\anaconda3\envs\raphael-env"
lib_bin = os.path.join(conda_prefix, "Library", "bin")
if os.path.exists(lib_bin) and lib_bin not in os.environ["PATH"]:
    os.environ["PATH"] = lib_bin + os.pathsep + os.environ["PATH"]

import uuid
import pandas as pd
import numpy as np
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

from prophet import Prophet
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

try:
    mlflow.set_tracking_uri(f"http://127.0.0.1:{os.getenv('MLFLOW_PORT', '5000')}")
except Exception:
    pass

MIN_OBS = 30       # Minimum observations required to train
HORIZON_HRS = 48   # Forecast horizon


def train_and_forecast(
    db: Session,
    zone_id: str,
    layer_type: str,
    horizon_hours: int = HORIZON_HRS
) -> Optional[dict]:
    """
    Train Prophet on historical observations for a zone+layer,
    produce a 48-hour forecast, and persist to ml_outputs table.
    """
    from db.queries import get_observations_for_zone
    from db.models import MLOutput

    obs = get_observations_for_zone(db, zone_id, layer_type, lookback_days=90)
    if len(obs) < MIN_OBS:
        print(f"[forecast] Insufficient data for {layer_type} in zone {zone_id[:8]}: "
              f"{len(obs)} obs (need {MIN_OBS})")
        return None

    df = pd.DataFrame(obs)
    df["ds"] = pd.to_datetime(df["ds"])
    df["y"] = pd.to_numeric(df["y"], errors="coerce")
    df = df.dropna(subset=["ds", "y"]).sort_values("ds")

    if len(df) < MIN_OBS:
        print(f"[forecast] After cleanup, only {len(df)} valid rows for {layer_type}")
        return None

    experiment_name = f"{layer_type}_forecast"
    run_id = None
    run_obj = None

    # Isolate MLflow session setup — a tracking-server outage must not
    # prevent Prophet training or the database writes below.
    try:
        mlflow.set_experiment(experiment_name)
        run_obj = mlflow.start_run(
            run_name=f"zone_{zone_id[:8]}_{datetime.now().strftime('%Y%m%d_%H%M')}"
        )
        run_id = run_obj.info.run_id
    except Exception as me:
        print(f"[forecast] MLflow tracking unavailable (non-fatal): {me}")

    # Core forecasting and database persistence — independent of MLflow.
    try:
        # Log parameters defensively
        if run_id:
            try:
                mlflow.log_params({
                    "zone_id":                  zone_id,
                    "layer_type":               layer_type,
                    "training_rows":            len(df),
                    "horizon_hours":            horizon_hours,
                    "changepoint_prior_scale":  0.05,
                    "seasonality_mode":         "multiplicative"
                })
            except Exception as le:
                print(f"[forecast] MLflow log_params failed (non-fatal): {le}")

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

        future = m.make_future_dataframe(periods=horizon_hours, freq="h")
        forecast = m.predict(future)
        fcast = forecast.tail(horizon_hours).copy()

        mean_forecast = float(fcast["yhat"].mean())
        peak_forecast = float(fcast["yhat"].max())

        # Log metrics defensively
        if run_id:
            try:
                mlflow.log_metrics({
                    "forecast_mean":  mean_forecast,
                    "forecast_peak":  peak_forecast,
                    "forecast_range": float(fcast["yhat"].max() - fcast["yhat"].min())
                })
            except Exception as le:
                print(f"[forecast] MLflow log_metrics failed (non-fatal): {le}")

        # Identify exceedance windows
        thresholds = {"aq": 150.0, "lst": 42.0, "ndvi": 0.1}
        threshold = thresholds.get(layer_type, float("inf"))
        exceedance = fcast[fcast["yhat"] > threshold]

        explanation = _generate_explanation(
            layer_type, mean_forecast, peak_forecast, len(exceedance)
        )

        # Write forecast outputs to database — DELETE and INSERT share one
        # transaction now, committed together, so no reader ever sees a
        # zero-row window for this zone/layer mid-write.
        db.execute(text("""
            DELETE FROM ml_outputs
            WHERE model_type  = 'prophet_forecast'
              AND output_type = 'point_forecast'
              AND zone_id     = :zone_id
              AND layer_type  = :layer_type
        """), {"zone_id": zone_id, "layer_type": layer_type})

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
                mlflow_run_id=run_id if run_id else "no_mlflow_run",
                computed_at=datetime.now(timezone.utc),
                valid_from=row["ds"].to_pydatetime().replace(tzinfo=timezone.utc),
                valid_to=row["ds"].to_pydatetime().replace(tzinfo=timezone.utc)
            ))

        db.bulk_save_objects(outputs)
        db.commit()
        print(f"[forecast] {len(outputs)} points for {layer_type} "
              f"in zone {zone_id[:8]}")

        # Finalize MLflow session
        if run_id:
            try:
                mlflow.end_run()
            except Exception as re:
                print(f"[forecast] MLflow run end failed (non-fatal): {re}")

        return {
            "run_id":      run_id if run_id else "no_mlflow_run",
            "mean":        mean_forecast,
            "peak":        peak_forecast,
            "explanation": explanation,
            "points":      len(outputs)
        }

    except Exception as e:
        db.rollback()
        print(f"[forecast] Prophet failed for {layer_type}/{zone_id[:8]}: {e}")
        if run_id:
            try:
                mlflow.end_run(status="FAILED")
            except Exception:
                pass
        return None


def _generate_explanation(
    layer_type: str, mean: float, peak: float, exceedance_hours: int
) -> str:
    if layer_type == "aq":
        if peak > 300:
            return (f"Air quality forecast to reach hazardous levels "
                    f"(peak {peak:.0f} AQI). Exceedance expected for "
                    f"{exceedance_hours} hours. Outdoor activity "
                    f"strongly discouraged.")
        elif peak > 200:
            return (f"PM2.5 forecast to reach very unhealthy levels "
                    f"(peak {peak:.0f} AQI) for {exceedance_hours} hours. "
                    f"Sensitive groups should avoid outdoor exposure.")
        elif peak > 150:
            return (f"PM2.5 likely to rise to unhealthy range "
                    f"(peak {peak:.0f} AQI). Wind speed reduction and "
                    f"temperature inversion may contribute.")
        else:
            return (f"Air quality forecast to remain in acceptable range "
                    f"(mean {mean:.0f} AQI) over the next 48 hours.")
    elif layer_type == "lst":
        if peak > 48:
            return (f"Land surface temperature forecast to exceed 48°C "
                    f"(peak {peak:.1f}°C). Extreme heat risk. "
                    f"Urban heat island effect intensifying.")
        elif peak > 42:
            return (f"Surface temperature forecast to reach {peak:.1f}°C. "
                    f"High heat stress expected. Low wind speed and low "
                    f"vegetation cover are contributing factors.")
        else:
            return (f"Surface temperature forecast to remain moderate "
                    f"(mean {mean:.1f}°C) over the next 72 hours.")
    else:
        return (f"Forecast computed. Mean value: {mean:.2f}, "
                f"peak: {peak:.2f} over next {HORIZON_HRS} hours.")


import torch
import torch.nn as nn
import pickle
import structlog

class ResidualLSTM(nn.Module):
    def __init__(self, hidden_size=64, num_layers=2):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=1, 
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=0.2 if num_layers > 1 else 0
        )
        self.fc = nn.Linear(hidden_size, 1)
    
    def forward(self, x):
        out, _ = self.lstm(x)
        return self.fc(out[:, -1, :])

def run_hybrid_forecast(db, zone_id: str, 
                         layer_type: str = 'aq',
                         horizon_hours: int = 48) -> dict:
    """
    Prophet+LSTM hybrid forecaster.
    Prophet handles trend+seasonality, LSTM learns residuals.
    Based on Milli et al. (2025) architecture.
    Falls back to Prophet-only if < 24 residual samples.
    """
    import numpy as np
    import pandas as pd
    from prophet import Prophet
    from sqlalchemy import text
    import json
    from datetime import datetime, timezone
    
    LOOKBACK = 12
    MODEL_DIR = os.path.join(
        os.path.dirname(__file__), '..', 'notebooks', 'models'
    )
    os.makedirs(MODEL_DIR, exist_ok=True)
    
    log = structlog.get_logger()
    
    # Load time series for this zone
    rows = db.execute(text("""
        SELECT observed_at, value, station_name
        FROM raw_observations
        WHERE region_id = (
            SELECT region_id FROM zone_geometries WHERE id = :zone_id
        )
        AND layer_type = :layer_type
        AND value > 0 AND value < 500
        ORDER BY observed_at
    """), {"zone_id": zone_id, "layer_type": layer_type}).fetchall()
    
    if len(rows) < 20:
        log.warning("hybrid_forecast_insufficient_data", 
                    zone_id=zone_id, n_rows=len(rows))
        return {"status": "insufficient_data", "forecasts": []}
    
    df = pd.DataFrame(rows, columns=['ds', 'y', 'station'])
    df['ds'] = pd.to_datetime(df['ds'])
    df = df.groupby('ds')['y'].mean().reset_index()
    df = df.sort_values('ds').reset_index(drop=True)
    
    # Only use recent continuous data for forecasting
    # Filter to last 30 days (or all data if < 30 days available)
    cutoff = df['ds'].max() - pd.Timedelta(days=30)
    df_recent = df[df['ds'] >= cutoff].copy()
    
    if len(df_recent) < 10:
        # Not enough recent data — use all data but log warning
        df_fit = df.copy()
        log.warning("forecast_using_all_historical_data",
                    reason="insufficient_recent_data",
                    n_recent=len(df_recent))
    else:
        df_fit = df_recent
        log.info("forecast_using_recent_data",
                 n_points=len(df_fit),
                 date_range=f"{df_fit['ds'].min()} to {df_fit['ds'].max()}")

    # Stage 1: Prophet
    m = Prophet(
        daily_seasonality=True,
        weekly_seasonality=False,
        yearly_seasonality=False,
        changepoint_prior_scale=0.3,
        seasonality_prior_scale=0.1,
        interval_width=0.80,
        uncertainty_samples=100
    )
    
    # Suppress Prophet stdout
    import logging
    logging.getLogger('prophet').setLevel(logging.WARNING)
    
    m.fit(df_fit[['ds', 'y']])
    
    # Compute residuals on training data
    train_forecast = m.predict(df_fit[['ds']])
    residuals = (df_fit['y'].values - 
                 train_forecast['yhat'].values).astype(np.float32)
    
    # Stage 2: LSTM on residuals
    lstm_model = None
    if len(residuals) >= 24:
        # Prepare sequences
        X_seq, y_seq = [], []
        for i in range(LOOKBACK, len(residuals)):
            X_seq.append(residuals[i-LOOKBACK:i])
            y_seq.append(residuals[i])
        
        X_t = torch.FloatTensor(X_seq).unsqueeze(-1)
        y_t = torch.FloatTensor(y_seq).unsqueeze(-1)
        
        # Train/val split
        split = int(len(X_t) * 0.85)
        X_tr, X_val = X_t[:split], X_t[split:]
        y_tr, y_val = y_t[:split], y_t[split:]
        
        model = ResidualLSTM(hidden_size=64, num_layers=2)
        optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
        criterion = nn.MSELoss()
        
        best_val_loss = float('inf')
        patience_counter = 0
        
        for epoch in range(50):
            model.train()
            optimizer.zero_grad()
            pred = model(X_tr)
            loss = criterion(pred, y_tr)
            loss.backward()
            optimizer.step()
            
            if len(X_val) > 0:
                model.eval()
                with torch.no_grad():
                    val_pred = model(X_val)
                    val_loss = criterion(val_pred, y_val).item()
                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    patience_counter = 0
                    torch.save(model.state_dict(),
                               os.path.join(MODEL_DIR, 
                               f'lstm_residual_{zone_id[:8]}.pt'))
                else:
                    patience_counter += 1
                    if patience_counter >= 10:
                          break
            
        # Load best weights if saved
        best_path = os.path.join(MODEL_DIR, 
                                  f'lstm_residual_{zone_id[:8]}.pt')
        if os.path.exists(best_path):
            model.load_state_dict(torch.load(best_path,
                                             weights_only=True))
        lstm_model = model
        
        # Save Prophet model
        with open(os.path.join(MODEL_DIR, 
                  f'prophet_{zone_id[:8]}.pkl'), 'wb') as f:
            pickle.dump(m, f)
    else:
        log.info("hybrid_forecast_lstm_skip_insufficient_residuals",
                 n_residuals=len(residuals))
    
    # Generate future forecasts
    future = m.make_future_dataframe(periods=horizon_hours, freq='H')
    prophet_fc = m.predict(future)
    horizon_fc = prophet_fc.tail(horizon_hours)
    
    # Add LSTM residual corrections if available
    forecasts = []
    if lstm_model is not None:
        last_residuals = residuals[-LOOKBACK:].tolist()
        lstm_model.eval()
        
        with torch.no_grad():
            for h in range(horizon_hours):
                seq = torch.FloatTensor(
                    last_residuals[-LOOKBACK:]
                ).unsqueeze(0).unsqueeze(-1)
                pred_resid = lstm_model(seq).item()
                last_residuals.append(pred_resid)
        
        lstm_residuals = last_residuals[-horizon_hours:]
        
        for i, (_, row) in enumerate(horizon_fc.iterrows()):
            final_val = float(row['yhat']) + lstm_residuals[i]
            forecasts.append({
                'ds': str(row['ds']),
                'yhat': max(0, final_val),
                'yhat_lower': max(0, float(row['yhat_lower'])),
                'yhat_upper': max(0, float(row['yhat_upper'])),
                'prophet_component': float(row['yhat']),
                'lstm_residual': lstm_residuals[i]
            })
    else:
        for _, row in horizon_fc.iterrows():
            forecasts.append({
                'ds': str(row['ds']),
                'yhat': max(0, float(row['yhat'])),
                'yhat_lower': max(0, float(row['yhat_lower'])),
                'yhat_upper': max(0, float(row['yhat_upper'])),
                'prophet_component': float(row['yhat']),
                'lstm_residual': 0.0
            })
    
    return {
        "status": "complete",
        "zone_id": zone_id,
        "model": "prophet_lstm" if lstm_model else "prophet_only",
        "horizon_hours": horizon_hours,
        "forecasts": forecasts
    }
