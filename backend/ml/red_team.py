"""
Red Team — Deterministic Evidence Challenge Layer.

For each anomalous Evidence Object (if_anomaly=True), runs a fixed
set of deterministic plausibility checks that could weaken
confidence in the anomaly or its physics corroboration. This is
NOT a learned model — every check is a fixed rule against known
physical/statistical bounds or recent observation history.

Red Team never modifies the original confidence or rule_id set by
the Symbolic layer (ml/rules.py). It produces a separate
ChallengeResult attached to the evidence, so the original PCAD
output remains traceable and unaltered — Red Team's role is to
surface reasons for caution, not to overrule the Blue Team.

Checks implemented:
  1. wind_consistency     — near-calm/missing wind undermines
                             plume-based corroboration
  2. meteorological_plausibility — implausible wind readings
  3. magnitude_sanity      — anomaly score near IF decision boundary
  4. temporal_isolation    — single-reading spike vs sustained trend
"""

from dataclasses import dataclass, asdict
from typing import Optional
import pandas as pd
from sqlalchemy import text

# Thresholds — fixed, documented, not learned
CALM_WIND_THRESHOLD_MS = 0.5
MAX_PLAUSIBLE_WIND_MS = 40.0
BORDERLINE_SCORE_THRESHOLD = 0.05
TEMPORAL_WINDOW_HOURS = 3


@dataclass
class ChallengeResult:
    station_name: str
    observed_at: str
    rule_id: str                # unchanged, copied from evidence for traceability
    confidence: str              # unchanged, copied from evidence for traceability

    wind_consistency_triggered: bool
    wind_consistency_detail: str

    meteorological_plausibility_triggered: bool
    meteorological_plausibility_detail: str

    magnitude_sanity_triggered: bool
    magnitude_sanity_detail: str

    temporal_isolation_triggered: Optional[bool]
    temporal_isolation_detail: str

    n_challenges_triggered: int
    robustness: str  # "ROBUST" | "FRAGILE"

    def to_dict(self) -> dict:
        return asdict(self)


def _check_wind_consistency(evidence) -> tuple:
    if evidence.plume_corroborated is not True:
        return False, "Not applicable — plume did not corroborate this anomaly."
    if evidence.wind_speed is None:
        return True, "Wind speed missing; plume corroboration cannot be trusted without meteorology."
    if evidence.wind_speed < CALM_WIND_THRESHOLD_MS:
        return True, (
            f"Wind speed {evidence.wind_speed:.2f} m/s is near-calm "
            f"(<{CALM_WIND_THRESHOLD_MS} m/s); plume direction and "
            f"spread are unreliable at this wind speed, weakening "
            f"the physics corroboration behind this HIGH confidence call."
        )
    return False, f"Wind speed {evidence.wind_speed:.2f} m/s supports reliable plume corroboration."


def _check_meteorological_plausibility(evidence) -> tuple:
    if evidence.wind_speed is None:
        return False, "No wind data to evaluate."
    if evidence.wind_speed < 0 or evidence.wind_speed > MAX_PLAUSIBLE_WIND_MS:
        return True, f"Wind speed {evidence.wind_speed} m/s is outside plausible bounds (0-{MAX_PLAUSIBLE_WIND_MS} m/s)."
    if evidence.wind_direction is not None and not (0 <= evidence.wind_direction <= 360):
        return True, f"Wind direction {evidence.wind_direction} is outside valid range (0-360 degrees)."
    return False, "Meteorological readings within plausible bounds."


def _check_magnitude_sanity(evidence) -> tuple:
    if evidence.anomaly_score is None:
        return False, "No anomaly score available to evaluate."
    if abs(evidence.anomaly_score) < BORDERLINE_SCORE_THRESHOLD:
        return True, (
