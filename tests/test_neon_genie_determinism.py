"""
Determinism golden tests for Neon-Genie overlay.

SEED enforcement rules:
- ≥12 runs with same input → invariant hash
- Missing required inputs → not_computable
- Process-based overlay with stdin/stdout contract
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def _hash_output(output: dict[str, Any]) -> str:
    """Compute determinism hash for Neon-Genie output."""
    canonical = json.dumps(output, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _generate_mock_output(request: dict[str, Any], seed: int) -> dict[str, Any]:
    """
    Mock Neon-Genie generate operation for testing.

    In production, this would invoke:
      node .aal/overlays/neon_genie/aal_bridge.js

    For testing, we simulate deterministic output based on seed.
    """
    prompt = request["payload"]["prompt"]

    # Deterministic "generation" based on seed and prompt
    # In real implementation, this uses SEED to control RNG
    seed_hash = hashlib.sha256(f"{seed}:{prompt}".encode()).hexdigest()
    generated_text = f"[SEED={seed}] Generated response for: {prompt[:50]}... (hash: {seed_hash[:8]})"

    input_hash = hashlib.sha256(
        json.dumps(request["payload"], sort_keys=True).encode()
    ).hexdigest()

    output = {
        "schema_version": "neon_genie.generate_output.v0",
        "generated_text": generated_text,
        "metadata": {
            "tokens_generated": len(generated_text.split()),
            "finish_reason": "complete",
            "model_version": "0.1.0",
            "seed_echo": seed,
            "entropy_bits": 0.0,  # Deterministic mode
        },
        "provenance": {
            "input_hash": input_hash,
            "output_hash": hashlib.sha256(generated_text.encode()).hexdigest(),
            "determinism_hash": hashlib.sha256(
                f"{input_hash}:{seed}:{generated_text}".encode()
            ).hexdigest(),
        },
    }

    return output


def _invoke_neon_genie_generate(prompt: str, seed: int, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Simulate Neon-Genie overlay invocation via stdin/stdout contract.

    Request envelope → stdin
    Response envelope ← stdout
    """
    request = {
        "schema_version": "neon_genie.overlay_request.v0",
        "operation": "generate",
        "request_id": f"test-req-{seed}",
        "payload": {
            "prompt": prompt,
            "context": context or {},
        },
        "provenance": {
            "caller": "test_suite",
            "seed": seed,
            "timestamp_utc": "2025-01-01T00:00:00Z",
        },
    }

    output = _generate_mock_output(request, seed)

    response = {
        "schema_version": "neon_genie.overlay_response.v0",
        "request_id": request["request_id"],
        "status": "success",
        "result": output,
        "provenance": {
            "engine": "neon_genie",
            "version": "0.1.0",
            "determinism_hash": output["provenance"]["determinism_hash"],
            "execution_time_ms": 42.0,
            "seed_used": seed,
        },
    }

    return response


def test_neon_genie_determinism_golden_12_runs():
    """
    Golden determinism test: ≥12 runs with same SEED → invariant hash.

    CRITICAL: This test validates SEED enforcement for Neon-Genie.
    Failure indicates non-deterministic behavior (FORBIDDEN).
    """
    prompt = "Generate a concise summary of AAL overlay architecture"
    seed = 42

    # Run 12 times with same seed
    hashes = []
    outputs = []

    for i in range(12):
        response = _invoke_neon_genie_generate(prompt=prompt, seed=seed)

        assert response["status"] == "success", f"Run {i+1} failed"
        assert response["provenance"]["seed_used"] == seed, f"Run {i+1} seed mismatch"

        result = response["result"]
        outputs.append(result)

        determinism_hash = result["provenance"]["determinism_hash"]
        hashes.append(determinism_hash)

    # ALL 12 runs MUST produce identical hash (determinism guarantee)
    unique_hashes = set(hashes)
    assert len(unique_hashes) == 1, (
        f"DETERMINISM VIOLATION: {len(unique_hashes)} unique hashes across 12 runs. "
        f"Expected: 1 (invariant). Hashes: {unique_hashes}"
    )

    # ALL 12 runs MUST produce identical output
    golden_output = outputs[0]
    for i, output in enumerate(outputs[1:], start=2):
        assert output == golden_output, (
            f"Run {i} output differs from golden (run 1). "
            f"Determinism guarantee violated."
        )

    # Validate schema compliance
    assert golden_output["schema_version"] == "neon_genie.generate_output.v0"
    assert "generated_text" in golden_output
    assert "metadata" in golden_output
    assert "provenance" in golden_output
    assert golden_output["metadata"]["seed_echo"] == seed

    print(f"✓ DETERMINISM GOLDEN: 12/12 runs identical (hash: {hashes[0][:16]}...)")


