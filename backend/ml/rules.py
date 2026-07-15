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
            "from the observed value, so this is physics-informed "
            "corroboration rather than a fully independent check."
        ),
        priority=10,
    ),
    "R002": Rule(
        rule_id="R002",
        name="statistical_anomaly_uncorroborated",
        conditions={"if_anomaly": True, "plume_corroborated": False},
        evidence_used=("IsolationForest",),
        output="MEDIUM",
        rationale=(
            "An anomaly is flagged by the statistical detector but "
            "the dispersion model does not predict elevated "
            "concentration at this station given current wind. Lack "
            "of corroboration may result from model limitations, "
            "meteorological uncertainty, or localized phenomena not "
            "represented by the simplified dispersion model. Retained "
            "as a distinct evidence-weighted tier rather than "
            "discarded."
        ),
        priority=10,
    ),
    "R003": Rule(
        rule_id="R003",
        name="no_anomaly",
        conditions={"if_anomaly": False},
        evidence_used=("IsolationForest",),
        output="NORMAL",
        rationale="No statistical anomaly detected; dispersion model not consulted.",
        priority=0,
    ),
}


def evaluate_confidence(if_anomaly: bool, plume_corroborated: bool) -> dict:
    """
    Apply the versioned rule base to a single observation's evidence.

    Returns: {"confidence": str, "rule_id": str, "evidence_used": tuple}

    Deterministic wrapper around the logic previously inlined in
    compute_pcad_scores(). Behavior is unchanged from the original
    if/else; only traceability is added.
    """
    if not if_anomaly:
        r = RULE_REGISTRY["R003"]
    elif plume_corroborated:
        r = RULE_REGISTRY["R001"]
    else:
        r = RULE_REGISTRY["R002"]
    return {"confidence": r.output, "rule_id": r.rule_id, "evidence_used": r.evidence_used}


def get_rule(rule_id: str) -> Optional[Rule]:
    return RULE_REGISTRY.get(rule_id)


def rules_summary() -> str:
    """Human-readable dump of the current rule base, for logging/paper appendix."""
    lines = ["RAPHAEL Rule Base (Tier 2 — versioned domain rules)"]
    for r in RULE_REGISTRY.values():
        lines.append(
            f"  [{r.rule_id}] {r.name} (v{r.version}, priority={r.priority})\n"
            f"    IF: {r.conditions}\n"
            f"    THEN: confidence = {r.output}\n"
            f"    Evidence used: {r.evidence_used}\n"
            f"    Rationale: {r.rationale}"
        )
    return "\n".join(lines)


# ── SYMBOLIC RECONCILIATION LAYER ───────────────────────────
"""
Symbolic Reconciliation Layer.

Extends the Tier 2 rule base with a second registry (S-prefixed,
distinct from PCAD's R-prefixed rules) that reconciles Blue Team
evidence (confidence tier from R001-R003) with Red Team challenge
output (robustness) into a single traceable verdict.

This layer never overwrites the original PCAD confidence or
rule_id — those remain as-assigned, preserving the provenance of
each layer's independent assessment. The symbolic verdict is
appended as a separate field so a reader can always trace: "PCAD
said X (rule R00n), Red Team found it Y-robust, Symbolic Layer
therefore concluded Z (rule S00n)."

Deterministic table, no learning, no adaptive weighting.
"""


@dataclass(frozen=True)
class ReconciliationRule:
    rule_id: str
    name: str
    conditions: dict
    verdict: str
    rationale: str
    priority: int = 0
    version: str = "1.0"


