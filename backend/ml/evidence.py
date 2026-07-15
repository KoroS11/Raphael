"""
Blue Team — Evidence Aggregation Layer.

Collects outputs from already-validated modules (PCAD anomaly
detection, Gaussian Plume physics, Prophet+LSTM forecasting,
weather) into a single structured Evidence Object per observation.

This module performs NO inference and trains NO model. It is a
deterministic aggregator: its only job is to assemble evidence
that already exists elsewhere in the pipeline into one traceable
record, in preparation for Red Team challenge and Symbolic
reconciliation (see ml/rules.py).

Fields marked "not computed in production" reflect components
validated only in the research notebooks (e.g. SHAP) and are
included as optional/null so the schema is honest about current
system coverage rather than implying capabilities that don't run
live.
"""

from dataclasses import dataclass, asdict, field
from typing import Optional
from datetime import datetime
from ml.rules import get_rule


@dataclass
class EvidenceObject:
    # Identity
    station_name: str
    observed_at: str
    region_id: str

    # Raw observation
    pollutant: str
    value: float

    # Anomaly evidence (from PCAD / IsolationForest)
    if_anomaly: bool
    anomaly_score: Optional[float]

    # Physics evidence (from Gaussian Plume)
    plume_conc: Optional[float]
    plume_corroborated: Optional[bool]

    # Symbolic evidence (from ml/rules.py — already computed by PCAD)
    confidence: str            # HIGH / MEDIUM / NORMAL
    rule_id: str                 # R001 / R002 / R003
    evidence_used: tuple          # e.g. ('IsolationForest', 'GaussianPlume')

    # Meteorology (context, not yet a distinct rule)
    wind_speed: Optional[float] = None
    wind_direction: Optional[float] = None

    # Forecast evidence (from Prophet+LSTM, if available for this zone)
    forecast_next_1h: Optional[float] = None
    forecast_model: Optional[str] = None  # "prophet_lstm" | "prophet_only" | None

    # Explainability — NOT COMPUTED IN PRODUCTION.
    # SHAP is validated only in research notebooks (Notebook 1/2).
    # Left as None here rather than omitted, so downstream consumers
    # (Red Team, Gemma) can check for its absence explicitly instead
    # of assuming a field that silently doesn't exist.
    shap_top_features: Optional[list] = None
    shap_status: str = "not_computed_in_production"

    # Provenance
    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    schema_version: str = "1.0"

    def to_dict(self) -> dict:
        return asdict(self)


def aggregate_evidence(db, region_id: str, days_back: int = 1) -> list:
    """
    Build Evidence Objects for recent observations by joining
    already-computed PCAD output with weather and forecast data.

    Does NOT recompute anomaly detection, plume physics, or
    forecasting — it reads their outputs. If those modules haven't
    run for the requested window, returns an empty list rather than
    computing anything itself (Blue Team is aggregation-only).
    """
    import pandas as pd
    from sqlalchemy import text
    from ml.pcad import compute_pcad_scores

    pcad_df = compute_pcad_scores(db, region_id=region_id, days_back=days_back)
    if pcad_df.empty:
        return []

    # Nearest weather match per observation (reuse same 1h window
    # logic as compute_pcad_scores internally uses)
    weather = db.execute(text("""
        SELECT observed_at,
               MAX(CASE WHEN station_name = 'wind_speed_10m' THEN value END) as ws,
               MAX(CASE WHEN station_name = 'wind_direction_10m' THEN value END) as wd
        FROM raw_observations
        WHERE region_id = :rid
        AND layer_type = 'weather'
        AND observed_at > datetime('now', :days)
        GROUP BY observed_at
        ORDER BY observed_at
    """), {"rid": region_id, "days": f"-{days_back} days"}).fetchall()

    df_w = pd.DataFrame(weather, columns=['observed_at', 'ws', 'wd'])
    if not df_w.empty:
        df_w['observed_at'] = pd.to_datetime(df_w['observed_at'])

    evidence_list = []
    for _, row in pcad_df.iterrows():
        ws, wd = None, None
        if not df_w.empty:
            time_diff = abs(df_w['observed_at'] - pd.Timestamp(row['observed_at']))
            nearest_idx = time_diff.idxmin()
            if time_diff[nearest_idx] <= pd.Timedelta('1H'):
                ws = float(df_w.loc[nearest_idx, 'ws']) if df_w.loc[nearest_idx, 'ws'] else None
                wd = float(df_w.loc[nearest_idx, 'wd']) if df_w.loc[nearest_idx, 'wd'] else None

        evidence_list.append(EvidenceObject(
            station_name=row['station_name'],
            observed_at=str(row['observed_at']),
            region_id=str(region_id),
            pollutant="pm25",
            value=float(row['value']),
            if_anomaly=bool(row['if_anomaly']),
            anomaly_score=float(row['anomaly_score']) if 'anomaly_score' in row and row['anomaly_score'] is not None else None,
            plume_conc=float(row['plume_conc']) if row.get('plume_conc') is not None else None,
            plume_corroborated=bool(row['plume_conc'] > 15.0) if row.get('plume_conc') is not None else None,
            confidence=row['confidence'],
            rule_id=row['rule_id'],
            evidence_used=get_rule(row['rule_id']).evidence_used if get_rule(row['rule_id']) else (),
            wind_speed=ws,
            wind_direction=wd,
        ))

    return evidence_list


def evidence_to_json_list(evidence_list: list) -> list:
    """Serialize Evidence Objects for storage, broadcast, or Gemma input."""
    return [e.to_dict() for e in evidence_list]
