"""Fetch selected external reference sources for STINT_1.1.

This script intentionally admits only source files needed for the reference
layer. External sources are not client ground truth and cannot create a
measurement denominator without later target-specific validation.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXTERNAL_DIR = ROOT / "external"
MANIFEST_PATH = EXTERNAL_DIR / "source-manifest.json"


def run(cmd: list[str], cwd: Path | None = None) -> None:
    subprocess.run(cmd, cwd=cwd, check=True)


def copy_path(src: Path, dst: Path) -> None:
    if src.is_dir():
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns(".git", "__pycache__"))
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def clone_at(url: str, commit: str, destination: Path) -> None:
    run(["git", "clone", "--depth", "1", url, str(destination)])
    actual = subprocess.check_output(["git", "-C", str(destination), "rev-parse", "HEAD"], text=True).strip()
    if actual != commit:
        raise RuntimeError(f"Unexpected HEAD for {url}: {actual} != {commit}")


def main() -> int:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="fsa_ref_ingest_") as tmp:
        tmp_root = Path(tmp)
        for source in manifest["sources"]:
            source_id = source["source_id"]
            upstream = tmp_root / source_id
            clone_at(source["upstream_url"], source["pinned_commit"], upstream)
            target_dir = EXTERNAL_DIR / source_id
            target_dir.mkdir(parents=True, exist_ok=True)
            for relative in source.get("included_paths", []):
                copy_path(upstream / relative, target_dir / relative)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

