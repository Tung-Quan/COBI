"""Versioned UCI feature and outcome contract."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "https://archive.ics.uci.edu"
CARD = SOURCE + "/dataset/350/default+of+credit+card+clients"
ARCHIVE = SOURCE + "/static/public/350/default+of+credit+card+clients.zip"
FILENAME = "default of credit card clients.xls"
TARGET = "default.payment.next.month"
DOMAIN = "TAIWAN_CREDIT_CARD_2005"
HORIZON = "next payment month"
STATUS = ["PAY_0", *(f"PAY_{month}" for month in range(2, 7))]
BILLS = [f"BILL_AMT{month}" for month in range(1, 7)]
PAYMENTS = [f"PAY_AMT{month}" for month in range(1, 7)]
DEMOGRAPHICS = ["SEX", "EDUCATION", "MARRIAGE", "AGE"]
RAW_COLUMNS = ["ID", "LIMIT_BAL", *DEMOGRAPHICS, *STATUS, *BILLS, *PAYMENTS, TARGET]
CATEGORIES = list(range(-2, 10))
NUMERIC = ["LIMIT_BAL", *BILLS, *PAYMENTS]


def definition(name, unit, bounds, semantics):
    return dict(name=name, type="integer", unit=unit, bounds=bounds, semantics=semantics)


FEATURES = [
    definition("LIMIT_BAL", "NTD", [1, 10_000_000], "Credit limit including supplementary credit"),
    *(definition(name, "status code", [-2, 9],
                 f"Repayment status {month}/2005, preserved categorically including undocumented codes")
      for name, month in zip(STATUS, range(9, 3, -1))),
    *(definition(name, "NTD", [-10_000_000, 10_000_000], f"Statement amount {month}/2005")
      for name, month in zip(BILLS, range(9, 3, -1))),
    *(definition(name, "NTD", [0, 10_000_000], f"Prior payment amount {month}/2005")
      for name, month in zip(PAYMENTS, range(9, 3, -1))),
]
ALLOWLIST = [feature["name"] for feature in FEATURES]
CONTRACT = {
    "features": FEATURES, "target": TARGET, "horizon": HORIZON, "source_domain": DOMAIN,
    "preprocessing_version": "train-zscore-fixed-status-onehot-v1",
}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


SIGNATURE = hashlib.sha256(canonical(CONTRACT)).hexdigest()


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    temp.replace(path)
