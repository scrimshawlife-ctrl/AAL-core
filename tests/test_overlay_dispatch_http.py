"""Tests for overlay dispatch with HTTP runner using a fake server."""

import json
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict

from abx_runes.scheduler_memory_layer import MemoryAwareScheduler

from aal_overlays.dispatch import dispatch_capability_call, make_overlay_run_job
from aal_overlays.manifest import OverlayManifest
from aal_overlays.registry import OverlayRegistry


class FakeOverlayHandler(BaseHTTPRequestHandler):
    """Fake HTTP overlay server that echoes requests."""

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress logging."""
        pass

    def do_POST(self) -> None:
        """Handle POST requests."""
        if self.path == "/run":
            # Read request body
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            request_data = json.loads(body)

            # Echo back the payload with a result
            response = {
                "ok": True,
                "result": {
                    "echo": request_data.get("payload", {}),
                    "message": "Fake overlay executed successfully",
                },
            }

            # Send response
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode("utf-8"))

        elif self.path == "/error":
            # Simulate an error
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            error_response = {
                "error": "Simulated error",
            }
            self.wfile.write(json.dumps(error_response).encode("utf-8"))

        else:
            self.send_response(404)
            self.end_headers()


def start_fake_server(port: int = 8787) -> HTTPServer:
    """Start a fake overlay HTTP server in a background thread."""
    server = HTTPServer(("127.0.0.1", port), FakeOverlayHandler)

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    return server


def create_test_manifest(port: int = 8787) -> OverlayManifest:
    """Create a test manifest pointing to fake server."""
    data = {
        "name": "fakeoverlay",
        "version": "0.1.0",
        "description": "Fake overlay for testing",
        "entrypoints": {
            "http": {"base_url": f"http://127.0.0.1:{port}"}
        },
        "capabilities": {
            "run": {
                "runner": "http",
                "path": "/run",
                "method": "POST",
                "timeout_s": 5,
                "default_profile": "BALANCED",
            },
            "error": {
                "runner": "http",
                "path": "/error",
                "method": "POST",
                "timeout_s": 5,
                "default_profile": "MINIMAL",
            }
        },
        "policy": {
            "deterministic": True
        }
    }
    return OverlayManifest.from_dict(data)


def test_dispatch_http_success():
    """Test successful HTTP dispatch."""
    # Start fake server
    server = start_fake_server(port=8787)

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            # Set up registry
            registry = OverlayRegistry(tmpdir)
            manifest = create_test_manifest(port=8787)
            registry.install_manifest(manifest)
            registry.enable("fakeoverlay")

            # Create scheduler
            run_job = make_overlay_run_job(registry)
            scheduler = MemoryAwareScheduler(run_job)

            # Dispatch capability call
            result = dispatch_capability_call(
                scheduler=scheduler,
                registry=registry,
                capability="fakeoverlay.run",
                payload={"test": "data", "value": 123},
                seed="test-seed",
            )

            # Verify result
            assert result["ok"] is True
            assert "result" in result
            assert result["result"]["echo"]["test"] == "data"
            assert result["result"]["echo"]["value"] == 123

            # Verify provenance
            assert "provenance" in result
            assert result["provenance"]["overlay"]["name"] == "fakeoverlay"
            assert result["provenance"]["capability"] == "run"
            assert result["provenance"]["deterministic"] is True

    finally:
        server.shutdown()


def test_dispatch_http_error():
    """Test HTTP dispatch with error response."""
    server = start_fake_server(port=8788)

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = OverlayRegistry(tmpdir)
            manifest = create_test_manifest(port=8788)
            registry.install_manifest(manifest)
            registry.enable("fakeoverlay")

            run_job = make_overlay_run_job(registry)
            scheduler = MemoryAwareScheduler(run_job)

            # Call error endpoint
            result = dispatch_capability_call(
                scheduler=scheduler,
                registry=registry,
                capability="fakeoverlay.error",
                payload={"test": "error"},
            )

            # Should get error response
            assert result["ok"] is False
            assert "error" in result

    finally:
        server.shutdown()


def test_dispatch_metadata_fields():
    """Test that dispatch sets correct metadata fields."""
    server = start_fake_server(port=8789)

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = OverlayRegistry(tmpdir)
            manifest = create_test_manifest(port=8789)
            registry.install_manifest(manifest)
            registry.enable("fakeoverlay")

            # Track job metadata
            captured_job = None

            def capture_run_job(job):
                nonlocal captured_job
                captured_job = job
                # Still execute normally
                return make_overlay_run_job(registry)(job)

            scheduler = MemoryAwareScheduler(capture_run_job)

            dispatch_capability_call(
                scheduler=scheduler,
                registry=registry,
                capability="fakeoverlay.run",
                payload={"test": "metadata"},
            )

            # Verify metadata was set
            assert captured_job is not None
            assert captured_job.metadata["overlay"] == "fakeoverlay"
            assert captured_job.metadata["capability"] == "run"
            assert captured_job.metadata["runner"] == "http"
            assert captured_job.metadata["timeout_s"] == 5
            assert "degradation" in captured_job.metadata
            assert "request" in captured_job.metadata

            # Verify request envelope structure
            request = captured_job.metadata["request"]
            assert "payload" in request
            assert "provenance" in request
            assert "policy" in request

    finally:
        server.shutdown()


def test_dispatch_custom_profile():
    """Test dispatch with custom memory profile."""
    server = start_fake_server(port=8790)

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = OverlayRegistry(tmpdir)
            manifest = create_test_manifest(port=8790)
            registry.install_manifest(manifest)
            registry.enable("fakeoverlay")

            captured_job = None

            def capture_run_job(job):
                nonlocal captured_job
                captured_job = job
                return make_overlay_run_job(registry)(job)

            scheduler = MemoryAwareScheduler(capture_run_job)

            # Use PERFORMANCE profile
            dispatch_capability_call(
                scheduler=scheduler,
                registry=registry,
                capability="fakeoverlay.run",
                payload={"test": "profile"},
                profile="PERFORMANCE",
            )

            # Verify profile was applied
            assert captured_job is not None
            assert captured_job.profile.priority == 8  # PERFORMANCE has priority 8

    finally:
        server.shutdown()


def test_dispatch_deterministic_run_id():
    """Test that run_id is deterministic with same seed."""
    server = start_fake_server(port=8791)

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = OverlayRegistry(tmpdir)
            manifest = create_test_manifest(port=8791)
            registry.install_manifest(manifest)
            registry.enable("fakeoverlay")

            run_job = make_overlay_run_job(registry)
            scheduler = MemoryAwareScheduler(run_job)

            # Call twice with same seed
            result1 = dispatch_capability_call(
                scheduler=scheduler,
                registry=registry,
                capability="fakeoverlay.run",
                payload={"test": "data"},
                seed="fixed-seed",
            )

            result2 = dispatch_capability_call(
                scheduler=scheduler,
                registry=registry,
                capability="fakeoverlay.run",
                payload={"test": "data"},
                seed="fixed-seed",
            )

            # run_id should be the same
            assert result1["provenance"]["run_id"] == result2["provenance"]["run_id"]

            # Call with different seed
            result3 = dispatch_capability_call(
                scheduler=scheduler,
                registry=registry,
                capability="fakeoverlay.run",
                payload={"test": "data"},
                seed="different-seed",
            )

            # run_id should be different
            assert result1["provenance"]["run_id"] != result3["provenance"]["run_id"]

    finally:
        server.shutdown()


if __name__ == "__main__":
    test_dispatch_http_success()
    test_dispatch_http_error()
    test_dispatch_metadata_fields()
    test_dispatch_custom_profile()
    test_dispatch_deterministic_run_id()
    print("All HTTP dispatch tests passed!")
