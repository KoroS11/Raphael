"""
Blue Team — Evidence Aggregation Layer.

Collects outputs from already-validated modules (PCAD anomaly
detection, Gaussian Plume physics, Prophet+LSTM forecasting,
weather) into a single structured Evidence Object per observation.

This module performs NO inference and trains NO model. It is a
deterministic aggregator: its only job is to assemble evidence
that already exists elsewhere in the pipeline into one traceable
record, in preparation for Red Team challenge and Symbolic
reconciliation (see ml/rules.py).

Fields marked "not computed in production" reflect components
validated only in the research notebooks (e.g. SHAP) and are
included as optional/null so the schema is honest about current
system coverage rather than implying capabilities that don't run
live.
"""

from dataclasses import dataclass, asdict, field
from typing import Optional
from datetime import datetime
from ml.rules import get_rule


@dataclass
class EvidenceObject:
