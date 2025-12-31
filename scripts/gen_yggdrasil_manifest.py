from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from abx_runes.yggdrasil.emitter_real import RealEmitterConfig, emit_manifest_from_repo
from abx_runes.yggdrasil.io import save_manifest_dict
from abx_runes.yggdrasil.schema import ProvenanceSpec


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate yggdrasil.manifest.json deterministically from repo structure.")
    ap.add_argument("--repo-root", default=".", help="Repo root path (default: .)")
    ap.add_argument("--out", default="yggdrasil.manifest.json", help="Output file (default: yggdrasil.manifest.json)")
    ap.add_argument("--schema", default="yggdrasil-ir/0.1", help="Schema version string")
    ap.add_argument("--source-commit", default="unknown", help="Commit hash or tag (string)")
    args = ap.parse_args()

    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    prov = ProvenanceSpec(
        schema_version=str(args.schema),
        manifest_hash="",
        created_at=now,
        updated_at=now,
        source_commit=str(args.source_commit),
    )

    cfg = RealEmitterConfig(repo_root=Path(args.repo_root))
    manifest = emit_manifest_from_repo(cfg, prov)

    out_path = Path(args.repo_root) / str(args.out)
    save_manifest_dict(out_path, manifest)
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
