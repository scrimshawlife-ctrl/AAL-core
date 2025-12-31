"""Tests for overlay registry."""

import tempfile
from pathlib import Path

from aal_overlays.manifest import OverlayManifest
from aal_overlays.registry import OverlayRegistry


def create_test_manifest(name: str = "test") -> OverlayManifest:
    """Helper to create a test manifest."""
    data = {
        "name": name,
        "version": "0.1.0",
        "description": f"Test overlay {name}",
        "entrypoints": {
            "http": {"base_url": f"http://localhost:8080/{name}"}
        },
        "capabilities": {
            "run": {
                "runner": "http",
                "path": "/run",
            }
        }
    }
    return OverlayManifest.from_dict(data)


def test_registry_install():
    """Test installing a manifest."""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry = OverlayRegistry(tmpdir)
        manifest = create_test_manifest("testoverlay")

        registry.install_manifest(manifest)

        installed = registry.list_installed()
        assert len(installed) == 1
        assert installed[0].name == "testoverlay"


def test_registry_enable_disable():
    """Test enabling and disabling overlays."""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry = OverlayRegistry(tmpdir)
        manifest = create_test_manifest("testoverlay")

        registry.install_manifest(manifest)

        # Should not be enabled initially
        assert not registry.is_enabled("testoverlay")
        assert len(registry.list_enabled()) == 0

        # Enable
        registry.enable("testoverlay")
        assert registry.is_enabled("testoverlay")
        assert "testoverlay" in registry.list_enabled()

        # Disable
        registry.disable("testoverlay")
        assert not registry.is_enabled("testoverlay")
        assert len(registry.list_enabled()) == 0


def test_registry_persistence():
    """Test that enabled state persists across registry instances."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # First registry instance
        registry1 = OverlayRegistry(tmpdir)
        manifest = create_test_manifest("testoverlay")
        registry1.install_manifest(manifest)
        registry1.enable("testoverlay")

        # Second registry instance
        registry2 = OverlayRegistry(tmpdir)
        assert registry2.is_enabled("testoverlay")


def test_registry_get_capability():
    """Test capability resolution."""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry = OverlayRegistry(tmpdir)

        # Install and enable two overlays
        manifest1 = create_test_manifest("overlay1")
        manifest2 = create_test_manifest("overlay2")

        registry.install_manifest(manifest1)
        registry.install_manifest(manifest2)
        registry.enable("overlay1")
        registry.enable("overlay2")

        # Test fully qualified capability
        manifest, cap_name = registry.get_capability("overlay1.run")
        assert manifest.name == "overlay1"
        assert cap_name == "run"

        # Test unqualified capability (should find in enabled overlays)
        manifest, cap_name = registry.get_capability("overlay1.run")
        assert manifest.name == "overlay1"


def test_registry_get_capability_not_enabled():
    """Test that disabled overlays are not resolved."""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry = OverlayRegistry(tmpdir)
        manifest = create_test_manifest("testoverlay")

        registry.install_manifest(manifest)
        # Don't enable it

        try:
            registry.get_capability("testoverlay.run")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "not enabled" in str(e).lower()


def test_registry_uninstall():
    """Test uninstalling an overlay."""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry = OverlayRegistry(tmpdir)
        manifest = create_test_manifest("testoverlay")

        registry.install_manifest(manifest)
        assert len(registry.list_installed()) == 1

        registry.uninstall("testoverlay")
        assert len(registry.list_installed()) == 0


def test_registry_uninstall_enabled_fails():
    """Test that uninstalling an enabled overlay fails."""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry = OverlayRegistry(tmpdir)
        manifest = create_test_manifest("testoverlay")

        registry.install_manifest(manifest)
        registry.enable("testoverlay")

        try:
            registry.uninstall("testoverlay")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "enabled" in str(e).lower()


def test_registry_multiple_overlays():
    """Test registry with multiple overlays."""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry = OverlayRegistry(tmpdir)

        # Install multiple overlays
        for name in ["overlay_a", "overlay_b", "overlay_c"]:
            manifest = create_test_manifest(name)
            registry.install_manifest(manifest)

        assert len(registry.list_installed()) == 3

        # Enable some
        registry.enable("overlay_a")
        registry.enable("overlay_c")

        enabled = registry.list_enabled()
        assert len(enabled) == 2
        assert "overlay_a" in enabled
        assert "overlay_c" in enabled
        assert "overlay_b" not in enabled


if __name__ == "__main__":
    test_registry_install()
    test_registry_enable_disable()
    test_registry_persistence()
    test_registry_get_capability()
    test_registry_get_capability_not_enabled()
    test_registry_uninstall()
    test_registry_uninstall_enabled_fails()
    test_registry_multiple_overlays()
    print("All registry tests passed!")
