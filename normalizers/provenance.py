"""
Provenance tracking for normalizer configurations.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any

from .types import SportNormalizerConfig
from .hash import stable_hash_dict


@dataclass(frozen=True)
class ProvenanceRecord:
    """Audit trail for a normalizer configuration."""
    created_at_iso: str
    schema_version: str
    sport_id: str
    config_version: str
    config_hash: str


def make_provenance(cfg: SportNormalizerConfig) -> ProvenanceRecord:
    """
    Create a provenance record for a normalizer configuration.

    Args:
        cfg: SportNormalizerConfig instance

    Returns:
        ProvenanceRecord with timestamp and hashes
    """
    # Convert config to dict and hash
    config_dict = cfg.to_dict()
    config_hash = stable_hash_dict(config_dict)

    return ProvenanceRecord(
        created_at_iso=datetime.utcnow().isoformat(),
        schema_version=cfg.schema_version,
        sport_id=cfg.sport_id,
        config_version=cfg.version,
        config_hash=config_hash,
    )


def cfg_fingerprint(cfg: SportNormalizerConfig) -> Dict[str, Any]:
    """
    Generate full fingerprint including normalized dict form.

    Args:
        cfg: SportNormalizerConfig instance

    Returns:
        Dictionary with config dict, hash, and metadata
    """
    config_dict = cfg.to_dict()
    config_hash = stable_hash_dict(config_dict)

    return {
        "config": config_dict,
        "hash": config_hash,
        "sport_id": cfg.sport_id,
        "version": cfg.version,
        "schema_version": cfg.schema_version,
    }
