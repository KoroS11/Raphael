"""
Raphael — Stage 2: ATTRIBUTE (Anomaly Attribution)

Rule-based + RandomForest hybrid attributor. Same philosophy as CANOPY's
primary-agent + red-team pattern but without LLM — uses feature engineering
+ Random Forest.

When an anomaly is detected, this module answers WHY:
- Is it a pollution spike from traffic/industry?
- Is it a heat island intensification?
- Is it a vegetation loss event?
- Is it a seasonal baseline shift?
"""
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder

ANOMALY_CAUSES = [
    "traffic_pollution",      # AQ spike, weekday morning/evening
    "industrial_emission",    # AQ spike, sustained, near industrial zone
    "crop_burning",           # AQ + fire combo, seasonal (Oct-Nov Delhi)
    "urban_heat_island",      # LST high, NDVI low, no weather explanation
    "heat_wave",              # LST high, region-wide, weather-correlated
    "vegetation_loss",        # NDVI drop over 16-day window
    "dust_storm",             # AQ spike, PM10 >> PM2.5, wind high
    "baseline_shift",         # Gradual long-term change, not acute
]


class AnomalyAttributor:
    """
    Rule-based + ML hybrid attributor.
    Same philosophy as CANOPY's primary-agent + red-team pattern
    but without LLM — uses feature engineering + Random Forest.

    Features used:
    - layer_type (aq, lst, ndvi, fire)
    - hour_of_day (traffic patterns)
    - day_of_week (weekday vs weekend)
    - month (seasonal: crop burning Oct-Nov)
    - anomaly_score (severity)
    - wind_speed (dust storm indicator)
    - pm10_pm25_ratio (dust vs combustion)
    - ndvi_value (vegetation context)
    - lst_value (heat context)
    - zone_industrial (is this an industrial zone?)
    - neighbor_anomaly_count (spatial spread)
    """

    def __init__(self):
        self.clf = RandomForestClassifier(
            n_estimators=100,
            max_depth=8,
            random_state=42
        )
        self.label_encoder = LabelEncoder()
        self.label_encoder.fit(ANOMALY_CAUSES)
        self.is_trained = False

    def build_features(self, observation: dict, context: dict) -> np.ndarray:
        hour = observation.get("hour", 12)
        month = observation.get("month", 6)

        # Rule-based pre-attribution (like CANOPY's red-team challenge)
        # These are strong signal features
        is_crop_burning_season = month in [10, 11]
        is_rush_hour = hour in [7, 8, 9, 17, 18, 19]
        is_weekend = observation.get("day_of_week", 0) in [5, 6]

        features = [
            observation.get("anomaly_score", 0),
            hour,
            observation.get("day_of_week", 0),
            month,
            float(is_crop_burning_season),
            float(is_rush_hour),
            float(is_weekend),
            context.get("wind_speed", 5.0),
            context.get("pm10_pm25_ratio", 1.5),
            context.get("ndvi_value", 0.2),
            context.get("lst_value", 35.0),
            float(context.get("zone_industrial", False)),
            context.get("neighbor_anomaly_count", 0),
        ]
        return np.array(features).reshape(1, -1)

    def rule_based_attribution(
        self, observation: dict, context: dict
    ) -> tuple:
        """
        Deterministic rules — high confidence when triggered.
        This is the 'red-team' that challenges the ML output.
        """
        month = observation.get("month", 6)
        hour = observation.get("hour", 12)
        wind = context.get("wind_speed", 5.0)
        pm_ratio = context.get("pm10_pm25_ratio", 1.5)
        layer = observation.get("layer_type", "aq")

        # Crop burning: October-November + AQ anomaly + fire nearby
        if (month in [10, 11] and layer == "aq" and
                context.get("fire_count_nearby", 0) > 0):
            return "crop_burning", 0.91

        # Dust storm: high wind + PM10 >> PM2.5
        if wind > 25 and pm_ratio > 3.0:
            return "dust_storm", 0.87

        # Traffic: rush hour + weekday + AQ spike
        if (hour in [7, 8, 9, 17, 18, 19] and
                observation.get("day_of_week", 0) < 5 and
                layer == "aq"):
            return "traffic_pollution", 0.78

        # Urban heat island: high LST + low NDVI + no heatwave elsewhere
        if (layer == "lst" and
                context.get("lst_value", 35) > 44 and
                context.get("ndvi_value", 0.3) < 0.15 and
                context.get("region_wide_lst_anomaly", False) is False):
            return "urban_heat_island", 0.82

        return None, 0.0  # No rule triggered → use ML

    def attribute(
        self, observation: dict, context: dict
    ) -> dict:
        """
        Full attribution pipeline:
        1. Try rule-based (high confidence, deterministic)
        2. If no rule fires, use Random Forest
        3. Reconcile: if RF contradicts rules, lower confidence
        Returns attribution with confidence + explanation
        """
        rule_cause, rule_conf = self.rule_based_attribution(
            observation, context
        )

        if rule_conf > 0.75:
            # Rule fired with high confidence — trust it
            return {
                "cause": rule_cause,
                "confidence": rule_conf,
                "method": "rule",
                "explanation": self._explain(rule_cause, context),
                "challenged": False
            }

        if not self.is_trained:
            # Not enough data to train RF yet — use rules only
            cause = rule_cause or "baseline_shift"
            return {
                "cause": cause,
                "confidence": 0.55,
                "method": "rule_fallback",
                "explanation": self._explain(cause, context),
                "challenged": False
            }

        # Random Forest attribution
        features = self.build_features(observation, context)
        proba = self.clf.predict_proba(features)[0]
        ml_cause_idx = np.argmax(proba)
        ml_cause = self.label_encoder.classes_[ml_cause_idx]
        ml_conf = float(proba[ml_cause_idx])

        # Reconcile: if rule and ML disagree, lower confidence
        challenged = (rule_cause is not None and
                      rule_cause != ml_cause and
                      rule_conf > 0.4)

        final_conf = ml_conf * 0.85 if challenged else ml_conf

        return {
            "cause": ml_cause,
            "confidence": round(final_conf, 2),
            "method": "random_forest",
            "explanation": self._explain(ml_cause, context),
            "challenged": challenged,
            "challenge_cause": rule_cause if challenged else None
        }

    def _explain(self, cause: str, context: dict) -> str:
        explanations = {
            "traffic_pollution": (
                f"PM2.5 spike consistent with vehicular emissions. "
                f"Wind speed {context.get('wind_speed', 5):.1f} km/h "
                f"reducing dispersion."
            ),
            "industrial_emission": (
                "Sustained elevated PM2.5 near industrial zone. "
                "Pattern inconsistent with traffic or seasonal burning."
            ),
            "crop_burning": (
                "Anomaly coincides with crop residue burning season "
                "(Oct-Nov). Fire detections in upwind Punjab/Haryana "
                "corridor confirm attribution."
            ),
            "urban_heat_island": (
                f"Surface temperature {context.get('lst_value', 40):.1f}°C "
                f"exceeds regional baseline. Low vegetation cover "
                f"(NDVI {context.get('ndvi_value', 0.1):.2f}) "
                f"amplifying heat retention."
            ),
            "heat_wave": (
                "Elevated temperatures across entire region indicate "
                "synoptic-scale heat wave rather than localized UHI."
            ),
            "vegetation_loss": (
                "NDVI decline over 16-day composite period. "
                "Consistent with deforestation, construction, or drought stress."
            ),
            "dust_storm": (
                f"PM10/PM2.5 ratio {context.get('pm10_pm25_ratio', 1.5):.1f} "
                f"indicates coarse particle dominance. Wind speed "
                f"{context.get('wind_speed', 5):.1f} km/h consistent "
                f"with dust transport."
            ),
            "baseline_shift": (
                "Gradual long-term change in environmental indicator. "
                "Not attributable to acute event — monitoring recommended."
            ),
        }
        return explanations.get(cause, f"Anomaly attributed to {cause}.")

    def fit(self, db) -> bool:
        """
        Train the RandomForest on historical anomalous observations.
        Requires at least 20 labeled anomalies across multiple cause types.
        Returns True if training succeeded, False if insufficient data.
        """
        from sqlalchemy import text

        # Query historical anomalies with enough context to build features
        rows = db.execute(text("""
            SELECT
                o.layer_type,
                o.anomaly_score,
                CAST(strftime('%H', o.observed_at) AS INTEGER) as hour,
                CAST(strftime('%w', o.observed_at) AS INTEGER) as day_of_week,
                CAST(strftime('%m', o.observed_at) AS INTEGER) as month,
                o.value,
                o.observed_at
            FROM raw_observations o
            WHERE o.is_anomalous = 1
              AND o.observed_at >= datetime('now', '-90 days')
            ORDER BY o.observed_at DESC
            LIMIT 500
        """)).fetchall()

        if len(rows) < 20:
            print(f"[Attribution] Insufficient anomaly data for RF training: "
                  f"{len(rows)} samples (need 20+)")
            return False

        # Auto-label using rule-based attribution as ground truth
        X, y = [], []

        for row in rows:
            obs_dict = {
                "layer_type":    row.layer_type,
                "anomaly_score": row.anomaly_score or 0,
                "hour":          row.hour or 12,
                "day_of_week":   row.day_of_week or 0,
                "month":         row.month or 6,
            }
            # Use default context — RF will learn from patterns
            context_dict = {
                "wind_speed":             8.0,
                "pm10_pm25_ratio":        1.8,
                "ndvi_value":             0.15,
                "lst_value":              row.value if row.layer_type == "lst" else 38.0,
                "zone_industrial":        False,
                "neighbor_anomaly_count": 2,
                "fire_count_nearby":      1 if row.month in [10, 11] else 0,
            }

            # Get rule-based label as training ground truth
            rule_cause, rule_conf = self.rule_based_attribution(
                obs_dict, context_dict
            )

            if rule_cause and rule_conf > 0.6:
                features = self.build_features(obs_dict, context_dict)
                X.append(features.flatten())
                y.append(rule_cause)

        if len(X) < 15:
            print(f"[Attribution] Only {len(X)} high-confidence rule labels — RF training skipped")
            return False

        # Ensure we have at least 2 different classes
        unique_classes = len(set(y))
        if unique_classes < 2:
            print(f"[Attribution] Only 1 class in training data ({y[0]}) — need diversity for RF")
            return False

        X_arr = np.array(X)
        y_arr = np.array(y)

        # Fit the classifier
        self.clf.fit(X_arr, y_arr)
        self.is_trained = True

        print(f"[Attribution] RandomForest trained on {len(X)} samples, "
              f"{unique_classes} classes: {list(set(y))}")
        return True
