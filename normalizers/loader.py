"""
Loader utilities for normalizer configurations.
"""
import yaml
from pathlib import Path
from typing import Dict, Any

from .types import (
    SportNormalizerConfig,
    OpportunitySpec,
    UsageSpec,
    ContinuitySpec,
    VolatilitySpec,
    FailureModes,
    FailureEffects,
    StatSpec,
    DistributionShape,
    Primitive,
)


def _parse_distribution_shape(value: str) -> DistributionShape:
    """Parse distribution shape from string."""
    mapping = {
        "normal": DistributionShape.NORMAL,
        "skewed": DistributionShape.SKEWED,
        "spiky": DistributionShape.SPIKY,
        "binary": DistributionShape.BINARY,
    }
    if value not in mapping:
        raise ValueError(f"Invalid distribution_shape: {value}")
    return mapping[value]


def _parse_primitive(value: str) -> Primitive:
    """Parse primitive from string."""
    mapping = {
        "opportunity": Primitive.OPPORTUNITY,
        "usage": Primitive.USAGE,
        "hybrid": Primitive.HYBRID,
        "event": Primitive.EVENT,
    }
    if value not in mapping:
        raise ValueError(f"Invalid primitive: {value}")
    return mapping[value]


def _parse_yaml_to_config(data: Dict[str, Any]) -> SportNormalizerConfig:
    """Convert YAML data to SportNormalizerConfig."""
    # Parse opportunity
    opp_data = data["opportunity"]
    opportunity = OpportunitySpec(
        unit=opp_data["unit"],
        stability_score=float(opp_data["stability_score"]),
    )

    # Parse usage
    usage_data = data["usage"]
    usage = UsageSpec(
        unit=usage_data["unit"],
        concentration_score=float(usage_data["concentration_score"]),
    )

    # Parse continuity
    cont_data = data["continuity"]
    continuity = ContinuitySpec(
        event_rate=float(cont_data["event_rate"]),
        distribution_shape=_parse_distribution_shape(cont_data["distribution_shape"]),
    )

    # Parse volatility
    vol_data = data["volatility"]
    volatility = VolatilitySpec(
        per_event_variance=float(vol_data["per_event_variance"]),
        game_level_variance=float(vol_data["game_level_variance"]),
    )

    # Parse failure modes
    fm_data = data["failure_modes"]
    effects_data = fm_data["bad_script_effects"]
    failure_modes = FailureModes(
        bad_script_definition=fm_data["bad_script_definition"],
        bad_script_effects=FailureEffects(
            suppresses=list(effects_data["suppresses"]),
            inflates=list(effects_data["inflates"]),
        ),
    )

    # Parse stat map
    stat_map = {}
    for stat_id, stat_data in data["stat_map"].items():
        stat_map[stat_id] = StatSpec(
            primitive=_parse_primitive(stat_data["primitive"]),
            survivability_score=float(stat_data["survivability_score"]),
        )

    # Parse optional meta
    meta = data.get("meta")

    return SportNormalizerConfig(
        schema_version=data["schema_version"],
        sport_id=data["sport_id"],
        version=data["version"],
        opportunity=opportunity,
        usage=usage,
        continuity=continuity,
        volatility=volatility,
        failure_modes=failure_modes,
        stat_map=stat_map,
        meta=meta,
    )


def load_normalizer(path: str) -> SportNormalizerConfig:
    """
    Load a normalizer configuration from a YAML file.

    Args:
        path: Path to YAML file

    Returns:
        SportNormalizerConfig instance

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If YAML is invalid or doesn't match schema
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Normalizer file not found: {path}")

    with open(file_path, "r") as f:
        data = yaml.safe_load(f)

    return _parse_yaml_to_config(data)


def load_preset(sport_id: str) -> SportNormalizerConfig:
    """
    Load a preset normalizer configuration.

    Args:
        sport_id: Sport identifier (e.g., "NBA", "NHL", "NFL")

    Returns:
        SportNormalizerConfig instance

    Raises:
        FileNotFoundError: If preset doesn't exist
    """
    # Get path to presets directory
    normalizers_dir = Path(__file__).parent
    presets_dir = normalizers_dir / "presets"
    preset_file = presets_dir / f"{sport_id.lower()}.yaml"

    if not preset_file.exists():
        raise FileNotFoundError(f"Preset not found for sport: {sport_id}")

    return load_normalizer(str(preset_file))
