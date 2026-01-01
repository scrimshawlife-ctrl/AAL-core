from pathlib import Path
from tempfile import TemporaryDirectory

from aal_core.ers.stabilization import new_state, note_change, tick_cycle
from aal_core.ers.stabilization_store import save_state, load_state


def test_stabilization_state_roundtrip():
    s = new_state()
    note_change(s, "m", "k")
    tick_cycle(s)
    tick_cycle(s)

    with TemporaryDirectory() as td:
        p = Path(td) / "stab.json"
        save_state(s, p)
        s2 = load_state(p)
        assert s2.cycles_since_change[("m", "k")] == 2
