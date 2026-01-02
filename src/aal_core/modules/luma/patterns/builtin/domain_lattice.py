from __future__ import annotations

from typing import Any, Mapping, Tuple

from ...contracts.enums import NotComputable, PatternKind
from ...contracts.scene_ir import AnimationPlan, SceneEntity
from ..base import BasePattern, PatternBuildResult

NC = NotComputable.VALUE.value


class DomainLatticePattern(BasePattern):
    """
    Grid / layered domain-subdomain map.
    """

    kind = PatternKind.DOMAIN_LATTICE

    def input_contract(self) -> Mapping[str, Any]:
        return {"domains": "list[str] or list[{domain,subdomains?}]"}

    def failure_modes(self) -> Tuple[str, ...]:
        return ("not_computable", "no_domains")

    def affordances(self) -> Tuple[str, ...]:
        return ("lattice", "layered_domains")

    def build(self, *, frame_payload: Mapping[str, Any], seed: int) -> PatternBuildResult:
        domains_in = frame_payload.get("domains")
        if not isinstance(domains_in, list) or not domains_in:
            inst = self._instance(
                pattern_id="domain_lattice/v1",
                inputs={"domains": domains_in},
                failure_mode="no_domains",
            )
            return PatternBuildResult(
                instance=inst,
                entities=tuple(),
                edges=tuple(),
                fields=tuple(),
                time_axis=NC,
                animation_plan=AnimationPlan(kind="none", steps=tuple()),
                semantic_map_patch={},
                constraints_patch={},
            )

        # Normalize to (domain, subdomain)
        norm = []
        for d in domains_in:
            if isinstance(d, str):
                norm.append((d, NC))
            elif isinstance(d, Mapping):
                dom = str(d.get("domain") or NC)
                subs = d.get("subdomains")
                if isinstance(subs, list) and subs:
                    for s in subs:
                        norm.append((dom, str(s)))
                else:
                    norm.append((dom, NC))
        norm_s = tuple(sorted(norm))

        entities = []
        for i, (dom, sub) in enumerate(norm_s):
            eid = f"domain:{dom}" if sub == NC else f"subdomain:{dom}:{sub}"
            entities.append(
                SceneEntity(
                    entity_id=eid,
                    kind="domain" if sub == NC else "subdomain",
                    label=dom if sub == NC else sub,
                    domain=dom,
                    glyph_rune_id=NC,
                    metrics={"order": float(i)},
                )
            )

        inst = self._instance(
            pattern_id="domain_lattice/v1",
            inputs={"domains": norm_s},
            failure_mode="none",
        )
        return PatternBuildResult(
            instance=inst,
            entities=tuple(entities),
            edges=tuple(),
            fields=tuple(),
            time_axis=NC,
            animation_plan=AnimationPlan(kind="none", steps=tuple()),
            semantic_map_patch={
                "position_semantics": "domain_layering_only",
            },
            constraints_patch={},
        )
