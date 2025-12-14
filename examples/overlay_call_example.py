#!/usr/bin/env python3
"""
Example: Using the AAL Overlay Adapter Layer

Demonstrates:
1. Creating and installing an overlay manifest
2. Enabling the overlay in the registry
3. Dispatching capability calls through the memory-aware scheduler
4. Handling results and provenance tracking

For this example, we'll simulate a simple overlay without needing an actual server.
"""

import json
import sys
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from abx_runes.scheduler_memory_layer import MemoryAwareScheduler, JobContext
from aal_overlays import (
    OverlayManifest,
    OverlayRegistry,
    dispatch_capability_call,
    make_overlay_run_job,
)


def create_demo_overlay_manifest() -> OverlayManifest:
    """
    Create a demo overlay manifest for Psy-Fi simulation.

    In production, this would point to a real service.
    """
    manifest_data = {
        "name": "psyfi",
        "version": "0.1.0",
        "description": "Psy-Fi simulation and analysis overlay",
        "entrypoints": {
            # In real deployment, this would be your actual service URL
            "http": {"base_url": "http://127.0.0.1:8787"}
        },
        "capabilities": {
            "simulate": {
                "runner": "http",
                "path": "/run",
                "method": "POST",
                "timeout_s": 60,
                "default_profile": "BALANCED",
                "degradation": {
                    "max_fraction": 0.7,
                    "disable_nonessential": True,
                }
            },
            "analyze": {
                "runner": "http",
                "path": "/analyze",
                "method": "POST",
                "timeout_s": 30,
                "default_profile": "PERFORMANCE",
                "degradation": {
                    "max_fraction": 0.5,
                    "disable_nonessential": False,
                }
            }
        },
        "resources": {
            "prefers_gpu": True,
            "notes": "Psy-Fi simulation benefits from GPU acceleration"
        },
        "policy": {
            "deterministic": True
        }
    }

    return OverlayManifest.from_dict(manifest_data)


def demo_simple_run_job(job: JobContext) -> dict:
    """
    Simple demo run_job that simulates overlay execution.

    In production, this would be make_overlay_run_job(registry).
    """
    print(f"\n{'='*60}")
    print(f"JOB EXECUTION: {job.job_id}")
    print(f"{'='*60}")

    print(f"\nMemory Profile:")
    print(f"  Priority: {job.profile.priority}")
    print(f"  Soft Cap: {job.profile.mem.soft_cap_mb}MB")
    print(f"  Hard Cap: {job.profile.mem.hard_cap_mb}MB")
    print(f"  Tier: {job.profile.tier.value}")

    print(f"\nJob Metadata:")
    print(f"  Overlay: {job.metadata.get('overlay')}")
    print(f"  Capability: {job.metadata.get('capability')}")
    print(f"  Runner: {job.metadata.get('runner')}")
    print(f"  Timeout: {job.metadata.get('timeout_s')}s")

    # Check for degradation metadata applied by scheduler
    degradation_applied = []
    if "kv_shrink_factor" in job.metadata:
        degradation_applied.append(f"KV shrink: {job.metadata['kv_shrink_factor']}")
    if "max_context_tokens" in job.metadata:
        degradation_applied.append(f"Context limit: {job.metadata['max_context_tokens']}")
    if "disabled_features" in job.metadata:
        degradation_applied.append(f"Disabled: {job.metadata['disabled_features']}")

    if degradation_applied:
        print(f"\nDegradation Applied:")
        for item in degradation_applied:
            print(f"  - {item}")

    # Simulate execution
    request = job.metadata.get("request", {})
    payload = request.get("payload", {})

    print(f"\nInput Payload:")
    print(f"  {json.dumps(payload, indent=2)}")

    # Return simulated result
    return {
        "ok": True,
        "result": {
            "simulation_id": "sim_12345",
            "status": "completed",
            "data": payload,
            "message": "Demo overlay executed successfully (simulated)",
        }
    }


def main():
    """Run the overlay example."""
    print("="*60)
    print("AAL Overlay Adapter Layer - Example")
    print("="*60)

    # Use temporary directory for this demo
    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"\n1. Creating overlay registry at: {tmpdir}")
        registry = OverlayRegistry(tmpdir)

        print("\n2. Creating Psy-Fi overlay manifest")
        manifest = create_demo_overlay_manifest()
        print(f"   Name: {manifest.name}")
        print(f"   Version: {manifest.version}")
        print(f"   Capabilities: {list(manifest.capabilities.keys())}")

        print("\n3. Installing manifest to registry")
        registry.install_manifest(manifest)

        print("\n4. Enabling overlay")
        registry.enable("psyfi")

        print(f"\n5. Installed overlays: {[m.name for m in registry.list_installed()]}")
        print(f"   Enabled overlays: {registry.list_enabled()}")

        print("\n6. Creating memory-aware scheduler")
        # For demo, use our simple run_job; in production, use make_overlay_run_job(registry)
        scheduler = MemoryAwareScheduler(demo_simple_run_job)

        print("\n7. Dispatching capability call: psyfi.simulate")
        result = dispatch_capability_call(
            scheduler=scheduler,
            registry=registry,
            capability="psyfi.simulate",
            payload={
                "simulation_type": "quantum_coherence",
                "parameters": {
                    "duration": 100,
                    "resolution": 0.01,
                },
                "options": {
                    "visualize": True,
                    "export_format": "json",
                }
            },
            profile="BALANCED",  # Use BALANCED memory profile
            seed="demo-seed-123",  # Deterministic run_id
        )

        print(f"\n{'='*60}")
        print("RESULT")
        print(f"{'='*60}")
        print(f"\nSuccess: {result.get('ok')}")

        if result.get("ok"):
            print(f"\nResult:")
            print(f"  {json.dumps(result.get('result'), indent=2)}")
        else:
            print(f"\nError: {result.get('error')}")

        print(f"\nProvenance:")
        prov = result.get("provenance", {})
        print(f"  Run ID: {prov.get('run_id')}")
        print(f"  Overlay: {prov.get('overlay', {}).get('name')} v{prov.get('overlay', {}).get('version')}")
        print(f"  Capability: {prov.get('capability')}")
        print(f"  Deterministic: {prov.get('deterministic')}")
        print(f"  Timestamp: {prov.get('environment', {}).get('timestamp_utc')}")

        print(f"\n{'='*60}")
        print("Example completed successfully!")
        print(f"{'='*60}")

        print("\nNext steps:")
        print("  1. Deploy an actual overlay HTTP service")
        print("  2. Update manifest with real service URL")
        print("  3. Use make_overlay_run_job(registry) for real execution")
        print("  4. Wire pipeline code to consume job.metadata degradation params")
        print("  5. Add monitoring and metrics collection")


if __name__ == "__main__":
    main()
