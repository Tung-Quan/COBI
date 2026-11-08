"""Freeze dataset-bound stratified membership before any preprocessing fit."""

import json
from datetime import datetime, timezone

import pandas as pd
from sklearn.model_selection import train_test_split

from ml.contracts import ROOT, SIGNATURE, TARGET, sha, write_json

DATASET = ROOT / "data/manifest/uci350.yaml"
CSV = ROOT / "data/processed/uci350.csv"
LOCK = ROOT / "data/processed/uci350-split-v2.json"
PROTOCOL = ROOT / "ml/protocol.json"


def dataset():
    manifest = json.loads(DATASET.read_text(encoding="utf-8"))
    if (manifest["status"], manifest["license"], manifest["feature_signature"], manifest["normalized_sha256"]) != (
        "VERIFIED", "CC BY 4.0", SIGNATURE, sha(CSV)
    ):
        raise ValueError("Verified UCI provenance and checksum required")
    return manifest, pd.read_csv(CSV).set_index("ID", verify_integrity=True)


def assignments(y, config):
    sizes = config["split"]
    options = dict(random_state=config["seed"])
    train, rest = train_test_split(y.index, train_size=sizes["train"], stratify=y, **options)
    validation, rest = train_test_split(rest, train_size=sizes["validation"], stratify=y.loc[rest], **options)
    calibration, test = train_test_split(rest, train_size=sizes["calibration"], stratify=y.loc[rest], **options)
    return {name: sorted(map(int, ids)) for name, ids in zip(sizes, (train, validation, calibration, test), strict=True)}


def audit_membership(y, membership, config):
    ids = [item for group in membership.values() for item in group]
    if len(ids) != len(set(ids)) or set(ids) != set(y.index) or set(membership) != set(config["split"]):
        raise ValueError("Split overlap or incomplete membership")
    result = {}
    for name, group in membership.items():
        positives = int(y.loc[group].sum())
        negatives = len(group) - positives
        if len(group) != config["split"][name] or min(positives, negatives) < config["minimum_calibration_and_test_events_per_class"]:
            raise ValueError(f"INSUFFICIENT_TEST_EVIDENCE: {name} cohort size or events")
        result[name] = {"n": len(group), "events": positives, "non_events": negatives,
                        "prevalence": positives / len(group)}
    return result


def main():
    manifest, data = dataset()
    config = json.loads(PROTOCOL.read_text())
    membership = assignments(data[TARGET], config)
    locked = {
        "seed": config["seed"], "strategy": manifest["split_protocol"], "normalized_sha256": sha(CSV),
        "protocol_sha256": sha(PROTOCOL), "split_code_sha256": sha(__file_path()),
        "split_overlap": False, "cohorts": audit_membership(data[TARGET], membership, config),
        "membership": membership,
    }
    if LOCK.exists():
        existing = json.loads(LOCK.read_text())
        if {k: v for k, v in existing.items() if k != "locked_at"} != locked:
            raise ValueError("Existing split lock differs; investigate before defining a new experiment")
        locked = existing
    else:
        locked["locked_at"] = datetime.now(timezone.utc).isoformat()
        write_json(LOCK, locked)
    print(json.dumps({k: v for k, v in locked.items() if k != "membership"} | {"lock_sha256": sha(LOCK)}, indent=2))


def __file_path():
    from pathlib import Path
    return Path(__file__)


if __name__ == "__main__":
    main()
