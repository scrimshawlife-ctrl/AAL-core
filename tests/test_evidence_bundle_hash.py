from abx_runes.yggdrasil.evidence_bundle import SCHEMA_VERSION, lock_hash, verify_hash


def test_lock_and_verify_roundtrip():
    """
    Test that lock_hash computes and sets bundle_hash, and verify_hash confirms it.
    """
    b = {
        "schema_version": SCHEMA_VERSION,
        "created_at": "2025-12-31T00:00:00+00:00",
        "bundle_hash": "",
        "sources": [{"kind": "url", "ref": "x", "digest": "y", "observed_at": "t"}],
        "claims": [{"id": "claim.001", "statement": "s", "confidence": 0.6, "supports": ["x"]}],
        "calibration_refs": [],
    }
    b2 = lock_hash(b)
    assert verify_hash(b2) is True
    assert b2["bundle_hash"] != ""


def test_verify_hash_rejects_tampered_bundle():
    """
    Test that verify_hash detects tampering.
    """
    b = {
        "schema_version": SCHEMA_VERSION,
        "created_at": "2025-12-31T00:00:00+00:00",
        "bundle_hash": "",
        "sources": [{"kind": "url", "ref": "x", "digest": "y", "observed_at": "t"}],
        "claims": [{"id": "claim.001", "statement": "s", "confidence": 0.6, "supports": ["x"]}],
        "calibration_refs": [],
    }
    b2 = lock_hash(b)
    # Tamper with the bundle
    b2["claims"][0]["statement"] = "tampered"
    assert verify_hash(b2) is False


def test_hash_is_deterministic():
    """
    Test that hashing the same bundle twice gives the same result.
    """
    b = {
        "schema_version": SCHEMA_VERSION,
        "created_at": "2025-12-31T00:00:00+00:00",
        "bundle_hash": "",
        "sources": [{"kind": "url", "ref": "x", "digest": "y", "observed_at": "t"}],
        "claims": [{"id": "claim.001", "statement": "s", "confidence": 0.6, "supports": ["x"]}],
        "calibration_refs": [],
    }
    b1 = lock_hash(b)
    b2 = lock_hash(b)
    assert b1["bundle_hash"] == b2["bundle_hash"]
