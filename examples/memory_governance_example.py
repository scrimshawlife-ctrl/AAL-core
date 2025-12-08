#!/usr/bin/env python3
"""
Example usage of ABX-Runes memory governance layer.

This demonstrates how to:
1. Parse memory rune annotations
2. Create a memory-aware scheduler
3. Submit jobs with memory constraints
4. Handle degradation under RAM stress
"""

from abx_runes.memory_runes import parse_memory_profile
from abx_runes.scheduler_memory_layer import JobContext, MemoryAwareScheduler


# Example runic annotation for an LLM pipeline
RUNE_TEXT = """
MEM[SOFT=2048,HARD=4096,VOL=MED];
KV[CAP=0.2,POLICY=WINDOW,PURGE=ON_STRESS];
TIER=EXTENDED;
PRIORITY=7;
DEGRADE{
  STEP1:SHRINK_KV(0.75),
  STEP2:CONTEXT(4096),
  STEP3:DISABLE(HIGH_COST_METRICS),
  STEP4:BATCH(ASYNC),
  STEP5:OFFLOAD(EXTENDED)
}
"""


def run_job(job: JobContext):
    """
    Your existing ABX-Runes job execution logic.
    This would normally interface with your LLM/pipeline.
    """
    print(f"Running job: {job.job_id}")
    print(f"  Priority: {job.profile.priority}")
    print(f"  Memory caps: SOFT={job.profile.mem.soft_cap_mb}MB, HARD={job.profile.mem.hard_cap_mb}MB")
    print(f"  Tier: {job.profile.tier.value}")

    # Check for degradation metadata
    if "kv_shrink_factor" in job.metadata:
        print(f"  KV cache shrunk by factor: {job.metadata['kv_shrink_factor']}")
    if "max_context_tokens" in job.metadata:
        print(f"  Context limited to: {job.metadata['max_context_tokens']} tokens")
    if "disabled_features" in job.metadata:
        print(f"  Disabled features: {job.metadata['disabled_features']}")
    if "batch_mode" in job.metadata:
        print(f"  Batch mode: {job.metadata['batch_mode']}")
    if "offload_tier" in job.metadata:
        print(f"  Offload tier: {job.metadata['offload_tier']}")

    return {"status": "completed"}


def main():
    # Parse the memory profile from rune annotation
    profile = parse_memory_profile(RUNE_TEXT)

    # Create memory-aware scheduler wrapping your existing scheduler
    mem_scheduler = MemoryAwareScheduler(run_job)

    # Create and submit a job
    job = JobContext(
        job_id="oracle-001",
        profile=profile,
        metadata={}
    )

    print("=" * 60)
    print("Submitting job with memory governance")
    print("=" * 60)

    try:
        result = mem_scheduler.submit(job)
        print(f"\nJob completed: {result}")
    except Exception as e:
        print(f"\nJob failed: {e}")

    print("\n" + "=" * 60)
    print("Memory governance layer is active!")
    print("=" * 60)


if __name__ == "__main__":
    main()
