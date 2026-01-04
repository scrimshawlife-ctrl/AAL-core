"""
AAL-GIMLET Coupling Tests
Test YAML-driven coupling map generation and 12-run invariance.
"""

import pytest
import yaml
from pathlib import Path

from aal_core.adapters.gimlet import (
    inspect,
    generate_coupling_map,
    load_rune_catalog,
    get_rune_capabilities,
)
from aal_core.adapters.gimlet.scan import normalize_input
from aal_core.adapters.gimlet.identity import classify_identity
from aal_core.adapters.gimlet.contracts import InspectMode


@pytest.fixture
def sample_external_codebase(tmp_path):
    """External codebase for coupling tests"""
    (tmp_path / "main.py").write_text("def main():\n    pass\n")
    (tmp_path / "utils.py").write_text("def helper():\n    pass\n")
    return str(tmp_path)


@pytest.fixture
def sample_aal_overlay(tmp_path):
    """AAL overlay for coupling tests"""
    overlay_dir = tmp_path / ".aal" / "overlays" / "test_overlay"
    overlay_dir.mkdir(parents=True)

    manifest = {
        "name": "test_overlay",
        "version": "1.0",
        "status": "active"
    }
    (overlay_dir / "manifest.json").write_text(
        __import__("json").dumps(manifest)
    )

    return str(tmp_path)


def test_coupling_map_generation_external(sample_external_codebase):
    """Coupling map is generated for external codebases"""
    result = inspect(sample_external_codebase, run_seed="coupling-test", generate_coupling=True)

    assert "coupling_map" in result
    coupling_map = result["coupling_map"]

    # Validate schema
    assert coupling_map["schema"] == "coupling_map.v0"
    assert "provenance" in coupling_map
    assert "policies" in coupling_map
    assert "systems" in coupling_map


def test_coupling_map_generation_overlay(sample_aal_overlay):
    """Coupling map is generated for AAL overlays"""
    result = inspect(sample_aal_overlay, run_seed="coupling-test", generate_coupling=True)

    assert "coupling_map" in result
    coupling_map = result["coupling_map"]

    # Should classify as AAL_OVERLAY
    assert coupling_map["systems"][0]["kind"] == "AAL_OVERLAY"


def test_coupling_map_optional(sample_external_codebase):
    """Coupling map generation can be disabled"""
    result = inspect(sample_external_codebase, run_seed="test", generate_coupling=False)

    assert "coupling_map" not in result
    assert "result" in result
    assert "abx_runes" in result


def test_coupling_map_has_provenance(sample_external_codebase):
    """Coupling map includes deterministic provenance"""
    result = inspect(sample_external_codebase, run_seed="prov-test", generate_coupling=True)

    provenance = result["coupling_map"]["provenance"]

    assert "artifact_hash" in provenance
    assert "generated_by" in provenance
    assert provenance["generated_by"] == "aal-gimlet"
    assert "seed" in provenance
    assert provenance["seed"] == "prov-test"


def test_coupling_map_has_policies(sample_external_codebase):
    """Coupling map includes canonical policies"""
    result = inspect(sample_external_codebase, run_seed="policy-test", generate_coupling=True)

    policies = result["coupling_map"]["policies"]

    assert policies["coupling"] == "abx-runes-only"
    assert policies["determinism"] == "seeded"
    assert policies["sandbox"] == "capability"
    assert policies["scheduler"] == "ers"


def test_coupling_map_has_capabilities(sample_external_codebase):
    """Coupling map includes rune capabilities"""
    result = inspect(sample_external_codebase, run_seed="cap-test", generate_coupling=True)

    systems = result["coupling_map"]["systems"]
    assert len(systems) > 0

    system = systems[0]
    assert "capabilities" in system
    assert len(system["capabilities"]) > 0

    # Should have at least gimlet.v0.inspect capability
    cap_runes = [cap["rune"] for cap in system["capabilities"]]
    assert "gimlet.v0.inspect" in cap_runes


def test_dozen_run_coupling_map_invariance(sample_external_codebase):
    """
    GOLDEN TEST: 12-run invariance for coupling map generation.

    Requirement: 12 consecutive runs with same seed produce identical coupling maps.
    This is the canonical stability test for YAML-driven coupling generation.
    """
    seed = "coupling-golden-seed"
    num_runs = 12

    results = []
    for run_num in range(num_runs):
        result = inspect(sample_external_codebase, run_seed=seed, generate_coupling=True)
        results.append(result)

    # Extract coupling maps
    coupling_maps = [r["coupling_map"] for r in results]

    # Convert to YAML strings for comparison (deterministic serialization)
    coupling_yamls = [
        yaml.dump(cm, sort_keys=True, default_flow_style=False)
        for cm in coupling_maps
    ]

    # ALL YAML strings must be identical
    unique_yamls = set(coupling_yamls)
    assert len(unique_yamls) == 1, \
        f"Dozen-run coupling map invariance failed: got {len(unique_yamls)} unique outputs instead of 1"

    # Verify specific fields are identical across all runs
    for i in range(1, num_runs):
        # Provenance (except run_id which may vary)
        assert coupling_maps[0]["provenance"]["artifact_hash"] == \
               coupling_maps[i]["provenance"]["artifact_hash"], \
            f"Run {i}: artifact_hash differs"

        assert coupling_maps[0]["provenance"]["seed"] == \
               coupling_maps[i]["provenance"]["seed"], \
            f"Run {i}: seed differs"

        # Policies
        assert coupling_maps[0]["policies"] == coupling_maps[i]["policies"], \
            f"Run {i}: policies differ"

        # Systems
        assert len(coupling_maps[0]["systems"]) == len(coupling_maps[i]["systems"]), \
            f"Run {i}: system count differs"

        # System details
        sys0 = coupling_maps[0]["systems"][0]
        sysi = coupling_maps[i]["systems"][0]

        assert sys0["kind"] == sysi["kind"], f"Run {i}: system kind differs"
        assert sys0["system_id"] == sysi["system_id"], f"Run {i}: system_id differs"

        # Capabilities
        assert len(sys0["capabilities"]) == len(sysi["capabilities"]), \
            f"Run {i}: capabilities count differs"


