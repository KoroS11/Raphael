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
