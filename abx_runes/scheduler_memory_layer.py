# abx_runes/scheduler_memory_layer.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from .memory_runes import (
    MemoryProfile,
    DegradeStep,
)
from .ram_stress import RamStressMonitor


@dataclass
class JobContext:
    """
    Minimal representation of a runnable unit in ABX-Runes.
    Extend this to match your actual job abstraction.
    """
    job_id: str
    profile: MemoryProfile
    metadata: Dict[str, Any]


class MemoryPolicyError(RuntimeError):
    pass


class MemoryAwareScheduler:
    """
    Wraps an existing 'run_job' callable with ABX memory enforcement.

    Usage:

        base_scheduler = ...
        mem_scheduler = MemoryAwareScheduler(base_scheduler.run_job)

        mem_scheduler.submit(job_ctx)

    """

    def __init__(
        self,
        run_job: Callable[[JobContext], Any],
        ram_monitor: Optional[RamStressMonitor] = None,
        stress_hard_cutoff: float = 0.98,
    ) -> None:
        self._run_job = run_job
        self._monitor = ram_monitor or RamStressMonitor()
        self._stress_hard_cutoff = stress_hard_cutoff

    def submit(self, job: JobContext) -> Any:
        """
        Entry point: enforce memory rules, apply degradation, then delegate to underlying scheduler.
        """
        stress = self._monitor.sample()
        classification = self._monitor.classify()

        # Hard kill condition: if global stress is insane and job is low priority, reject / requeue.
        if stress >= self._stress_hard_cutoff and job.profile.priority <= 3:
            raise MemoryPolicyError(
                f"RAM_STRESS={stress:.2f} ({classification}) too high for low-priority job {job.job_id}"
            )

        adjusted_metadata = self._apply_degrade_path(job, stress)
        job.metadata.update(adjusted_metadata)

        # Here you could also enforce hard_cap_mb using a cgroup / container limit externally.
        # This layer focuses on symbolic + KV/context constraints.

        return self._run_job(job)

    def _apply_degrade_path(self, job: JobContext, stress: float) -> Dict[str, Any]:
        """
        Given RAM_STRESS and a job's MemoryProfile, apply degradation actions in order,
        mutating the effective runtime parameters (exposed via job.metadata).
        """
        profile = job.profile
        result: Dict[str, Any] = {}

        if not profile.degrade:
            return result

        # Compute an "activation level" for degradation based on stress and priority.
        # Higher priority -> later degradation.
        # Simple heuristic: threshold = 0.3 + 0.05 * priority
        base_threshold = 0.3 + 0.05 * profile.priority
        if stress < base_threshold:
            return result

        for step in profile.degrade.sorted_steps():
            self._apply_single_step(step, result, stress)

        return result

    def _apply_single_step(self, step: DegradeStep, params: Dict[str, Any], stress: float) -> None:
        """
        Map degrade actions onto concrete runtime parameters.

        This layer does *not* perform the actual KV/context changes;
        it sets flags and values that your LLM / pipeline code consumes.

        Supported actions:
          - SHRINK_KV(fraction)
          - CONTEXT(tokens)
          - DISABLE(flag_name)
          - BATCH(mode)
          - OFFLOAD(tier)
        """
        action = step.action.upper()

        if action == "SHRINK_KV":
            if not step.args:
                return
            factor = float(step.args[0])
            # Compose multiplicatively if already set
            existing = params.get("kv_shrink_factor", 1.0)
            params["kv_shrink_factor"] = existing * factor

        elif action == "CONTEXT":
            if not step.args:
                return
            max_tokens = int(step.args[0])
            current = params.get("max_context_tokens")
            params["max_context_tokens"] = min(current, max_tokens) if current else max_tokens

        elif action == "DISABLE":
            if not step.args:
                return
            flag = step.args[0]
            disabled = params.setdefault("disabled_features", set())
            disabled.add(flag)

        elif action == "BATCH":
            if not step.args:
                return
            mode = step.args[0]
            params["batch_mode"] = mode

        elif action == "OFFLOAD":
            if not step.args:
                return
            tier = step.args[0]
            params["offload_tier"] = tier

        # You can extend this mapping with project-specific actions as needed.
