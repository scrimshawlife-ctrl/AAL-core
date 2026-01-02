from __future__ import annotations

from typing import Any, Dict, List, Mapping, Tuple

from ...contracts.enums import NotComputable, PatternKind
from ...contracts.scene_ir import AnimationPlan, SceneEntity
from ..base import BasePattern, PatternBuildResult

NC = NotComputable.VALUE.value


class DomainLatticePattern(BasePattern):
    """
    Grid / layered domain-subdomain map (static coordinate scaffold).

    Canonical semantics:
    - Each domain is a column.
    - Subdomains stack top-to-bottom within their domain column.
    - This pattern is instrumentation only (non-influential); it does not imply importance.
    """

    kind = PatternKind.DOMAIN_LATTICE

    def input_contract(self) -> Mapping[str, Any]:
        return {
            "domains": (
                "list[str] (domain_ids) OR "
                "list[{id?,domain?,label?,family?,subdomains?}] "
                "(subdomains may be list[str] or list[{id?,label?,rank?}])"
            ),
            "domain_order": "list[str] (optional)",
            "subdomain_order": "map[domain_id -> list[str]] (optional)",
        }

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

        # Optional ordering hints (also mirrored into scene.constraints via constraints_patch).
        domain_order = frame_payload.get("domain_order")
        subdomain_order = frame_payload.get("subdomain_order")
        constraints_patch: Dict[str, Any] = {}
        if isinstance(domain_order, list) and domain_order:
            constraints_patch["domain_order"] = [str(x) for x in domain_order]
        if isinstance(subdomain_order, Mapping) and subdomain_order:
            # Normalize to {str: [str,...]} with stable ordering.
            tmp: Dict[str, List[str]] = {}
            for k, v in subdomain_order.items():
                if isinstance(v, list) and v:
                    tmp[str(k)] = [str(x) for x in v]
            if tmp:
                constraints_patch["subdomain_order"] = dict(sorted(tmp.items(), key=lambda kv: kv[0]))

        # Parse domains + subdomains (accept legacy keys for forward-compatibility).
        domains: Dict[str, Dict[str, Any]] = {}
        for item in domains_in:
            if isinstance(item, str):
                dom_id = str(item)
                domains.setdefault(dom_id, {"id": dom_id, "label": dom_id, "family": dom_id, "subdomains": []})
                continue
            if isinstance(item, Mapping):
                dom_id = str(item.get("id") or item.get("domain") or NC)
                if not dom_id or dom_id == NC:
                    continue
                d0 = domains.setdefault(
                    dom_id,
                    {
                        "id": dom_id,
                        "label": str(item.get("label") or dom_id),
                        "family": str(item.get("family") or dom_id),
                        "subdomains": [],
                    },
                )
                subs = item.get("subdomains")
                if isinstance(subs, list) and subs:
                    d0["subdomains"] = list(subs)
                continue

        if not domains:
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
                constraints_patch=constraints_patch,
            )

        # Domain ordering: constraints_patch.domain_order (if present) else deterministic sort.
        domain_ids_all = sorted(domains.keys())
        domain_ids: List[str] = []
        dom_order = constraints_patch.get("domain_order")
        if isinstance(dom_order, list) and dom_order:
            for did in dom_order:
                if did in domains and did not in domain_ids:
                    domain_ids.append(did)
            for did in domain_ids_all:
                if did not in domain_ids:
                    domain_ids.append(did)
        else:
            domain_ids = domain_ids_all

        # Subdomain ordering per domain: constraints_patch.subdomain_order (if present)
        # else deterministic by (rank, subdomain_id).
        sub_order_map = constraints_patch.get("subdomain_order")
        if not isinstance(sub_order_map, Mapping):
            sub_order_map = {}

        entities = []
        for i, dom_id in enumerate(domain_ids):
            d = domains[dom_id]
            entities.append(
                SceneEntity(
                    entity_id=dom_id,
                    kind="domain",
                    label=str(d.get("label") or dom_id),
                    domain=str(d.get("family") or dom_id),
                    glyph_rune_id=NC,
                    metrics={"order": float(i)},
                )
            )

            subs_in = d.get("subdomains") or []
            parsed_subs: Dict[str, Dict[str, Any]] = {}
            if isinstance(subs_in, list):
                for s in subs_in:
                    if isinstance(s, str):
                        sid = str(s)
                        parsed_subs.setdefault(sid, {"id": sid, "label": sid, "rank": None})
                    elif isinstance(s, Mapping):
                        sid = str(s.get("id") or s.get("subdomain") or s.get("label") or NC)
                        if not sid or sid == NC:
                            continue
                        parsed_subs.setdefault(
                            sid,
                            {
                                "id": sid,
                                "label": str(s.get("label") or sid),
                                "rank": s.get("rank"),
                            },
                        )

            sub_ids_all = sorted(parsed_subs.keys())
            ordered: List[str] = []
            forced = sub_order_map.get(dom_id)
            if isinstance(forced, list) and forced:
                for sid in forced:
                    sid_s = str(sid)
                    if sid_s in parsed_subs and sid_s not in ordered:
                        ordered.append(sid_s)
                for sid in sub_ids_all:
                    if sid not in ordered:
                        ordered.append(sid)
            else:
                def _k(sid: str) -> Tuple[int, str]:
                    r = parsed_subs[sid].get("rank")
                    try:
                        r_int = int(r) if r is not None else 10**9
                    except Exception:
                        r_int = 10**9
                    return (r_int, sid)

                ordered = sorted(sub_ids_all, key=_k)

            for j, sid in enumerate(ordered):
                info = parsed_subs[sid]
                metrics: Dict[str, Any] = {"order": float(j)}
                r = info.get("rank")
                if isinstance(r, (int, float)):
                    metrics["rank"] = float(r)
                entities.append(
                    SceneEntity(
                        entity_id=sid,
                        kind="subdomain",
                        label=str(info.get("label") or sid),
                        domain=dom_id,  # subdomain belongs-to domain_id
                        glyph_rune_id=NC,
                        metrics=metrics,
                    )
                )

        inst = self._instance(
            pattern_id="domain_lattice/v1",
            inputs={
                "domains": tuple(
                    (did, str(domains[did].get("label") or did), tuple(sorted(str(x) for x in (domains[did].get("subdomains") or ()))))
                    for did in domain_ids
                ),
                "domain_order": tuple(constraints_patch.get("domain_order") or ()),
                "subdomain_order": tuple(
                    (k, tuple(v)) for k, v in sorted((constraints_patch.get("subdomain_order") or {}).items())
                ),
            },
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
            constraints_patch=constraints_patch,
        )
