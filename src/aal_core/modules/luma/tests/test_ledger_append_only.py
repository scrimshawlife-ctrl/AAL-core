import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[5] / "src"))

from aal_core.modules.luma.governance.ledger import append_entry, load_ledger, make_entry


def test_ledger_append_only(tmp_path):
    ledger = str(tmp_path / "ledger.json")

    append_entry(
        ledger,
        make_entry("proposed_exported", "p1", "sha1", "scene1", "tester", {"x": 1}),
    )
    append_entry(
        ledger,
        make_entry(
            "accepted_for_canary",
            "p1",
            "sha1",
            "scene1",
            "tester",
            {"note": "ok"},
        ),
    )

    obj = load_ledger(ledger)
    assert len(obj["entries"]) == 2
    assert obj["entries"][0]["action"] == "proposed_exported"
    assert obj["entries"][1]["action"] == "accepted_for_canary"
