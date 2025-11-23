from typing import List
from aal_core.models import ResonanceFrame


def handle_frame(frame: ResonanceFrame, bus) -> List[ResonanceFrame]:
    """
    v0 Abraxas:
    - Take incoming text.
    - Echo back a trivial 'oracle' with a coherence metric.
    Later, this will call an LLM or your own model.
    """
    text = frame.text or ""
    # Extremely dumb oracle: reverse text and pretend it's insight.
    oracle_text = text[::-1]

    out = ResonanceFrame(
        source="abraxas_basic",
        channel="oracle",
        text=oracle_text,
        tags=frame.tags + ["oracle_basic"],
        symbolic_state=frame.symbolic_state,
        metrics={"coherence": 0.1},  # placeholder until we define real metrics
    )

    return [out]
