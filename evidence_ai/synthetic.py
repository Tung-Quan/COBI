"""Controlled evidence generator. Gold values and observed features are separate."""

from datetime import date, timedelta
from hashlib import sha256
from pathlib import Path
import json

import numpy as np

from ml.contracts import ROOT, canonical, sha, write_json

PROTOCOL = Path(__file__).with_name("protocol.json")
DATA = ROOT / "data/processed/evidence-v3"
FIELDS = ("income", "debt", "purchase")
SPLITS = ("train", "validation", "calibration", "test")
SOURCES = ("statement", "payroll", "merchant")
CAP = 6


def build_document(rng, truth, template, date_at, limits, group, case_index, index):
    source = SOURCES[index % len(SOURCES)]
    verified = bool(rng.random() > .16)
    ocr_quality = float(rng.uniform(.48, .995))
    documented = dict(truth)
    observed = {}
    # Draw defects independently of CS; metadata and model observations are imperfect proxies.
    for field, reference in truth.items():
        if rng.random() < (.065 if verified else .16):
            documented[field] = max(1, reference + int(rng.choice([-1, 1])) * int(limits[field] * rng.uniform(.4, 3.4)))
        value = documented[field]
        draw = rng.random()
        if draw < .015 + .08 * (1 - ocr_quality):
            value = None
        elif draw < .07 + .22 * (1 - ocr_quality):
            value = max(1, value + int(rng.choice([-1, 1])) * int(limits[field] * rng.uniform(.08, 3)))
        observed[field] = value
    material = any(value is None or abs(value - truth[field]) >= limits[field]
                   for field, value in observed.items())
    critical = any(value is None or abs(value - truth[field]) >= 2 * limits[field]
                   for field, value in observed.items())
    inconsistent = {field: int(abs(value - truth[field]) >= limits[field])
                    for field, value in documented.items()}
    wording = "observed " + " ".join(f"{field} {value if value is not None else '[missing]'}" for field, value in observed.items())
    document_key = f"synthetic-{group}-{case_index}-{index}"
    payload = {
        "document_key": document_key, "source": source, "template": template, "values": observed,
        "age_days": int(rng.integers(1, 91)), "verified": verified, "ocr_quality": ocr_quality,
        "text": wording, "observed_at": date_at.isoformat(),
    }
    return payload, {
        "document_key": document_key,
        "observed_payload_sha256": sha256(canonical(payload)).hexdigest(),
        "label_origin": "PROGRAMMATIC_GOLD", "material_evidence_error": int(material),
        "critical_evidence_error": int(critical),
        "field_extraction_error": {field: int(value != documented[field]) for field, value in observed.items()},
        "cross_source_inconsistency_against_synthetic_reference": inconsistent,
        "verification_required": int(material or not verified),
    }


def generate(config):
    rng = np.random.default_rng(config["generator_seed"])
    observations, labels = [], []
    for i in range(config["customers"]):
        group = f"g-{i:04d}"
        for j in range(config["cases_per_customer"]):
            case_key = f"{group}-{j}"
            date_at = date(2024, 1, 1) + timedelta(days=i * 2 + j)
            truth = {"income": int(rng.integers(6, 36) * 400000),
                     "debt": int(rng.integers(0, 25) * 100000), "purchase": int(rng.integers(7, 41) * 250000)}
            # Late-only membership tag tests grouping. The separate format challenge shifts inputs.
            template = "late-only" if i >= int(config["customers"] * .85) and i % 3 == 0 else f"fixture-{i % 5}"
            pairs = [build_document(rng, truth, template, date_at, config["material_vnd_thresholds"], group, j, d)
                     for d in range(int(rng.integers(2, CAP + 1)))]
            docs, targets = map(list, zip(*pairs))
            observations.append({"case_key": case_key, "customer_group": group, "observed_at": date_at.isoformat(),
                                 "income_history_months": int(rng.integers(3, 13)), "documents": docs})
            labels.append({"case_key": case_key, "documents": targets})
    return observations, labels


def split_cases(rows, fractions):
    dates = {}
    for row in rows:
        dates.setdefault(row["customer_group"], []).append(date.fromisoformat(row["observed_at"]))
    groups = sorted(dates, key=lambda group: (min(dates[group]), group))
    boundaries = [0, *map(int, np.rint(np.cumsum(fractions[:-1]) * len(groups))), len(groups)]
    output = {}
    for index, split in enumerate(SPLITS):
        cohort = set(groups[boundaries[index]:boundaries[index + 1]])
        output[split] = [row["case_key"] for row in rows if row["customer_group"] in cohort]
        if index and min(min(dates[group]) for group in cohort) <= max(dates[groups[boundaries[index] - 1]]):
            raise ValueError("Chronological group boundary overlaps")
    return output


def freeze(config):
    observations, labels = generate(config)
    split = split_cases(observations, config["split_fractions"])
    DATA.mkdir(parents=True, exist_ok=True)
    files = {"observed.json": observations, "technical_labels.json": labels, "locked_split.json": split}
    for name, records in files.items():
        path = DATA / name
        if path.exists():
            if json.loads(path.read_text()) != records:
                raise ValueError(f"Locked data changed: {name}")
        else:
            write_json(path, records)
    return observations, labels, split, {name: sha(DATA / name) for name in files}


if __name__ == "__main__":
    _, _, partitions, hashes = freeze(json.loads(PROTOCOL.read_text()))
    print(json.dumps({"case_counts": {name: len(rows) for name, rows in partitions.items()}, "sha256": hashes}, indent=2))
