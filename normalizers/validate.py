"""
Validation logic for sport normalizer configurations.
"""
from .types import SportNormalizerConfig, DistributionShape, Primitive


def validate_normalizer(cfg: SportNormalizerConfig) -> None:
    """
    Validate a sport normalizer configuration.

    Checks:
    - schema_version == "1.0"
    - All scores in [0, 1]
    - distribution_shape and primitive are valid enums
    - stat_map is non-empty
    - failure_modes keys exist

    Args:
        cfg: SportNormalizerConfig to validate

    Raises:
        ValueError: If validation fails
    """
    # Schema version check
    if cfg.schema_version != "1.0":
        raise ValueError(f"Invalid schema_version: {cfg.schema_version}, expected '1.0'")

    # Opportunity validation
    if not 0.0 <= cfg.opportunity.stability_score <= 1.0:
        raise ValueError(
            f"opportunity.stability_score out of range: {cfg.opportunity.stability_score}"
        )

    # Usage validation
    if not 0.0 <= cfg.usage.concentration_score <= 1.0:
        raise ValueError(
            f"usage.concentration_score out of range: {cfg.usage.concentration_score}"
        )

    # Continuity validation
    if cfg.continuity.event_rate < 0.0:
        raise ValueError(f"continuity.event_rate must be >= 0: {cfg.continuity.event_rate}")

    if not isinstance(cfg.continuity.distribution_shape, DistributionShape):
        raise ValueError(
            f"Invalid distribution_shape: {cfg.continuity.distribution_shape}"
        )

    # Volatility validation
    if cfg.volatility.per_event_variance < 0.0:
        raise ValueError(
            f"volatility.per_event_variance must be >= 0: {cfg.volatility.per_event_variance}"
        )

    if cfg.volatility.game_level_variance < 0.0:
        raise ValueError(
            f"volatility.game_level_variance must be >= 0: {cfg.volatility.game_level_variance}"
        )

    # Failure modes validation
    if not cfg.failure_modes.bad_script_definition:
        raise ValueError("failure_modes.bad_script_definition cannot be empty")

    if not isinstance(cfg.failure_modes.bad_script_effects.suppresses, list):
        raise ValueError("failure_modes.bad_script_effects.suppresses must be a list")

    if not isinstance(cfg.failure_modes.bad_script_effects.inflates, list):
        raise ValueError("failure_modes.bad_script_effects.inflates must be a list")

    # Stat map validation
    if not cfg.stat_map:
        raise ValueError("stat_map cannot be empty")

    for stat_id, stat_spec in cfg.stat_map.items():
        if not isinstance(stat_spec.primitive, Primitive):
            raise ValueError(f"Invalid primitive for '{stat_id}': {stat_spec.primitive}")

        if not 0.0 <= stat_spec.survivability_score <= 1.0:
            raise ValueError(
                f"survivability_score for '{stat_id}' out of range: "
                f"{stat_spec.survivability_score}"
            )

    # Meta validation (optional field)
    if cfg.meta is not None and not isinstance(cfg.meta, dict):
        raise ValueError("meta must be a dictionary if provided")
