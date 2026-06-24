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