RECONCILIATION_REGISTRY = {
    "S001": ReconciliationRule(
        rule_id="S001",
        name="confirmed_high_confidence",
        conditions={"confidence": "HIGH", "robustness": "ROBUST"},
        verdict="CONFIRMED",
        rationale=(
            "Physics-corroborated anomaly (R001) that also passed all "
            "Red Team deterministic challenge checks. This is the "
            "strongest verdict tier available under the current "
            "architecture: both agreement (Blue Team) and absence of "
            "identified fragility (Red Team) support the finding."
        ),
        priority=20,
    ),
    "S002": ReconciliationRule(
        rule_id="S002",
        name="contested_high_confidence",
        conditions={"confidence": "HIGH", "robustness": "FRAGILE"},
        verdict="CONTESTED",
        rationale=(
            "Physics-corroborated anomaly (R001) but Red Team "
            "identified at least one plausibility concern (e.g. "
            "missing/implausible meteorology, borderline anomaly "
            "score, or lack of temporal persistence). The original "
            "R001 assignment is preserved for traceability; this "
            "verdict flags that the corroboration should not be "
            "treated as conclusive without further review."
        ),
        priority=15,
    ),
    "S003": ReconciliationRule(
        rule_id="S003",
        name="plausible_medium_confidence",
        conditions={"confidence": "MEDIUM", "robustness": "ROBUST"},
        verdict="PLAUSIBLE",
        rationale=(
            "Statistically anomalous (R002) without physics "
            "corroboration, but passed all Red Team checks — no "
            "additional reason for caution was found beyond the "
            "known limitation that physics did not corroborate."
        ),
        priority=10,
    ),
    "S004": ReconciliationRule(
        rule_id="S004",
        name="weak_medium_confidence",
        conditions={"confidence": "MEDIUM", "robustness": "FRAGILE"},
        verdict="WEAK",
        rationale=(
            "Statistically anomalous (R002) without physics "
            "corroboration, and Red Team identified additional "
            "concerns. Lowest-confidence non-normal verdict; "
            "consistent with either a real minor event or sensor "
            "noise — architecture does not currently distinguish "
            "these without further evidence."
        ),
        priority=5,
    ),
    "S005": ReconciliationRule(
        rule_id="S005",
        name="normal_no_reconciliation_needed",
        conditions={"confidence": "NORMAL"},
        verdict="NORMAL",
        rationale="No anomaly detected; Red Team does not run on normal readings, so no reconciliation is needed.",
        priority=0,
    ),
}


def reconcile_evidence(confidence: str, robustness: Optional[str]) -> dict:
    """
    Reconcile Blue Team confidence with Red Team robustness into a
    final symbolic verdict. Pure lookup, deterministic, no learning.

    robustness is None for NORMAL-confidence evidence, since Red
    Team only runs on anomalous (if_anomaly=True) records.

    Returns: {"verdict": str, "symbolic_rule_id": str, "rationale": str}
    """
    if confidence == "NORMAL":
        r = RECONCILIATION_REGISTRY["S005"]
    elif confidence == "HIGH" and robustness == "ROBUST":
        r = RECONCILIATION_REGISTRY["S001"]
    elif confidence == "HIGH" and robustness == "FRAGILE":
        r = RECONCILIATION_REGISTRY["S002"]
    elif confidence == "MEDIUM" and robustness == "ROBUST":
        r = RECONCILIATION_REGISTRY["S003"]
    elif confidence == "MEDIUM" and robustness == "FRAGILE":
        r = RECONCILIATION_REGISTRY["S004"]
    else:
        # Defensive fallback — should not occur given current rule set,
        # but fail loudly rather than silently misclassify.
        return {"verdict": "UNRECOGNIZED", "symbolic_rule_id": None,
                "rationale": f"No reconciliation rule matched confidence={confidence}, robustness={robustness}"}

    return {"verdict": r.verdict, "symbolic_rule_id": r.rule_id, "rationale": r.rationale}


def reconciliation_summary() -> str:
    lines = ["RAPHAEL Symbolic Reconciliation Rules (Blue Team x Red Team)"]
    for r in RECONCILIATION_REGISTRY.values():
        lines.append(
            f"  [{r.rule_id}] {r.name} (v{r.version}, priority={r.priority})\n"
            f"    IF: {r.conditions}\n"
            f"    THEN: verdict = {r.verdict}\n"
            f"    Rationale: {r.rationale}"
        )
    return "\n".join(lines)
