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

    # edges must reference existing nodes
    for ed in scene.edges:
        if ed.source not in ids or ed.target not in ids:
            raise SceneValidationError(f"edge references unknown node: {ed.source}->{ed.target}")
        if ed.weight != ed.weight:  # NaN check
            raise SceneValidationError("edge.weight is NaN")
        if ed.weight < 0:
            raise SceneValidationError("edge.weight must be >= 0")

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
