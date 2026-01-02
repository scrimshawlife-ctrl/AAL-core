import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[5] / "src"))

from aal_core.modules.luma.ideation.constraints import validate_pattern_spec


def test_constraints_reject_causality_claims():
    spec = {
        "pattern_id": "proposal.bad",
        "primitives": ["nodes"],
        "layers": ["x"],
        "channels": {"size": "edge.resonance_magnitude"},
        "mappings": [{"source": "edge.resonance_magnitude", "target": "size"}],
        "intent": "bad",
        "claims": ["this causes that"],
    }
    try:
        validate_pattern_spec(spec)
        assert False, "expected rejection"
    except ValueError:
        assert True
