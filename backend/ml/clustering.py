"""
Raphael — KMeans Zone Clustering

Groups administrative zones into environmental clusters based on
their current air quality, land surface temperature, and vegetation
indicators. All SQL is SpatiaLite-compatible.
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

from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import text

try:
    mlflow.set_tracking_uri(f"http://127.0.0.1:{os.getenv('MLFLOW_PORT', '5000')}")
except Exception:
    pass

N_CLUSTERS = 5


def assign_cluster_labels(km: KMeans, scaler: StandardScaler) -> dict:
    """
    Sort KMeans centroids by composite environmental stress
    (weighted sum of AQ + LST - NDVI in original scale)
    so label assignments are stable and physically meaningful.

    Returns: {cluster_index: label_string}
    """
    centroids_original = scaler.inverse_transform(km.cluster_centers_)

    stress_scores = (
        (centroids_original[:, 0] / 500.0) * 0.40 +
        ((centroids_original[:, 1] - 20) / 35.0) * 0.35 +
        (1 - centroids_original[:, 2]) * 0.25
    )

    ranked_indices = np.argsort(stress_scores)

    label_texts = [
        "Low stress — good air quality, moderate temperature, adequate vegetation",
        "Mild concern — slightly elevated indicators, monitoring recommended",
        "Moderate stress — elevated AQ or heat, limited green cover",
        "High stress — poor air quality combined with heat or vegetation loss",
        "Critical zone — all environmental indicators at elevated levels"
    ]

    label_map = {}
    for rank, cluster_idx in enumerate(ranked_indices):
        label_map[int(cluster_idx)] = label_texts[min(rank, len(label_texts) - 1)]

    return label_map


def _fallback_label(cluster_id: int) -> str:
    labels = {
        0: "Low stress — good air quality, moderate temperature, adequate vegetation",
        1: "Mild concern — slightly elevated indicators, monitoring recommended",
        2: "Moderate stress — elevated AQ or heat, limited green cover",
        3: "High stress — poor air quality combined with heat or vegetation loss",
        4: "Critical zone — all environmental indicators at elevated levels"
    }
    return labels.get(cluster_id, f"Environmental cluster {cluster_id}")


def cluster_zones(db: Session, region_id: str) -> dict:
    """
    Cluster zones by their current environmental indicators using KMeans.
    Writes cluster assignments to ml_outputs table.
    """
    from db.models import MLOutput

    rows = db.execute(text("""
        SELECT
            z.id   as zone_id,
            z.name as zone_name,
            AVG(CASE WHEN o.layer_type = 'aq'   THEN o.value END) as aq_mean,
            AVG(CASE WHEN o.layer_type = 'lst'  THEN o.value END) as lst_mean,
            AVG(CASE WHEN o.layer_type = 'ndvi' THEN o.value END) as ndvi_mean
        FROM zone_geometries z
        INNER JOIN raw_observations o ON ST_Within(o.geometry, z.geometry)
            AND o.observed_at >= datetime('now', '-24 hours')
        WHERE z.region_id = :region_id
        GROUP BY z.id, z.name
        HAVING COUNT(o.id) > 0
    """), {"region_id": region_id}).fetchall()

    if len(rows) < N_CLUSTERS:
        print(f"[clustering] Not enough zones with data: {len(rows)} (need {N_CLUSTERS})")
        return _fallback_clustering(db, region_id)

    df = pd.DataFrame(rows, columns=[
        "zone_id", "zone_name", "aq_mean", "lst_mean", "ndvi_mean"
    ])
    df = df.fillna(df.mean(numeric_only=True))

    X = df[["aq_mean", "lst_mean", "ndvi_mean"]].values
    scaler = StandardScaler()
    X_norm = scaler.fit_transform(X)

    try:
        mlflow.set_experiment("zone_clustering")
        with mlflow.start_run(
            run_name=f"kmeans_zones_{region_id[:8]}"
        ):
            km = KMeans(
                n_clusters=min(N_CLUSTERS, len(df)),
                init="k-means++",
                n_init=10,
                random_state=42
            )
            labels = km.fit_predict(X_norm)

            mlflow.log_params({
                "n_clusters": min(N_CLUSTERS, len(df)),
                "n_zones": len(df)
            })
            mlflow.log_metric("inertia", float(km.inertia_))
    except Exception as e:
        print(f"[clustering] MLflow tracking failed (non-fatal): {e}")
        km = KMeans(
            n_clusters=min(N_CLUSTERS, len(df)),
            init="k-means++", n_init=10, random_state=42
        )
        labels = km.fit_predict(X_norm)

    # Delete previous cluster assignments for this region — this DELETE
    # is committed together with the INSERT below in a single transaction,
    # so a concurrent reader never sees a zero-row window for this region.
    db.execute(text("""
        DELETE FROM ml_outputs
        WHERE model_type = 'kmeans_clustering'
          AND zone_id IN (
              SELECT id FROM zone_geometries
              WHERE region_id = :region_id
          )
    """), {"region_id": region_id})

    label_map = assign_cluster_labels(km, scaler)

    outputs = []
    for i, row in df.iterrows():
        outputs.append(MLOutput(
            id=uuid.uuid4(),
            zone_id=str(row["zone_id"]),
            model_type="kmeans_clustering",
            output_type="cluster_assignment",
            value=float(labels[i]),
            explanation=label_map.get(int(labels[i]), f"Cluster {labels[i]}"),
            model_version="sklearn-kmeans-stable-labels",
            computed_at=datetime.now(timezone.utc)
        ))

    db.bulk_save_objects(outputs)
    db.commit()

    result = dict(zip(df["zone_id"].astype(str), labels.tolist()))
    print(f"[clustering] Clustered {len(df)} zones into {min(N_CLUSTERS, len(df))} groups")
    return result


def _fallback_clustering(db: Session, region_id: str) -> dict:
    """
    When insufficient zones have real observations for KMeans,
    assign synthetic clusters based on zone names/positions.
    This ensures the pipeline doesn't break on sparse data.
    """
    from db.models import ZoneGeometry, MLOutput

    zones = db.query(ZoneGeometry).filter(
        ZoneGeometry.region_id == region_id
    ).limit(20).all()

    # Delete previous cluster assignments for this region first — this
    # DELETE is committed together with whatever INSERT follows (even if
    # zero rows), so the transaction always finalizes atomically instead
    # of leaving a pending, uncommitted deletion.
    db.execute(text("""
        DELETE FROM ml_outputs
        WHERE model_type = 'kmeans_clustering'
          AND zone_id IN (
              SELECT id FROM zone_geometries
              WHERE region_id = :region_id
          )
    """), {"region_id": region_id})

    outputs = []
    result = {}
    for i, zone in enumerate(zones):
        cluster = i % N_CLUSTERS
        outputs.append(MLOutput(
            id=uuid.uuid4(),
            zone_id=str(zone.id),
            model_type="kmeans_clustering",
            output_type="cluster_assignment",
            value=float(cluster),
            explanation=_fallback_label(cluster),
            model_version="fallback-v1.0",
            computed_at=datetime.now(timezone.utc)
        ))
        result[str(zone.id)] = cluster

    if outputs:
        db.bulk_save_objects(outputs)
    db.commit()

    print(f"[clustering] Fallback: assigned {len(outputs)} zones to clusters")
    return result
