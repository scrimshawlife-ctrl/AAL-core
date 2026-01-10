import json
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas" / "aalmanac" / "aalmanac.signal.v1.schema.json"
GOLDEN_PATH = ROOT / "tests" / "golden" / "aalmanac.golden.v1.json"


def test_aalmanac_schema_validates_golden_vector():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    doc = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(doc)


def test_single_token_contract_enforced():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    bad = {
        "schema_version": "aalmanac.signal.v1",
        "generated_at_utc": "2026-01-09T00:00:00Z",
        "inputs_hash": "x" * 16,
        "entries": [
            {
                "term": "two words",
                "term_type": "single",
                "tokens": ["two", "words"],  # illegal for single
                "source_class": "oracle_internal",
                "domain_tags": ["culture"],
                "sense_shift": {"from_sense": "a", "to_sense": "b", "shift_type": "compression"},
                "usage_frame": "x" * 12,
                "example_templates": ["x" * 12],
                "scores": {"STI": 0.1, "CP": 0.1, "IPS": 0.1, "RFR": 0.1, "lambdaN": 0.1},
                "half_life": "days",
                "confidence": 0.5,
                "provenance": {
                    "engine": "aal_core",
                    "ruleset_id": "aalmanac.rules.v1",
                    "input_fingerprints": ["x" * 8],
                    "run_id": "x" * 8,
                    "determinism_hash": "x" * 16,
                },
            }
        ],
        "drift_ledger": [],
        "provenance": {
            "engine": "aal_core",
            "ruleset_id": "aalmanac.rules.v1",
            "input_fingerprints": ["x" * 8],
            "run_id": "x" * 8,
            "determinism_hash": "x" * 16,
        },
    }
    v = jsonschema.Draft202012Validator(schema)
    errors = sorted(v.iter_errors(bad), key=lambda e: e.path)
    assert errors, "Expected schema to reject single-token violations"
