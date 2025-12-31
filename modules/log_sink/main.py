from typing import List
from aal_core.models import ResonanceFrame


def handle_frame(frame: ResonanceFrame, bus) -> List[ResonanceFrame]:
    """
    Log frames for now. Later: write to sqlite or another store.
    """
    print(f"[LOG_SINK] {frame.timestamp} {frame.channel} {frame.source} {frame.id} {frame.text}")
    return []
