"""
Versioned rule base for RAPHAEL's symbolic evidence-fusion layer.

Formalizes the confidence-tier logic used by PCAD (Physics-
Corroborated Anomaly Detection) as explicit, citable rules rather
than inline conditionals. Each rule records its condition, the
evidence it consumes, its output, and a rationale.

This is Tier 2 (versioned domain rules) in RAPHAEL's knowledge
architecture. Tier 1 (immutable physics/WHO constants) lives in
ml/plume.py and ml/risk_score.py. Tier 3 (adaptive, evidence-
weighted rules) is not implemented in this study — see Future Work.

Note on independence: the Gaussian Plume feature is physics-informed
but not fully independent of the sensor reading, since its emission
proxy Q is derived from the observed PM2.5 value. Rule rationale
text below reflects this — corroboration, not independent validation.

The current implementation contains three version-controlled domain
rules. The framework is intentionally extensible (see `priority`
field) but only these validated rules are included in the present
study.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Rule:
    rule_id: str
    name: str
    conditions: dict         # machine-parseable condition
    evidence_used: tuple      # evidence sources this rule consumes
    output: str                # confidence tier this rule assigns
    rationale: str              # design justification (not a proof claim)
    priority: int = 0            # placeholder for future rule ordering; unused
    version: str = "1.0"


RULE_REGISTRY = {
    "R001": Rule(
        rule_id="R001",
        name="physics_corroborated_anomaly",
        conditions={"if_anomaly": True, "plume_corroborated": True},
        evidence_used=("IsolationForest", "GaussianPlume"),
        output="HIGH",
        rationale=(
            "Agreement between the statistical detector and the "
            "atmospheric dispersion model provides corroborating "
            "evidence, increasing confidence in the detected event. "
            "Note: the dispersion model's emission proxy is derived "
