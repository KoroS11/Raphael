"""
Gemma Explanation Layer.

Consumes ONLY the structured, symbolic-layer-annotated evidence
record (evidence + challenge + verdict) produced by
ml/symbolic.run_symbolic_layer(). Produces a natural-language
explanation of the finding.

Gemma reads facts and writes prose. It does not see raw logs, does
not re-run any model, and — critically — its output NEVER feeds
back into confidence, rule_id, robustness, or verdict. Those are
already final by the time this layer runs. This preserves the
"Gemma explains, does not decide" boundary from the architecture
contract.
"""

import requests
import json

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_TAG = "gemma3:4b"


def build_prompt(annotated_record: dict) -> str:
    """
    Build a fact-only prompt from one symbolic-layer-annotated
    record. No speculation, no fields the record doesn't contain.
    """
    ev = annotated_record["evidence"]
    challenge = annotated_record.get("challenge")
    verdict = annotated_record["verdict"]
    symbolic_rule = annotated_record["symbolic_rule_id"]
    symbolic_rationale = annotated_record["symbolic_rationale"]

    facts = [
        f"Station: {ev['station_name']}",
        f"Time: {ev['observed_at']}",
        f"PM2.5 reading: {ev['value']} ug/m3",
        f"Statistical anomaly detected: {ev['if_anomaly']} (IsolationForest score: {ev.get('anomaly_score')})",
        f"Gaussian Plume predicted concentration at this station: {ev.get('plume_conc')} ug/m3",
        f"Physics corroboration: {ev.get('plume_corroborated')}",
        f"PCAD confidence tier: {ev['confidence']} (rule {ev['rule_id']})",
    ]
    if ev.get("wind_speed") is not None:
        facts.append(f"Wind speed: {ev['wind_speed']} m/s, direction: {ev.get('wind_direction')} degrees")
    if challenge:
        facts.append(f"Red Team robustness assessment: {challenge['robustness']} ({challenge['n_challenges_triggered']} concerns raised)")
        for check in ["wind_consistency", "meteorological_plausibility", "magnitude_sanity", "temporal_isolation"]:
            if challenge.get(f"{check}_triggered"):
                facts.append(f"  - {check}: {challenge[f'{check}_detail']}")
    facts.append(f"Final symbolic verdict: {verdict} (rule {symbolic_rule})")
    facts.append(f"Verdict rationale: {symbolic_rationale}")

    prompt = (
        "You are an environmental monitoring assistant. Below is structured "
        "evidence about one air quality observation, already processed by an "
        "automated anomaly detection, physics-corroboration, and evidence-review "
        "pipeline. Write a clear, factual explanation of what was found and why "
        "it received this verdict. Use ONLY the facts given below — do not "
        "invent details, causes, or sources not stated. If evidence is limited "
        "or the verdict is uncertain, say so plainly rather than overstating "
        "confidence. Keep it to 3-5 sentences, written for a non-technical "
        "reader who still wants the real reasoning, not just a summary label.\n\n"
        "EVIDENCE:\n" + "\n".join(facts) + "\n\nEXPLANATION:"
    )
    return prompt


def generate_explanation(annotated_record: dict, timeout: int = 60) -> dict:
    """
    Call local Gemma via Ollama with the fact-only prompt.
    Returns: {"explanation": str, "model": str, "status": "ok"|"error", "error": str|None}
    """
    prompt = build_prompt(annotated_record)
    try:
        resp = requests.post(
            OLLAMA_URL,
            json={"model": MODEL_TAG, "prompt": prompt, "stream": False},
            timeout=timeout
        )
        resp.raise_for_status()
        data = resp.json()
        return {
            "explanation": data.get("response", "").strip(),
            "model": MODEL_TAG,
            "status": "ok",
            "error": None,
        }
    except Exception as e:
        return {
            "explanation": None,
            "model": MODEL_TAG,
            "status": "error",
            "error": str(e),
        }
