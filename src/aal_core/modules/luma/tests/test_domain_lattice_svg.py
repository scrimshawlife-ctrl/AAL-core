import sys
from pathlib import Path

# Ensure `src/` is importable (repo uses split package layout)
sys.path.insert(0, str(Path(__file__).resolve().parents[5] / "src"))

from aal_core.modules.luma import render
from aal_core.modules.luma.patterns.catalog import register_builtins


def _fixed_frame(payload: dict) -> dict:
    return {
        "utc": "2026-01-02T00:00:00Z",
        "module": "test.luma",
        "payload": payload,
        "abx_runes": {"used": ["0001"], "gate_state": "CLEAR"},
        "provenance": {
            "vendor_lock_sha256": "0" * 64,
            "manifest_sha256": "1" * 64,
        },
    }


def test_domain_lattice_svg_is_stable_and_present():
    # Registry is static today, but keep the explicit call for API stability.
    register_builtins()

    frame = _fixed_frame(
        {
            "domains": [
                {
                    "id": "d.tech",
                    "label": "Tech/AI",
                    "subdomains": [
                        {"id": "sd.llm", "label": "LLMs", "rank": 0},
                        {"id": "sd.chips", "label": "Hardware", "rank": 1},
                    ],
                },
                {
                    "id": "d.geo",
                    "label": "Geopolitics",
                    "subdomains": [
                        {"id": "sd.elections", "label": "Elections", "rank": 0},
                    ],
                },
            ],
            "domain_order": ["d.geo", "d.tech"],
            "subdomain_order": {"d.tech": ["sd.llm", "sd.chips"], "d.geo": ["sd.elections"]},
            # Motifs can coexist; lattice should still be a stable background map.
            "motifs": ["alpha", "beta"],
            "edges": [{"source": "alpha", "target": "beta", "magnitude": 0.8}],
        }
    )

    a1 = render(frame, mode="static", pattern_overrides=["motif_graph", "domain_lattice"])[0]
    a2 = render(frame, mode="static", pattern_overrides=["motif_graph", "domain_lattice"])[0]
    assert a1.content_sha256 == a2.content_sha256
    assert 'id="domain_lattice"' in a1.content

