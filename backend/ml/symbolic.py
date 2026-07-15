"""
Symbolic Layer orchestration — runs Blue Team aggregation, Red Team
challenge, and reconciliation, returning one final annotated record
per evidence object. Pure orchestration; all decision logic lives
in ml/rules.py (reconcile_evidence) and ml/red_team.py.
"""

def run_symbolic_layer(db, region_id: str) -> list:
    from ml.evidence import aggregate_evidence
    from ml.red_team import challenge_evidence
    from ml.rules import reconcile_evidence

    evidence_list = aggregate_evidence(db, region_id=region_id)
    if not evidence_list:
        return []

    challenge_results = challenge_evidence(evidence_list, db)
    challenge_by_key = {
        (c.station_name, c.observed_at): c for c in challenge_results
    }

    annotated = []
    for e in evidence_list:
        key = (e.station_name, e.observed_at)
        challenge = challenge_by_key.get(key)
        robustness = challenge.robustness if challenge else None

        verdict_info = reconcile_evidence(e.confidence, robustness)

        annotated.append({
            "evidence": e.to_dict(),
            "challenge": challenge.to_dict() if challenge else None,
            "verdict": verdict_info["verdict"],
            "symbolic_rule_id": verdict_info["symbolic_rule_id"],
            "symbolic_rationale": verdict_info["rationale"],
        })

    return annotated
