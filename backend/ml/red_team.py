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
