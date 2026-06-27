"""
Raphael — Intelligence Layer (Multi-Stage ML Pipeline)

Four-stage pipeline:
  Stage 1 — DETECT    (IsolationForest anomaly detection)
  Stage 2 — ATTRIBUTE (Rule-based + RandomForest hybrid)
  Stage 3 — FORECAST  (Prophet per zone per layer)
  Stage 4 — DECIDE    (Risk scorer + action recommender)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

