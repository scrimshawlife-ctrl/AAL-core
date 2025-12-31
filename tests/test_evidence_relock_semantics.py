from abx_runes.yggdrasil.evidence_bundle import SCHEMA_VERSION, lock_hash, verify_hash


def test_relock_changes_hash_when_bundle_changes():
    b = {
        "schema_version": SCHEMA_VERSION,
        "created_at": "2025-12-31T00:00:00+00:00",
        "bundle_hash": "",
        "sources": [{"kind": "url", "ref": "x", "digest": "y", "observed_at": "t"}],
        "claims": [{"id": "claim.001", "statement": "s", "confidence": 0.6, "supports": ["x"]}],
        "calibration_refs": [],
        "bridges": [{"from": "a", "to": "b"}],
    }
    b1 = lock_hash(b)
    assert verify_hash(b1) is True

    # mutate content, then relock
    b1["calibration_refs"] = [{"kind": "metrics_run", "ref": "run-001", "digest": "deadbeef"}]
    b2 = lock_hash(b1)
    assert verify_hash(b2) is True
    assert b2["bundle_hash"] != b1["bundle_hash"]
