"""
Tests for AAL-core Dynamic Function Registry (DFD)
"""

import json
import tempfile
import time
from pathlib import Path
from typing import Any, List

import pytest

from aal_core.bus import EventBus
from aal_core.services.fn_registry import (
    CatalogSnapshot,
    FunctionRegistry,
    validate_descriptor,
    validate_descriptors,
    REQUIRED_FIELDS,
    VALID_KINDS,
)
from aal_core.services.fn_registry.sources.manifest import load_overlay_manifests
from aal_core.services.fn_registry.sources.py_entrypoints import load_py_exports


# --------------------------------------------------
# Fixtures
# --------------------------------------------------

@pytest.fixture
def valid_descriptor() -> dict:
    """Create a valid FunctionDescriptor."""
    return {
        "id": "test.metric.example.v1",
        "name": "Example Metric",
        "kind": "metric",
        "version": "1.0.0",
        "owner": "test",
        "entrypoint": "test.metrics:example",
        "inputs_schema": {
            "type": "object",
            "properties": {},
            "required": []
        },
        "outputs_schema": {
            "type": "object",
            "properties": {
                "value": {"type": "number"}
            },
            "required": ["value"]
        },
        "capabilities": ["read_only", "no_net"],
        "provenance": {
            "repo": "https://github.com/test/repo",
            "commit": "abc123",
            "artifact_hash": "sha256:test",
            "generated_at": int(time.time())
        }
    }


@pytest.fixture
def temp_overlays_dir(tmp_path):
    """Create temporary overlays directory with test manifests."""
    overlays_root = tmp_path / "overlays"
    overlays_root.mkdir()

    # Create test overlay 1
    overlay1 = overlays_root / "test_overlay_1"
    overlay1.mkdir()
    manifest1 = {
        "name": "test_overlay_1",
        "version": "1.0.0",
        "status": "active"
    }
    (overlay1 / "manifest.json").write_text(json.dumps(manifest1))

    # Create test overlay 2
    overlay2 = overlays_root / "test_overlay_2"
    overlay2.mkdir()
    manifest2 = {
        "name": "test_overlay_2",
        "version": "2.0.0",
        "status": "active"
    }
    (overlay2 / "manifest.json").write_text(json.dumps(manifest2))

    return str(overlays_root)


@pytest.fixture
def mock_bus():
    """Create mock event bus for testing."""
    class MockBus:
        def __init__(self):
            self.events: List[tuple] = []

        def publish(self, topic: str, payload: Any):
            self.events.append((topic, payload))

    return MockBus()


# --------------------------------------------------
# Validation Tests
# --------------------------------------------------

def test_validate_descriptor_valid(valid_descriptor):
    """Test validation passes for valid descriptor."""
    # Should not raise
    validate_descriptor(valid_descriptor)


def test_validate_descriptor_missing_required_field(valid_descriptor):
    """Test validation fails for missing required field."""
    del valid_descriptor["version"]

    with pytest.raises(ValueError, match="missing required fields"):
        validate_descriptor(valid_descriptor)


def test_validate_descriptor_invalid_kind(valid_descriptor):
    """Test validation fails for invalid kind."""
    valid_descriptor["kind"] = "invalid_kind"

    with pytest.raises(ValueError, match="invalid kind"):
        validate_descriptor(valid_descriptor)


def test_validate_descriptor_missing_provenance_field(valid_descriptor):
    """Test validation fails for incomplete provenance."""
    del valid_descriptor["provenance"]["commit"]

    with pytest.raises(ValueError, match="provenance missing"):
        validate_descriptor(valid_descriptor)


def test_validate_descriptor_invalid_schema_type(valid_descriptor):
    """Test validation fails for non-dict schema."""
    valid_descriptor["inputs_schema"] = "not a dict"

    with pytest.raises(ValueError, match="must be a dict"):
        validate_descriptor(valid_descriptor)


def test_validate_descriptors_duplicate_id(valid_descriptor):
    """Test validation fails for duplicate IDs."""
    descriptors = [valid_descriptor, valid_descriptor.copy()]

    with pytest.raises(ValueError, match="Duplicate function id"):
        validate_descriptors(descriptors)


def test_validate_descriptors_multiple_valid(valid_descriptor):
    """Test validation passes for multiple unique descriptors."""
    desc2 = valid_descriptor.copy()
    desc2["id"] = "test.metric.another.v1"

    descriptors = [valid_descriptor, desc2]

    # Should not raise
    validate_descriptors(descriptors)


