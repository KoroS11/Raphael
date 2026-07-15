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
            f"Anomaly score {evidence.anomaly_score:.4f} is near the "
            f"IsolationForest decision boundary (threshold "
            f"{BORDERLINE_SCORE_THRESHOLD}); classification may be "
            f"sensitive to minor feature perturbation."
        )
    return False, f"Anomaly score {evidence.anomaly_score:.4f} is well-separated from the decision boundary."


def _check_temporal_isolation(evidence, db) -> tuple:
    """
    Query surrounding observations for this station to check whether
    this anomaly is an isolated single reading or part of a sustained
    elevation. Requires a light DB query — still deterministic, no
    model involved.
    """
    try:
        rows = db.execute(text("""
            SELECT value, observed_at
            FROM raw_observations
            WHERE station_name = :station
            AND layer_type = 'aq'
            AND observed_at BETWEEN
                datetime(:ts, '-' || :hrs || ' hours')
                AND datetime(:ts, '+' || :hrs || ' hours')
            ORDER BY observed_at
        """), {
            "station": evidence.station_name,
            "ts": evidence.observed_at,
            "hrs": TEMPORAL_WINDOW_HOURS
        }).fetchall()

        if len(rows) < 2:
            return None, "Insufficient surrounding readings to assess temporal persistence."

        values = [r[0] for r in rows]
        mean_surrounding = sum(values) / len(values)
        # Crude persistence check: are other readings in window also elevated
        # (within 20% of the anomalous value) or is this reading a lone spike?
        elevated_threshold = evidence.value * 0.8
        n_elevated = sum(1 for v in values if v >= elevated_threshold)

        if n_elevated <= 1:
            return True, (
                f"Anomalous reading ({evidence.value:.1f}) appears isolated: "
                f"only {n_elevated}/{len(values)} readings in the surrounding "
                f"{TEMPORAL_WINDOW_HOURS}h window are comparably elevated, "
                f"consistent with a single-reading spike rather than a "
                f"sustained pollution event."
            )
        return False, (
            f"{n_elevated}/{len(values)} readings in the surrounding "
            f"{TEMPORAL_WINDOW_HOURS}h window are comparably elevated, "
            f"consistent with a sustained event rather than an isolated spike."
        )
    except Exception as e:
        return None, f"Temporal isolation check failed: {e}"


def challenge_evidence(evidence_list: list, db) -> list:
    """
    Run Red Team checks on all anomalous evidence objects.
    Returns a list of ChallengeResult, one per if_anomaly=True evidence.
    NORMAL evidence is skipped — nothing to challenge.
    """
    results = []
    for e in evidence_list:
        if not e.if_anomaly:
            continue

        wc_trig, wc_detail = _check_wind_consistency(e)
        mp_trig, mp_detail = _check_meteorological_plausibility(e)
        ms_trig, ms_detail = _check_magnitude_sanity(e)
        ti_trig, ti_detail = _check_temporal_isolation(e, db)

        triggered_flags = [wc_trig, mp_trig, ms_trig]
        if ti_trig is True:
            triggered_flags.append(True)
        n_triggered = sum(1 for f in triggered_flags if f)

        results.append(ChallengeResult(
            station_name=e.station_name,
            observed_at=e.observed_at,
            rule_id=e.rule_id,
            confidence=e.confidence,
            wind_consistency_triggered=wc_trig,
            wind_consistency_detail=wc_detail,
            meteorological_plausibility_triggered=mp_trig,
            meteorological_plausibility_detail=mp_detail,
            magnitude_sanity_triggered=ms_trig,
            magnitude_sanity_detail=ms_detail,
            temporal_isolation_triggered=ti_trig,
            temporal_isolation_detail=ti_detail,
            n_challenges_triggered=n_triggered,
            robustness="FRAGILE" if n_triggered >= 1 else "ROBUST",
        ))
    return results


def challenges_to_json_list(results: list) -> list:
    return [r.to_dict() for r in results]
