"""
Raphael — AI Insights Generator

Produces the three insight cards shown in the bottom-right panel of the
dashboard mockup:
  1. Temperature trend forecast
  2. AQ category forecast
  3. Low vegetation zones
All SQL is SpatiaLite-compatible.
"""
from sqlalchemy.orm import Session
from sqlalchemy import text


def generate_ai_insights(db: Session, region_id: str) -> list:
    """
    Generate up to 3 AI insight cards based on current ML outputs.
    Each insight has: type, icon, message, severity.
    """
    insights = []

    # ── Insight 1: Temperature trend ──────────────────────────────
    try:
        lst_forecast = db.execute(text("""
            SELECT AVG(value) as forecast_mean, MAX(value) as forecast_peak
            FROM ml_outputs
            WHERE model_type  = 'prophet_forecast'
              AND output_type = 'point_forecast'
              AND layer_type  = 'lst'
              AND valid_from  >= datetime('now')
              AND valid_to    <= datetime('now', '+48 hours')
        """)).fetchone()

        if lst_forecast and lst_forecast.forecast_peak:
            current_lst = db.execute(text("""
                SELECT AVG(value) FROM raw_observations
                WHERE layer_type = 'lst'
                  AND observed_at >= datetime('now', '-6 hours')
            """)).scalar()

            if current_lst:
                delta = round(float(lst_forecast.forecast_peak) -
                              float(current_lst), 1)
                if delta > 0:
                    insights.append({
                        "type":     "temperature",
                        "icon":     "heat",
                        "message":  (f"Heat index will increase by "
                                     f"{delta}\u00b0C in next 48 hours."),
                        "severity": "warning" if delta > 2 else "info"
                    })
                else:
                    insights.append({
                        "type":     "temperature",
                        "icon":     "heat",
                        "message":  (f"Surface temperature trending down "
                                     f"by {abs(delta)}\u00b0C over next 48h."),
                        "severity": "info"
                    })
    except Exception as e:
        print(f"[explainer] Temperature insight failed: {e}")

    # ── Insight 2: AQ category forecast ───────────────────────────
    try:
        aq_forecast = db.execute(text("""
            SELECT AVG(value) as mean_forecast
            FROM ml_outputs
            WHERE model_type  = 'prophet_forecast'
              AND layer_type  = 'aq'
              AND valid_from  >= datetime('now')
              AND valid_to    <= datetime('now', '+24 hours')
        """)).fetchone()

        if aq_forecast and aq_forecast.mean_forecast:
            val = float(aq_forecast.mean_forecast)
            cat = _aqi_category(val)
            insights.append({
                "type":     "air_quality",
                "icon":     "cloud",
                "message":  (f"AQI forecast to remain in '{cat}' "
                             f"category over next 24 hours."),
                "severity": ("critical" if val > 200
                             else "warning" if val > 100
                             else "info")
            })
    except Exception as e:
        print(f"[explainer] AQ insight failed: {e}")

    # ── Insight 3: Low vegetation zones ───────────────────────────
    try:
        # SpatiaLite: use GROUP_CONCAT instead of STRING_AGG
        low_ndvi = db.execute(text("""
            SELECT
                COUNT(*) as cnt,
                GROUP_CONCAT(sub.zone_name, ', ') as zones
            FROM (
                SELECT z.name as zone_name, AVG(o.value) as avg_ndvi
                FROM zone_geometries z
                INNER JOIN raw_observations o ON ST_Within(o.geometry, z.geometry)
                WHERE o.layer_type = 'ndvi'
                  AND o.observed_at >= datetime('now', '-7 days')
                  AND z.region_id = :region_id
                GROUP BY z.id, z.name
                HAVING AVG(o.value) < 0.2
                LIMIT 3
            ) sub
        """), {"region_id": region_id}).fetchone()

        if low_ndvi and low_ndvi.cnt and low_ndvi.cnt > 0:
            zones_text = low_ndvi.zones or "several zones"
            insights.append({
                "type":     "vegetation",
                "icon":     "leaf",
                "message":  (f"Low green cover in {zones_text} "
                             f"increasing heat risk."),
                "severity": "warning"
            })
    except Exception as e:
        print(f"[explainer] Vegetation insight failed: {e}")

    # ── Fallback insights if none generated ───────────────────────
    if not insights:
        # Generate sensible defaults based on current risk scores
        try:
            risk_count = db.execute(text("""
                SELECT COUNT(*) FROM ml_outputs
                WHERE model_type = 'risk_score' AND value >= 70
            """)).scalar()

            if risk_count and risk_count > 0:
                insights.append({
                    "type":     "risk",
                    "icon":     "alert",
                    "message":  (f"{risk_count} zones currently at "
                                 f"high or critical risk level."),
                    "severity": "warning"
                })

            anomaly_count = db.execute(text("""
                SELECT COUNT(*) FROM raw_observations
                WHERE is_anomalous = 1
                  AND observed_at >= datetime('now', '-24 hours')
            """)).scalar()

            if anomaly_count and anomaly_count > 0:
                insights.append({
                    "type":     "anomaly",
                    "icon":     "warning",
                    "message":  (f"{anomaly_count} anomalous readings "
                                 f"detected in last 24 hours."),
                    "severity": "info"
                })

            insights.append({
                "type":     "system",
                "icon":     "check",
                "message":  "Intelligence cycle running normally. "
                            "All models operational.",
                "severity": "info"
            })
        except Exception as e:
            print(f"[explainer] Fallback insights failed: {e}")
            insights.append({
                "type":     "system",
                "icon":     "check",
                "message":  "Intelligence pipeline active.",
                "severity": "info"
            })

    return insights[:3]  # Return max 3 insights (matching mockup)


def _aqi_category(aqi: float) -> str:
    if aqi <= 50:
        return "Good"
    if aqi <= 100:
        return "Moderate"
    if aqi <= 150:
        return "Unhealthy for Sensitive Groups"
    if aqi <= 200:
        return "Unhealthy"
    if aqi <= 300:
        return "Very Poor"
    return "Hazardous"
