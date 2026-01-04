"""
AAL-GIMLET Scan Module
File scanning and normalization for deterministic analysis.
"""

import hashlib
import json
import os
import zipfile
import tempfile
import shutil
from pathlib import Path
from typing import Optional, List, Tuple
from dataclasses import dataclass

from .contracts import FileInfo, FileMap, ProvenanceEnvelope, InspectMode


# Language detection by extension
_LANGUAGE_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "javascript",
    ".tsx": "typescript",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".md": "markdown",
    ".txt": "text",
    ".sh": "shell",
    ".toml": "toml",
    ".rs": "rust",
    ".go": "go",
    ".java": "java",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c",
    ".hpp": "cpp",
}

# Entrypoint detection heuristics
_ENTRYPOINT_NAMES = {
    "main.py",
    "__main__.py",
    "__init__.py",
    "index.js",
    "index.ts",
    "app.py",
    "server.py",
    "run.py",
    "setup.py",
    "manage.py",
    "main.go",
    "main.rs",
}


def _detect_language(path: str) -> Optional[str]:
    """Detect language from file extension"""
    ext = Path(path).suffix.lower()
    return _LANGUAGE_MAP.get(ext)


def _is_entrypoint(path: str) -> bool:
    """Heuristic check if file is likely an entrypoint"""
    name = Path(path).name.lower()
    return name in _ENTRYPOINT_NAMES


def _hash_file(file_path: Path) -> str:
    """Compute SHA256 hash of file contents"""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def _canonical_file_map_hash(file_map: FileMap) -> str:
    """Compute deterministic hash of FileMap"""
    # Sort files by path for determinism
    sorted_files = sorted(
        [{"path": f.path, "sha256": f.sha256, "size_bytes": f.size_bytes} for f in file_map.files],
        key=lambda x: x["path"]
    )
    blob = json.dumps(sorted_files, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()


def normalize_input(
    source_path: str,
    mode: InspectMode,
    run_seed: Optional[str] = None,
    exclude_patterns: Optional[List[str]] = None
) -> Tuple[FileMap, ProvenanceEnvelope, Optional[str]]:
    """
    Normalize input (directory or zip) into deterministic FileMap.

    Args:
        source_path: Path to directory or zip file
        mode: Operating mode
        run_seed: Optional deterministic seed
        exclude_patterns: Optional list of glob patterns to exclude (e.g., ["*.pyc", "__pycache__"])

    Returns:
        (FileMap, ProvenanceEnvelope, temp_dir_path)
        temp_dir_path is None for directories, set for extracted zips (caller must cleanup)
    """
    import time
    from fnmatch import fnmatch

    exclude_patterns = exclude_patterns or ["*.pyc", "__pycache__", ".git", "node_modules", ".DS_Store"]

    source = Path(source_path)
    temp_dir = None

    # Handle zip extraction
    if source.is_file() and source.suffix.lower() == ".zip":
        temp_dir = tempfile.mkdtemp(prefix="gimlet_")
        with zipfile.ZipFile(source, "r") as zf:
            # Extract with deterministic ordering
            members = sorted(zf.namelist())
            for member in members:
                zf.extract(member, temp_dir)
        scan_root = Path(temp_dir)
    elif source.is_dir():
        scan_root = source
    else:
        raise ValueError(f"source_path must be directory or .zip file, got: {source_path}")

    # Scan files
    files: List[FileInfo] = []
    total_size = 0
    languages_set = set()
    entrypoints = []

    for root, dirs, filenames in os.walk(scan_root):
        # Filter out excluded directories
        dirs[:] = [
            d for d in dirs
            if not any(fnmatch(d, pat) for pat in exclude_patterns)
        ]

        for filename in sorted(filenames):  # Sorted for determinism
            file_path = Path(root) / filename
            rel_path = str(file_path.relative_to(scan_root))

            # Skip excluded patterns
            if any(fnmatch(rel_path, pat) for pat in exclude_patterns):
                continue
            if any(fnmatch(filename, pat) for pat in exclude_patterns):
                continue

            # Compute metadata
            file_hash = _hash_file(file_path)
            size = file_path.stat().st_size
            lang = _detect_language(rel_path)
            is_entry = _is_entrypoint(rel_path)

            files.append(FileInfo(
                path=rel_path,
                sha256=file_hash,
                size_bytes=size,
                language=lang,
                is_entrypoint=is_entry
            ))

            total_size += size
            if lang:
                languages_set.add(lang)
            if is_entry:
                entrypoints.append(rel_path)

    # Build FileMap
    file_map = FileMap(
        files=files,
        total_size_bytes=total_size,
        file_count=len(files),
        languages=sorted(languages_set),
        entrypoints=sorted(entrypoints)
    )

    # Build provenance
    artifact_hash = _canonical_file_map_hash(file_map)
    provenance = ProvenanceEnvelope(
        artifact_hash=artifact_hash,
        run_seed=run_seed,
        tool_version="gimlet/0.1.0",
        timestamp_unix=int(time.time()),
        mode=mode
    )

    return (file_map, provenance, temp_dir)


def cleanup_temp(temp_dir: Optional[str]) -> None:
    """Clean up temporary directory if it exists"""
    if temp_dir and os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