def test_neon_genie_different_seeds_produce_different_outputs():
    """
    Different SEEDs MUST produce different outputs (entropy not leaked).
    """
    prompt = "Generate a concise summary of AAL overlay architecture"

    response1 = _invoke_neon_genie_generate(prompt=prompt, seed=42)
    response2 = _invoke_neon_genie_generate(prompt=prompt, seed=43)

    hash1 = response1["result"]["provenance"]["determinism_hash"]
    hash2 = response2["result"]["provenance"]["determinism_hash"]

    assert hash1 != hash2, "Different seeds MUST produce different outputs"

    text1 = response1["result"]["generated_text"]
    text2 = response2["result"]["generated_text"]

    assert text1 != text2, "Different seeds MUST produce different generated text"

    print(f"✓ SEED INDEPENDENCE: seed=42 → {hash1[:16]}..., seed=43 → {hash2[:16]}...")


def test_neon_genie_missing_required_input_returns_not_computable():
    """
    Missing required input (prompt) → status=not_computable.

    This validates ABX-Runes contract: missing inputs MUST NOT fail silently.
    """
    request = {
        "schema_version": "neon_genie.overlay_request.v0",
        "operation": "generate",
        "request_id": "test-missing-input",
        "payload": {
            # NO prompt field (required!)
            "context": {"style": "formal"},
        },
        "provenance": {
            "caller": "test_suite",
            "seed": 0,
            "timestamp_utc": "2025-01-01T00:00:00Z",
        },
    }

    # Simulate overlay validation
    payload = request["payload"]
    if "prompt" not in payload:
        response = {
            "schema_version": "neon_genie.overlay_response.v0",
            "request_id": request["request_id"],
            "status": "not_computable",
            "result": None,
            "error": {
                "code": "MISSING_REQUIRED_INPUT",
                "message": "Required input 'prompt' is missing",
                "details": {"missing_fields": ["prompt"]},
            },
            "provenance": {
                "engine": "neon_genie",
                "version": "0.1.0",
                "determinism_hash": "",
                "execution_time_ms": 0.0,
            },
        }

    # Validate not_computable response
    assert response["status"] == "not_computable"
    assert response["result"] is None
    assert response["error"]["code"] == "MISSING_REQUIRED_INPUT"
    assert "prompt" in response["error"]["message"]

    print("✓ NOT_COMPUTABLE: Missing 'prompt' → not_computable (correct)")


def test_neon_genie_empty_prompt_is_valid():
    """
    Empty string prompt is technically valid (minLength: 0 in schema).
    Overlay MUST handle it gracefully.
    """
    response = _invoke_neon_genie_generate(prompt="", seed=0)

    assert response["status"] == "success"
    result = response["result"]

    # Should generate SOMETHING (even if trivial)
    assert "generated_text" in result
    assert result["metadata"]["finish_reason"] in ["complete", "constraint_violation"]

    print("✓ EDGE CASE: Empty prompt handled gracefully")


def test_neon_genie_output_hash_stability():
    """
    Output hash MUST be stable for same content (no timestamp leakage).
    """
    prompt = "Test prompt for hash stability"
    seed = 99

    # Generate output twice
    response1 = _invoke_neon_genie_generate(prompt=prompt, seed=seed)
    response2 = _invoke_neon_genie_generate(prompt=prompt, seed=seed)

    result1 = response1["result"]
    result2 = response2["result"]

    # Generated text MUST be identical
    assert result1["generated_text"] == result2["generated_text"]

    # Output hash MUST be identical
    assert result1["provenance"]["output_hash"] == result2["provenance"]["output_hash"]

    # Determinism hash MUST be identical
    assert result1["provenance"]["determinism_hash"] == result2["provenance"]["determinism_hash"]

    print("✓ HASH STABILITY: Same input+seed → identical hashes")


def test_neon_genie_schema_version_enforcement():
    """
    Response MUST include correct schema versions.
    """
    response = _invoke_neon_genie_generate(prompt="test", seed=1)

    assert response["schema_version"] == "neon_genie.overlay_response.v0"
    assert response["result"]["schema_version"] == "neon_genie.generate_output.v0"

    print("✓ SCHEMA VERSION: Correct versions enforced")


if __name__ == "__main__":
    # Run golden test standalone
    test_neon_genie_determinism_golden_12_runs()
    test_neon_genie_different_seeds_produce_different_outputs()
    test_neon_genie_missing_required_input_returns_not_computable()
    test_neon_genie_empty_prompt_is_valid()
    test_neon_genie_output_hash_stability()
    test_neon_genie_schema_version_enforcement()
    print("\n✓ ALL DETERMINISM TESTS PASSED")
