"""Acquire and cross-check the published UCI XLS and ucimlrepo CSV."""

import io
import json
from datetime import datetime, timezone
from urllib.request import urlopen
from zipfile import ZipFile

import numpy as np
import pandas as pd
from ucimlrepo import fetch_ucirepo

from ml.contracts import (
    ALLOWLIST, ARCHIVE, CARD, DOMAIN, FEATURES, FILENAME, HORIZON, RAW_COLUMNS, ROOT,
    SIGNATURE, SOURCE, STATUS, TARGET, sha, write_json,
)

MANIFEST = ROOT / "data/manifest/uci350.yaml"  # JSON is a subset of YAML 1.2.
PROCESSED = ROOT / "data/processed/uci350.csv"


def download(url):
    if not url.startswith(SOURCE + "/"):
        raise ValueError("Non-UCI download URL")
    with urlopen(url, timeout=75) as response:
        if not response.url.startswith(SOURCE + "/"):
            raise ValueError("Non-UCI redirect")
        return response.read()


def normalize(frame):
    mapping = dict(zip((f"X{i}" for i in range(1, 24)), RAW_COLUMNS[1:-1]))
    frame = frame.rename(columns=mapping | {"Y": TARGET, "default payment next month": TARGET})
    if frame.columns.tolist() != RAW_COLUMNS or frame.shape != (30000, 25):
        raise ValueError("SCHEMA_MISMATCH: unexpected UCI columns or shape")
    frame = frame.apply(pd.to_numeric, errors="raise")
    values = frame.to_numpy()
    if not np.isfinite(values).all() or not (values == np.trunc(values)).all():
        raise ValueError("SCHEMA_MISMATCH: expected finite integers")
    if frame.ID.duplicated().any() or set(frame.ID) != set(range(1, 30001)):
        raise ValueError("SCHEMA_MISMATCH: expected unique UCI sample IDs")
    if set(frame[TARGET]) != {0, 1}:
        raise ValueError("SCHEMA_MISMATCH: expected two binary classes")
    for feature in FEATURES:
        low, high = feature["bounds"]
        if not frame[feature["name"]].between(low, high).all():
            raise ValueError(f"SCHEMA_MISMATCH: feature range {feature['name']}")
    return frame.astype("int64")


def main():
    raw = ROOT / "data/raw"
    raw.mkdir(parents=True, exist_ok=True)
    manifest = dict(dataset_id="UCI_350", source_url=CARD, archive_url=ARCHIVE,
                    provider="UCI Machine Learning Repository", citation="Yeh, I. (2009), DOI 10.24432/C55S3H",
                    license="CC BY 4.0", license_url="https://creativecommons.org/licenses/by/4.0/",
                    source_domain=DOMAIN, target=TARGET, label_mapping={"0": "no default", "1": "default"},
                    horizon=HORIZON, population="Taiwan credit-card customers",
                    snapshot="Monthly credit-card histories April–September 2005, no application or customer-group index",
                    split_protocol="STRATIFIED_RANDOM_60_15_10_15_NOT_OOT",
                    feature_allowlist=ALLOWLIST, feature_signature=SIGNATURE,
                    application_compatibility="BENCHMARK_ONLY")
    stage = "DOWNLOAD_FAILED"
    try:
        card = download(CARD)
        if b"creativecommons.org/licenses/by/4.0" not in card or b"10.24432/C55S3H" not in card:
            stage = "LICENSE_REVIEW_REQUIRED"
            raise ValueError("Official license or citation changed")
        (raw / "uci350-card.html").write_bytes(card)
        package = fetch_ucirepo(id=350)
        csv_url = package.metadata.data_url
        csv_bytes = download(csv_url)
        archive_bytes = download(ARCHIVE)
        (raw / "uci350.zip").write_bytes(archive_bytes)
        (raw / "uci350-official.csv").write_bytes(csv_bytes)
        stage = "SCHEMA_MISMATCH"
        with ZipFile(io.BytesIO(archive_bytes)) as archive:
            original = archive.read(FILENAME)
        (raw / FILENAME).write_bytes(original)
        xls = normalize(pd.read_excel(io.BytesIO(original), header=1, engine="xlrd"))
        csv = normalize(pd.read_csv(io.BytesIO(csv_bytes)))
        from_package = normalize(package.data.original)
        pd.testing.assert_frame_equal(xls, csv)
        pd.testing.assert_frame_equal(csv, from_package)
        normalized = csv.loc[:, ["ID", *ALLOWLIST, TARGET]]
        PROCESSED.parent.mkdir(parents=True, exist_ok=True)
        normalized.to_csv(PROCESSED, index=False, lineterminator="\n")
        manifest.update(
            status="VERIFIED", retrieved_utc=datetime.now(timezone.utc).isoformat(),
            original_filename=FILENAME, csv_url=csv_url, original_sha256=sha(raw / FILENAME),
            raw_archive_sha256=sha(raw / "uci350.zip"), raw_csv_sha256=sha(raw / "uci350-official.csv"),
            license_snapshot_sha256=sha(raw / "uci350-card.html"), normalized_sha256=sha(PROCESSED),
            rows=len(csv), source_features=23, source_columns=RAW_COLUMNS, normalized_columns=normalized.columns.tolist(),
            label_counts={str(label): int(count) for label, count in csv[TARGET].value_counts().items()},
            missingness={name: int(count) for name, count in csv.isna().sum().items()},
            unique_sample_ids=int(csv.ID.nunique()), duplicate_predictor_rows=int(csv[ALLOWLIST].duplicated().sum()),
            feature_ranges={name: [int(csv[name].min()), int(csv[name].max())] for name in ALLOWLIST},
            repayment_code_counts={name: {str(k): int(v) for k, v in csv[name].value_counts().items()} for name in STATUS},
            training_eligibility="UCI research benchmark only", restrictions="CC BY 4.0 attribution; excluded ID and demographics",
            limitations=["No per-application dates", "No customer grouping key", "No Vietnamese checkout outcomes",
                         "Some repayment codes are undocumented in the UCI description; encoded as categories"])
        write_json(MANIFEST, manifest)
    except Exception as exc:
        # A failed refresh must not overwrite previously verified provenance.
        write_json(ROOT / "data/quarantine/uci350-failure.json", manifest | {"status": stage, "error": str(exc)})
        raise
    print(json.dumps({key: manifest[key] for key in ("status", "rows", "label_counts", "raw_archive_sha256",
                                                      "original_sha256", "normalized_sha256")}, indent=2))


if __name__ == "__main__":
    main()
