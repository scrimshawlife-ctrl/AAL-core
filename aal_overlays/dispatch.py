"""
Overlay dispatch layer - integration seam with MemoryAwareScheduler.

Provides dispatch_capability_call() which:
1. Resolves overlay + capability from registry
2. Builds deterministic request with provenance
3. Creates JobContext with memory profile
4. Submits to MemoryAwareScheduler
5. Executes via appropriate runner
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from abx_runes.memory_runes import parse_memory_profile, MemoryProfile
from abx_runes.scheduler_memory_layer import JobContext, MemoryAwareScheduler

from .manifest import OverlayManifest
from .provenance import create_provenance_record
from .registry import OverlayRegistry
from .runners.http_runner import HTTPOverlayRunner
from .runners.proc_runner import ProcOverlayRunner


# Default memory profiles for overlays
DEFAULT_PROFILES = {
    "MINIMAL": """
        MEM[SOFT=512,HARD=1024,VOL=LOW];
        TIER=LOCAL;
        PRIORITY=3;
    """,
    "BALANCED": """
        MEM[SOFT=2048,HARD=4096,VOL=MED];
        KV[CAP=0.2,POLICY=WINDOW,PURGE=ON_STRESS];
        TIER=EXTENDED;
        PRIORITY=5;
        DEGRADE{
          STEP1:SHRINK_KV(0.75),
          STEP2:CONTEXT(4096),
          STEP3:DISABLE(HIGH_COST_METRICS)
        }
    """,
    "PERFORMANCE": """
        MEM[SOFT=4096,HARD=8192,VOL=HIGH];
        KV[CAP=0.3,POLICY=TASK_BOUND,PURGE=ON_EVENT];
        TIER=LOCAL;
        PRIORITY=8;
        DEGRADE{
          STEP1:SHRINK_KV(0.9),
          STEP2:DISABLE(TELEMETRY)
        }
    """,
}


def get_memory_profile(profile_name: str) -> MemoryProfile:
    """
    Get memory profile by name.

    Args:
        profile_name: Profile name (MINIMAL, BALANCED, PERFORMANCE) or custom rune text

    Returns:
        Parsed MemoryProfile

    Raises:
        ValueError: If profile cannot be parsed
    """
    # Check if it's a default profile
    if profile_name in DEFAULT_PROFILES:
        rune_text = DEFAULT_PROFILES[profile_name]
    else:
        # Assume it's custom rune text
        rune_text = profile_name

    return parse_memory_profile(rune_text)


def make_overlay_run_job(registry: OverlayRegistry) -> Callable[[JobContext], Dict[str, Any]]:
    """
    Create a run_job callback that executes overlays via their configured runners.

    This function is passed to MemoryAwareScheduler and executed when a job is submitted.

    Args:
        registry: OverlayRegistry for resolving manifests

    Returns:
        Callable that takes JobContext and returns execution result
    """
    def run_job(job: JobContext) -> Dict[str, Any]:
        """
        Execute overlay job using metadata.

        Args:
            job: JobContext with overlay metadata

        Returns:
            Execution result dictionary
        """
        # Extract overlay metadata
        overlay_name = job.metadata.get("overlay")
        capability_name = job.metadata.get("capability")
        runner_type = job.metadata.get("runner")
        request_data = job.metadata.get("request", {})

        if not all([overlay_name, capability_name, runner_type]):
            return {
                "ok": False,
                "error": "Missing required metadata: overlay, capability, or runner",
            }

        # Get manifest
        try:
            manifest = registry.get_manifest(overlay_name)
        except FileNotFoundError:
            return {
                "ok": False,
                "error": f"Overlay '{overlay_name}' not found",
            }

        # Get capability config
        if capability_name not in manifest.capabilities:
            return {
                "ok": False,
                "error": f"Capability '{capability_name}' not found in overlay '{overlay_name}'",
            }

        capability = manifest.capabilities[capability_name]

        # Create appropriate runner
        if runner_type == "http":
            if not manifest.entrypoints.http:
                return {
                    "ok": False,
                    "error": f"Overlay '{overlay_name}' has no HTTP entrypoint",
                }

            runner = HTTPOverlayRunner(
                base_url=manifest.entrypoints.http.base_url,
                timeout=capability.timeout_s,
            )

        elif runner_type == "proc":
            if not manifest.entrypoints.proc:
                return {
                    "ok": False,
                    "error": f"Overlay '{overlay_name}' has no proc entrypoint",
                }

            runner = ProcOverlayRunner(
                command=manifest.entrypoints.proc.command,
                timeout=capability.timeout_s,
            )

        else:
            return {
                "ok": False,
                "error": f"Unknown runner type: {runner_type}",
            }

        # Execute via runner
        result = runner.call(
            path=capability.path,
            payload=request_data,
        )

        return result

    return run_job


def dispatch_capability_call(
    scheduler: MemoryAwareScheduler,
    registry: OverlayRegistry,
    capability: str,
    payload: Dict[str, Any],
    profile: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    seed: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Dispatch a capability call through the memory-aware scheduler.

    This is the main integration seam for overlay execution.

    Args:
        scheduler: MemoryAwareScheduler instance
        registry: OverlayRegistry for resolving capabilities
        capability: Capability identifier (e.g., "psyfi.simulate" or "simulate")
        payload: Input payload for the capability
        profile: Memory profile name or custom rune text (default: use capability default)
        metadata: Additional metadata to include in JobContext
        seed: Optional seed for deterministic run_id generation

    Returns:
        Execution result dictionary with structure:
        {
            "ok": bool,
            "result": Any,  # Present if ok=True
            "error": str,   # Present if ok=False
            "provenance": dict  # Provenance record
        }

    Raises:
        ValueError: If capability cannot be resolved
    """
    # Resolve capability to overlay + capability name
    manifest, cap_name = registry.get_capability(capability)
    capability_config = manifest.capabilities[cap_name]

    # Determine memory profile
    if profile is None:
        profile = capability_config.default_profile

    try:
        memory_profile = get_memory_profile(profile)
    except Exception as e:
        return {
            "ok": False,
            "error": f"Invalid memory profile '{profile}': {e}",
        }

    # Create provenance record
    provenance = create_provenance_record(
        overlay_name=manifest.name,
        overlay_version=manifest.version,
        capability=cap_name,
        payload=payload,
        deterministic=manifest.policy.deterministic,
        seed=seed,
    )

    # Build deterministic request envelope
    request_envelope = {
        "payload": payload,
        "provenance": provenance.to_dict(),
        "policy": {
            "deterministic": manifest.policy.deterministic,
        },
    }

    # Build job metadata
    job_metadata = {
        "overlay": manifest.name,
        "capability": cap_name,
        "runner": capability_config.runner,
        "timeout_s": capability_config.timeout_s,
        "degradation": capability_config.degradation.to_dict(),
        "request": request_envelope,
    }

    # Merge with user-provided metadata
    if metadata:
        job_metadata.update(metadata)

    # Create JobContext
    job = JobContext(
        job_id=provenance.run_id,
        profile=memory_profile,
        metadata=job_metadata,
    )

    # Submit to scheduler
    try:
        result = scheduler.submit(job)

        # Attach provenance to successful result
        if isinstance(result, dict):
            result["provenance"] = provenance.to_dict()
        else:
            result = {
                "ok": True,
                "result": result,
                "provenance": provenance.to_dict(),
            }

        return result

    except Exception as e:
        return {
            "ok": False,
            "error": f"Scheduler error: {type(e).__name__}: {e}",
            "provenance": provenance.to_dict(),
        }