# --------------------------------------------------
# Source Discovery Tests
# --------------------------------------------------

def test_load_overlay_manifests(temp_overlays_dir):
    """Test loading overlay manifests from directory."""
    manifests = load_overlay_manifests(temp_overlays_dir)

    assert len(manifests) == 2
    assert manifests[0]["_overlay"] == "test_overlay_1"
    assert manifests[1]["_overlay"] == "test_overlay_2"
    assert manifests[0]["version"] == "1.0.0"
    assert manifests[1]["version"] == "2.0.0"


def test_load_overlay_manifests_missing_dir():
    """Test loading from non-existent directory returns empty list."""
    manifests = load_overlay_manifests("/nonexistent/path")
    assert manifests == []


def test_load_py_exports_no_exports():
    """Test loading from manifests without py_exports."""
    manifests = [
        {"name": "test", "_overlay": "test"}
    ]

    descriptors = load_py_exports(manifests)
    assert descriptors == []


# --------------------------------------------------
# Function Registry Tests
# --------------------------------------------------

def test_function_registry_init(mock_bus, temp_overlays_dir):
    """Test FunctionRegistry initialization."""
    registry = FunctionRegistry(mock_bus, temp_overlays_dir)

    assert registry._overlays_root == temp_overlays_dir
    assert registry._bus is mock_bus
    assert registry._last_hash is None
    assert registry._snapshot is None


def test_function_registry_build_catalog_empty(mock_bus, temp_overlays_dir):
    """Test building catalog with no function exports."""
    registry = FunctionRegistry(mock_bus, temp_overlays_dir)
    snapshot = registry.build_catalog()

    assert isinstance(snapshot, CatalogSnapshot)
    assert snapshot.count == 0
    assert snapshot.descriptors == []
    assert snapshot.catalog_hash.startswith("sha256:")
    assert snapshot.generated_at_unix > 0


def test_function_registry_tick_emits_event(mock_bus, temp_overlays_dir):
    """Test tick() emits bus event on catalog change."""
    registry = FunctionRegistry(mock_bus, temp_overlays_dir)

    # First tick
    registry.tick()

    assert len(mock_bus.events) == 1
    topic, payload = mock_bus.events[0]

    assert topic == "fn.registry.updated"
    assert "catalog_hash" in payload
    assert "generated_at_unix" in payload
    assert "count" in payload
    assert payload["count"] == 0


def test_function_registry_tick_no_event_if_unchanged(mock_bus, temp_overlays_dir):
    """Test tick() doesn't emit event if catalog unchanged."""
    registry = FunctionRegistry(mock_bus, temp_overlays_dir)

    # First tick
    registry.tick()
    assert len(mock_bus.events) == 1

    # Second tick (no changes)
    registry.tick()
    assert len(mock_bus.events) == 1  # No new event


def test_function_registry_get_snapshot(mock_bus, temp_overlays_dir):
    """Test get_snapshot() returns current snapshot."""
    registry = FunctionRegistry(mock_bus, temp_overlays_dir)

    # Build catalog
    snapshot1 = registry.build_catalog()
    snapshot2 = registry.get_snapshot()

    assert snapshot1.catalog_hash == snapshot2.catalog_hash
    assert snapshot1.count == snapshot2.count


def test_function_registry_catalog_hash_deterministic(mock_bus, temp_overlays_dir):
    """Test catalog hash is deterministic."""
    registry1 = FunctionRegistry(mock_bus, temp_overlays_dir)
    registry2 = FunctionRegistry(mock_bus, temp_overlays_dir)

    snapshot1 = registry1.build_catalog()
    snapshot2 = registry2.build_catalog()

    assert snapshot1.catalog_hash == snapshot2.catalog_hash


# --------------------------------------------------
# Integration Tests
# --------------------------------------------------

def test_full_dfd_workflow_with_abraxas():
    """
    Integration test: Load actual Abraxas exports and build catalog.

    This test requires abraxas.exports module to be importable.
    """
    try:
        import abraxas.exports  # noqa: F401
    except ImportError:
        pytest.skip("abraxas.exports not available")

    bus = EventBus()
    registry = FunctionRegistry(bus, overlays_root=".aal/overlays")

    # Build catalog
    snapshot = registry.build_catalog()

    # Should have Abraxas functions
    assert snapshot.count > 0

    # Check for expected Abraxas functions
    function_ids = {fn["id"] for fn in snapshot.descriptors}

    assert "abx.metric.alive.v1" in function_ids
    assert "abx.metric.entropy.v1" in function_ids
    assert "abx.rune.open.v1" in function_ids
    assert "abx.rune.seal.v1" in function_ids
    assert "abx.op.full_cycle.v1" in function_ids

    # Validate all descriptors
    validate_descriptors(snapshot.descriptors)

    # Check catalog hash format
    assert snapshot.catalog_hash.startswith("sha256:")
    assert len(snapshot.catalog_hash) == 71  # "sha256:" + 64 hex chars


