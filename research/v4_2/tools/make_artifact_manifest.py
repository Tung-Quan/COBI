"""Write/check a deterministic manifest scoped to research/v4_2 only."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "FINAL_ARTIFACT_MANIFEST.json"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build() -> dict:
    files = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path == MANIFEST or "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        files.append({"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": sha256(path)})
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT.parents[1], check=True, capture_output=True, text=True).stdout.strip()
    branch = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=ROOT.parents[1], check=True, capture_output=True, text=True).stdout.strip()
    return {
        "manifest_version": "cobi-v4.2-phase1-closeout-1.0",
        "scope": "research/v4_2/",
        "branch": branch,
        "head": head,
        "self_hash_excluded": True,
        "ignored_python_cache_excluded": True,
        "file_count": len(files),
        "files": files,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="compare current files with existing manifest without writing")
    args = parser.parse_args()
    current = build()
    if args.check:
        if not MANIFEST.is_file():
            print("MISSING_MANIFEST")
            return 2
        old = json.loads(MANIFEST.read_text(encoding="utf-8"))
        expected = {item["path"]: item["sha256"] for item in old["files"]}
        actual = {item["path"]: item["sha256"] for item in current["files"]}
        mismatches = sorted(path for path in set(expected) | set(actual) if expected.get(path) != actual.get(path))
        print(json.dumps({"status": "MATCH" if not mismatches else "MISMATCH", "file_count": len(actual), "mismatches": mismatches}, indent=2))
        return 0 if not mismatches else 1
    MANIFEST.write_text(json.dumps(current, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"path": "research/v4_2/FINAL_ARTIFACT_MANIFEST.json", "file_count": current["file_count"], "status": "WRITTEN"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
