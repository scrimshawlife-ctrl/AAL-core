from typing import Dict, Set

from ..contracts.scene_ir import LumaSceneIR


class SceneValidationError(ValueError):
    pass


def validate_scene(scene: LumaSceneIR) -> None:
    if not scene.scene_id:
        raise SceneValidationError("scene_id required")
    if not isinstance(scene.seed, int):
        raise SceneValidationError("seed must be int")

    ids: Set[str] = set()
    for e in scene.entities:
        if not e.entity_id:
            raise SceneValidationError("entity_id required")
        if e.entity_id in ids:
            raise SceneValidationError(f"duplicate entity_id: {e.entity_id}")
        ids.add(e.entity_id)

    if isinstance(scene.edges, str):
        if scene.edges != NC:
            errors.append("edges must be tuple[...] or not_computable")
    else:
        for ed in scene.edges:
            # Transfer contract: must connect explicit domain entities and carry a numeric magnitude.
            if ed.kind == "transfer":
                if not (ed.source_id.startswith("domain:") and ed.target_id.startswith("domain:")):
                    errors.append(f"transfer edge must connect domain:* entities: {ed.edge_id}")
                sd = ed.source_id.split("domain:", 1)[-1]
                td = ed.target_id.split("domain:", 1)[-1]
                if not sd or not td or sd == NC or td == NC:
                    errors.append(f"transfer edge missing source/target domain: {ed.edge_id}")
                if not isinstance(ed.resonance_magnitude, (int, float)):
                    errors.append(f"transfer edge resonance_magnitude must be numeric: {ed.edge_id}")

            if (
                isinstance(ed.resonance_magnitude, (int, float))
                and float(ed.resonance_magnitude) < 0.0
            ):
                errors.append(f"edge resonance_magnitude must be >= 0: {ed.edge_id}")
            if isinstance(ed.uncertainty, (int, float)):
                u = float(ed.uncertainty)
                if u < 0.0 or u > 1.0:
                    errors.append(f"edge uncertainty must be in [0,1]: {ed.edge_id}")

    # patterns must reference known entities/edge indices
    for p in scene.patterns:
        for eid in p.entities:
            if eid not in ids:
                raise SceneValidationError(f"pattern references unknown entity: {eid}")
        for idx in p.edges:
            if idx < 0 or idx >= len(scene.edges):
                raise SceneValidationError(f"pattern edge index out of range: {idx}")

    # enforce “not_computable” contract if present
    nc: Dict[str, bool] = scene.constraints.get("not_computable", {})
    if nc and not isinstance(nc, dict):
        raise SceneValidationError("constraints.not_computable must be dict[str,bool]")
