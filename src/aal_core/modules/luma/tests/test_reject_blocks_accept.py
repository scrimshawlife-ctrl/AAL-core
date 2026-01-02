import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[5] / "src"))

from aal_core.modules.luma.governance.ledger import load_ledger
from aal_core.modules.luma.governance.ops import accept_for_canary, reject


def test_reject_blocks_accept(tmp_path):
    ledger = str(tmp_path / "ledger.json")
    proposal = {"proposal_id": "pX", "provenance": {"scene_hash": "s1"}}

    reject(ledger, proposal, actor="tester", reason="no")
    try:
        accept_for_canary(ledger, proposal, actor="tester", note="yes")
        assert False, "expected error"
    except ValueError:
        assert True

    obj = load_ledger(ledger)
    assert obj["entries"][0]["action"] == "rejected"
