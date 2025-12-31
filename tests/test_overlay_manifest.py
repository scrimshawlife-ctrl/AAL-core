"""Tests for overlay manifest schema and validation."""

import json
import tempfile
from pathlib import Path

from aal_overlays.manifest import (
    OverlayManifest,
    Capability,
    Entrypoints,
    HTTPEntrypoint,
    ProcEntrypoint,
)


def test_minimal_manifest():
    """Test minimal valid manifest."""
    data = {
        "name": "test",
        "version": "0.1.0",
        "description": "Test overlay",
        "entrypoints": {
            "http": {"base_url": "http://localhost:8080"}
        },
        "capabilities": {
            "test.run": {
                "runner": "http",
                "path": "/run",
            }
        }
    }

    manifest = OverlayManifest.from_dict(data)
    assert manifest.name == "test"
    assert manifest.version == "0.1.0"
    assert manifest.entrypoints.http.base_url == "http://localhost:8080"
    assert "test.run" in manifest.capabilities


def test_manifest_validation_missing_name():
    """Test that missing name fails validation."""
    data = {
        "version": "0.1.0",
        "description": "Test",
        "entrypoints": {"http": {"base_url": "http://localhost"}},
        "capabilities": {"test": {"runner": "http", "path": "/"}},
    }

    try:
        OverlayManifest.from_dict(data)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "name" in str(e).lower()


def test_manifest_validation_missing_capabilities():
    """Test that missing capabilities fails validation."""
    data = {
        "name": "test",
        "version": "0.1.0",
        "description": "Test",
        "entrypoints": {"http": {"base_url": "http://localhost"}},
        "capabilities": {},
    }

    try:
        OverlayManifest.from_dict(data)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "capability" in str(e).lower() or "capabilities" in str(e).lower()


def test_manifest_validation_runner_mismatch():
    """Test that runner mismatch fails validation."""
    data = {
        "name": "test",
        "version": "0.1.0",
        "description": "Test",
        "entrypoints": {
            "http": {"base_url": "http://localhost"}
        },
        "capabilities": {
            "test.proc": {
                "runner": "proc",  # But no proc entrypoint!
                "path": "/run",
            }
        }
    }

    try:
        OverlayManifest.from_dict(data)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "proc" in str(e).lower()


def test_full_manifest():
    """Test full manifest with all fields."""
    data = {
        "name": "psyfi",
        "version": "0.1.0",
        "description": "Psy-Fi simulation overlay",
        "entrypoints": {
            "http": {"base_url": "http://127.0.0.1:8787"},
            "proc": {"command": ["python", "-m", "psyfi_cli"]}
        },
        "capabilities": {
            "psyfi.simulate": {
                "runner": "http",
                "path": "/run",
                "method": "POST",
                "timeout_s": 60,
                "default_profile": "PERFORMANCE",
                "degradation": {
                    "max_fraction": 0.7,
                    "disable_nonessential": False,
                }
            }
        },
        "resources": {
            "prefers_gpu": True,
            "notes": "Requires CUDA"
        },
        "policy": {
            "deterministic": True
        }
    }

    manifest = OverlayManifest.from_dict(data)
    assert manifest.name == "psyfi"
    assert manifest.entrypoints.http is not None
    assert manifest.entrypoints.proc is not None
    assert manifest.resources.prefers_gpu is True
    assert manifest.policy.deterministic is True

    cap = manifest.capabilities["psyfi.simulate"]
    assert cap.timeout_s == 60
    assert cap.default_profile == "PERFORMANCE"
    assert cap.degradation.max_fraction == 0.7


def test_manifest_save_load():
    """Test manifest persistence."""
    with tempfile.TemporaryDirectory() as tmpdir:
        data = {
            "name": "testoverlay",
            "version": "1.0.0",
            "description": "Test",
            "entrypoints": {"http": {"base_url": "http://localhost"}},
            "capabilities": {
                "test": {"runner": "http", "path": "/test"}
            }
        }

        manifest = OverlayManifest.from_dict(data)
        manifest.save(tmpdir)

        loaded = OverlayManifest.load("testoverlay", tmpdir)
        assert loaded.name == manifest.name
        assert loaded.version == manifest.version


def test_manifest_to_dict_roundtrip():
    """Test to_dict/from_dict roundtrip."""
    data = {
        "name": "test",
        "version": "0.1.0",
        "description": "Test overlay",
        "entrypoints": {
            "http": {"base_url": "http://localhost:8080"}
        },
        "capabilities": {
            "test.run": {
                "runner": "http",
                "path": "/run",
                "method": "POST",
                "timeout_s": 30,
                "default_profile": "BALANCED",
                "degradation": {
                    "max_fraction": 0.5,
                    "disable_nonessential": True,
                }
            }
        },
        "resources": {
            "prefers_gpu": False,
            "notes": ""
        },
        "policy": {
            "deterministic": True
        }
    }

    manifest = OverlayManifest.from_dict(data)
    recovered = OverlayManifest.from_dict(manifest.to_dict())

    assert recovered.name == manifest.name
    assert recovered.version == manifest.version
    assert recovered.capabilities["test.run"].timeout_s == 30


if __name__ == "__main__":
    test_minimal_manifest()
    test_manifest_validation_missing_name()
    test_manifest_validation_missing_capabilities()
    test_manifest_validation_runner_mismatch()
    test_full_manifest()
    test_manifest_save_load()
    test_manifest_to_dict_roundtrip()
    print("All manifest tests passed!")
