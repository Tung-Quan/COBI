"""Read-only checksum audit for protected V4/V4.1 release records."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def sha(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def v4_status() -> dict:
    # Preserve the exact repository path case: the committed file is lowercase
    # and this audit should also work on case-sensitive filesystems.
    manifest_path = ROOT / "reports/evidence-v4/final_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rows = []
    for item in manifest["artifacts"]:
        path = ROOT / item["path"]
        actual = sha(path)
        rows.append({"path": item["path"], "expected": item["sha256"], "actual": actual, "match": actual == item["sha256"]})
    return {"path": "reports/evidence-v4/final_manifest.json", "total": len(rows), "matched": sum(r["match"] for r in rows), "mismatches": [r for r in rows if not r["match"]]}


def v41_snapshot(manifest: dict, label: str) -> dict:
    groups = {}
    for group_name in ("source_checksums", "artifact_checksums"):
        mismatches = []
        for relative, expected in manifest.get(group_name, {}).items():
            actual = sha(ROOT / "reports/evidence-v4.1" / relative)
            if actual != expected:
                mismatches.append({"path": relative, "expected": expected, "actual": actual})
        groups[group_name] = {"total": len(manifest.get(group_name, {})), "matched": len(manifest.get(group_name, {})) - len(mismatches), "mismatches": mismatches}
    return {"snapshot": label, **groups}


def main() -> int:
    current_path = ROOT / "reports/evidence-v4.1/RELEASE_MANIFEST.json"
    current = json.loads(current_path.read_text(encoding="utf-8"))
    historical_text = subprocess.run(
        ["git", "show", "HEAD:reports/evidence-v4.1/RELEASE_MANIFEST.json"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout
    historical = json.loads(historical_text)
    c_path = ROOT / "reports/evidence-v4.1/data/generator-c-v1/C_PREDICTIONS_FROZEN.csv"
    v4_path = ROOT / "frontend/src/EvidenceResearch.tsx"
    result = {
        "head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip(),
        "branch": subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip(),
        "frozen_c_predictions": {"path": "reports/evidence-v4.1/data/generator-c-v1/C_PREDICTIONS_FROZEN.csv", "sha256": sha(c_path), "expected": "03d1a2a6aa3d52eae483cca2d538e8cf71777eea17aa32215160bc5be3dc7523"},
        "protected_v4": v4_status(),
        "protected_v4_manifest_file": {"path": "frontend/src/EvidenceResearch.tsx", "expected": "b3f7b74ec8ab8d1c773c970f5f31d3f2181c1f539fb968d37ab0fb4d7eff0947", "actual": sha(v4_path)},
        "v41_current_worktree_manifest": v41_snapshot(current, "CURRENT_WORKTREE"),
        "v41_committed_head_manifest_applied_to_current_files": v41_snapshot(historical, "HEAD_MANIFEST_CURRENT_FILES"),
        "tong_report": {"path": "reports/evidence-v4.1/TONG_HOP_COBI_V4_1.md", "sha256": sha(ROOT / "reports/evidence-v4.1/TONG_HOP_COBI_V4_1.md")},
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["frozen_c_predictions"]["sha256"] == result["frozen_c_predictions"]["expected"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