def test_load_rune_catalog():
    """Rune catalog can be loaded"""
    catalog = load_rune_catalog()

    assert "schema" in catalog
    assert catalog["schema"] == "rune_catalog.v0"
    assert "runes" in catalog
    assert len(catalog["runes"]) > 0


def test_get_rune_capabilities():
    """Rune capabilities can be retrieved"""
    caps = get_rune_capabilities("gimlet.v0.inspect")

    assert len(caps) > 0
    assert "ingress.inspect" in caps
    assert "ingress.classify" in caps


def test_coupling_map_to_yaml(sample_external_codebase):
    """Coupling map can be serialized to YAML"""
    result = inspect(sample_external_codebase, run_seed="yaml-test", generate_coupling=True)

    coupling_map = result["coupling_map"]

    # Convert to YAML string
    yaml_str = yaml.dump(coupling_map, sort_keys=False, default_flow_style=False)

    # Should be valid YAML
    parsed = yaml.safe_load(yaml_str)
    assert parsed["schema"] == "coupling_map.v0"


def test_coupling_map_systems_have_entrypoints(sample_external_codebase):
    """Coupling map systems include detected entrypoints"""
    result = inspect(sample_external_codebase, run_seed="entrypoint-test", generate_coupling=True)

    systems = result["coupling_map"]["systems"]
    assert len(systems) > 0

    system = systems[0]
    assert "entrypoints" in system
    assert len(system["entrypoints"]) > 0


def test_coupling_map_notes_include_identity(sample_external_codebase):
    """Coupling map notes include identity classification"""
    result = inspect(sample_external_codebase, run_seed="notes-test", generate_coupling=True)

    notes = result["coupling_map"]["notes"]

    assert len(notes) > 0
    # Should mention identity
    notes_text = " ".join(notes)
    assert "Identity:" in notes_text or "identity" in notes_text.lower()


def test_coupling_map_deterministic_across_modes(sample_external_codebase):
    """Coupling map is deterministic across different inspect modes"""
    seed = "mode-determinism"

    result_inspect = inspect(sample_external_codebase, mode="inspect", run_seed=seed, generate_coupling=True)
    result_optimize = inspect(sample_external_codebase, mode="optimize", run_seed=seed, generate_coupling=True)

    # Core coupling should be identical (mode affects other parts, not coupling)
    cm_inspect = result_inspect["coupling_map"]
    cm_optimize = result_optimize["coupling_map"]

    # Same identity classification
    assert cm_inspect["systems"][0]["kind"] == cm_optimize["systems"][0]["kind"]

    # Same capabilities
    assert len(cm_inspect["systems"][0]["capabilities"]) == \
           len(cm_optimize["systems"][0]["capabilities"])


def test_default_rules_yaml_exists():
    """default_rules.v0.yaml exists and is valid"""
    rules_path = Path(__file__).parent.parent / "default_rules.v0.yaml"

    assert rules_path.exists(), "default_rules.v0.yaml must exist"

    with open(rules_path, "r") as f:
        rules_doc = yaml.safe_load(f)

    assert rules_doc["schema"] == "gimlet_rules.v0"
    assert "rules" in rules_doc
    assert len(rules_doc["rules"]) > 0


def test_catalog_yaml_exists():
    """catalog.v0.yaml exists and is valid"""
    catalog_path = Path(__file__).parent.parent.parent.parent / "runes" / "catalog.v0.yaml"

    assert catalog_path.exists(), "catalog.v0.yaml must exist"

    with open(catalog_path, "r") as f:
        catalog = yaml.safe_load(f)

    assert catalog["schema"] == "rune_catalog.v0"
    assert "runes" in catalog
    assert len(catalog["runes"]) > 0

    # Verify gimlet.v0.inspect is in catalog
    rune_ids = [r["rune_id"] for r in catalog["runes"]]
    assert "gimlet.v0.inspect" in rune_ids


def test_coupling_template_yaml_exists():
    """coupling_map.v0.yaml template exists"""
    template_path = Path(__file__).parent.parent.parent.parent.parent / ".aal" / "coupling_map.v0.yaml"

    assert template_path.exists(), "coupling_map.v0.yaml template must exist"

    with open(template_path, "r") as f:
        template = yaml.safe_load(f)

    assert template["schema"] == "coupling_map.v0"
    assert "provenance" in template
    assert "policies" in template
    assert "systems" in template
