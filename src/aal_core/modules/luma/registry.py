from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping

from .contracts.enums import PatternKind
from .patterns.base import BasePattern
from .patterns.builtin.cluster_bloom import ClusterBloomPattern
from .patterns.builtin.domain_lattice import DomainLatticePattern
from .patterns.builtin.motif_domain_heatmap import MotifDomainHeatmapPattern
from .patterns.builtin.motif_graph import MotifGraphPattern
from .patterns.builtin.resonance_field import ResonanceFieldPattern
from .patterns.builtin.sankey_transfer import SankeyTransferPattern
from .patterns.builtin.temporal_braid import TemporalBraidPattern
from .patterns.builtin.transfer_chord import TransferChordPattern


@dataclass(frozen=True)
class LumaRegistry:
    patterns: Mapping[PatternKind, BasePattern]


def default_registry() -> LumaRegistry:
    patterns: Dict[PatternKind, BasePattern] = {
        PatternKind.MOTIF_GRAPH: MotifGraphPattern(),
        PatternKind.DOMAIN_LATTICE: DomainLatticePattern(),
        PatternKind.TEMPORAL_BRAID: TemporalBraidPattern(),
        PatternKind.RESONANCE_FIELD: ResonanceFieldPattern(),
        PatternKind.SANKEY_TRANSFER: SankeyTransferPattern(),
        PatternKind.CLUSTER_BLOOM: ClusterBloomPattern(),
        PatternKind.MOTIF_DOMAIN_HEATMAP: MotifDomainHeatmapPattern(),
        PatternKind.TRANSFER_CHORD: TransferChordPattern(),
    }
    return LumaRegistry(patterns=patterns)