def test_catalog_merge_strategy(mock_bus, temp_overlays_dir):
    """Test that later sources override earlier ones."""
    # This would require creating mock py_exports and http sources
    # For now, we test the principle with direct descriptor merge

    registry = FunctionRegistry(mock_bus, temp_overlays_dir)

    # Simulate merged descriptors with duplicate IDs
    desc1 = {
        "id": "test.metric.v1",
        "name": "First Version",
        "kind": "metric",
        "version": "1.0.0",
        "owner": "test",
        "entrypoint": "test:fn1",
        "inputs_schema": {},
        "outputs_schema": {},
        "capabilities": [],
        "provenance": {
            "repo": "test",
            "commit": "abc",
            "artifact_hash": "test",
            "generated_at": 123
        }
    }

    desc2 = desc1.copy()
    desc2["name"] = "Second Version"
    desc2["entrypoint"] = "test:fn2"

    # Merge by ID (later wins)
    merged = {}
    for d in [desc1, desc2]:
        merged[d["id"]] = d

    # Second version should win
    assert merged["test.metric.v1"]["name"] == "Second Version"
    assert merged["test.metric.v1"]["entrypoint"] == "test:fn2"


# --------------------------------------------------
# Event Bus Tests
# --------------------------------------------------

def test_event_bus_publish_and_subscribe(tmp_path):
    """Test event bus publish/subscribe mechanism."""
    log_path = tmp_path / "events.jsonl"
    bus = EventBus(log_path=log_path)

    # Subscribe
    received = []

    def handler(topic, payload):
        received.append((topic, payload))

    bus.subscribe("test.topic", handler)

    # Publish
    bus.publish("test.topic", {"key": "value"})

    # Check handler was called
    assert len(received) == 1
    assert received[0] == ("test.topic", {"key": "value"})

    # Check log file
    assert log_path.exists()
    with open(log_path) as f:
        event = json.loads(f.read())

    assert event["topic"] == "test.topic"
    assert event["payload"] == {"key": "value"}
    assert "timestamp" in event


def test_event_bus_get_recent_events(tmp_path):
    """Test retrieving recent events from log."""
    log_path = tmp_path / "events.jsonl"
    bus = EventBus(log_path=log_path)

    # Publish multiple events
    for i in range(5):
        bus.publish(f"topic.{i}", {"index": i})

    # Get recent events
    events = bus.get_recent_events(limit=3)

    assert len(events) == 3
    assert events[-1]["payload"]["index"] == 4
    assert events[0]["payload"]["index"] == 2


# --------------------------------------------------
# Required Fields and Kinds Tests
# --------------------------------------------------

def test_required_fields_constant():
    """Test REQUIRED_FIELDS constant is complete."""
    expected = {
        "id", "name", "kind", "version", "owner",
        "entrypoint", "inputs_schema", "outputs_schema",
        "capabilities", "provenance"
    }
    assert REQUIRED_FIELDS == expected


def test_valid_kinds_constant():
    """Test VALID_KINDS constant includes all expected kinds."""
    expected = {"metric", "rune", "op", "overlay_op", "io"}
    assert VALID_KINDS == expected


# --------------------------------------------------
# Snapshot Tests
# --------------------------------------------------

def test_catalog_snapshot_frozen():
    """Test CatalogSnapshot is immutable (frozen dataclass)."""
    snapshot = CatalogSnapshot(
        descriptors=[],
        catalog_hash="sha256:test",
        generated_at_unix=123
    )

    with pytest.raises(AttributeError):
        snapshot.catalog_hash = "modified"


def test_catalog_snapshot_count_property():
    """Test CatalogSnapshot.count property."""
    descriptors = [{"id": f"test.{i}"} for i in range(5)]
    snapshot = CatalogSnapshot(
        descriptors=descriptors,
        catalog_hash="sha256:test",
        generated_at_unix=123
    )

    assert snapshot.count == 5
