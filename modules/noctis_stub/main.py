from typing import List
from aal_core.models import ResonanceFrame


ARCHETYPE_KEYWORDS = {
    "shadow": ["dark", "chase", "falling"],
    "anima": ["ocean", "mother", "room"],
    "trickster": ["clown", "joke", "prank"],
}


def handle_frame(frame: ResonanceFrame, bus) -> List[ResonanceFrame]:
    """
    v0 Noctis stub:
    - Scan text for simple archetypal keywords.
    - Add tags and symbolic_state.
    """
    text = (frame.text or "").lower()
    new_syms = []

    for archetype, kws in ARCHETYPE_KEYWORDS.items():
        if any(kw in text for kw in kws):
            new_syms.append(archetype)

    out = frame.copy()
    out.source = "noctis_stub"
    out.channel = "dream"
    out.symbolic_state = list(set(out.symbolic_state + new_syms))
    out.tags = list(set(out.tags + ["noctis_analysis"]))

    return [out]
