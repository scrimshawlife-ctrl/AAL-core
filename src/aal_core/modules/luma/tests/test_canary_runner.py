import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[5] / "src"))

from aal_core.modules.luma.contracts.proposal_ir import PatternProposal
from aal_core.modules.luma.governance.canary_runner import CanaryRunner
from aal_core.modules.luma.governance.ledger import append_entry, make_entry


def test_canary_runner_selects_only_accepted(tmp_path):
    ledger = str(tmp_path / "ledger.json")

    p1 = PatternProposal(
        proposal_id="p1",
        base_patterns=["a"],
        pattern_spec={
            "pattern_id": "proposal.x",
            "primitives": ["matrix"],
            "layers": [],
            "channels": {},
            "mappings": [],
        },
        justification={},
        scores={"info_gain": 0.5},
        risks={},
        provenance={"scene_hash": "s1"},
    )
    p2 = PatternProposal(
        proposal_id="p2",
        base_patterns=["a"],
        pattern_spec={
            "pattern_id": "proposal.y",
            "primitives": ["timeline"],
            "layers": [],
            "channels": {},
            "mappings": [],
        },
        justification={},
        scores={"info_gain": 0.6},
        risks={},
        provenance={"scene_hash": "s1"},
    )

    append_entry(ledger, make_entry("accepted_for_canary", "p2", "sha", "s1", "tester", {}))

    runner = CanaryRunner()
    report = runner.run([p1, p2], ledger, scene_hash="s1")

    assert len(report.items) == 1
    assert report.items[0].proposal_id == "p2"
