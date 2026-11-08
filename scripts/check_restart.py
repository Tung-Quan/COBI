"""Verify repeatable UCI predictions across two clean API process starts."""

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd

from ml.contracts import ALLOWLIST, DOMAIN, HORIZON, SIGNATURE
from ml.predict import MODEL_ID
from ml.split import CSV, LOCK


def roundtrip(db_path, payload):
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", str(port)],
        env=os.environ | {"COBI_DB_PATH": str(db_path)}, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        base = f"http://127.0.0.1:{port}"
        for _ in range(100):
            try:
                with urlopen(base + "/api/health", timeout=2) as response:
                    assert response.status == 200
                break
            except URLError:
                if process.poll() is not None:
                    raise RuntimeError("Research API exited during startup")
                time.sleep(0.1)
        else:
            raise RuntimeError("Research API did not become healthy")

        def call(body):
            request = Request(base + f"/api/research/models/{MODEL_ID}/predict",
                              data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
            with urlopen(request, timeout=60) as response:
                return json.load(response)

        result = call(payload)
        try:
            call(payload | {"source_domain": "COBI_SYNTHETIC_CHECKOUT"})
        except HTTPError as exc:
            assert exc.code == 422 and json.load(exc)["detail"] == "PD_UNAVAILABLE_SCHEMA_MISMATCH"
        else:
            raise AssertionError("Incompatible domain was accepted")
        try:
            call(payload | {"rows": [{"existing_monthly_debt_vnd": 1_000_000}]})
        except HTTPError as exc:
            assert exc.code == 422 and json.load(exc)["detail"] == "PD_UNAVAILABLE_SCHEMA_MISMATCH"
        else:
            raise AssertionError("Incompatible feature schema was accepted")
        return result
    finally:
        process.terminate()
        process.wait(timeout=15)


def main():
    validation_ids = json.loads(LOCK.read_text())["membership"]["validation"][:16]
    rows = pd.read_csv(CSV).set_index("ID").loc[validation_ids, ALLOWLIST].to_dict("records")
    payload = {"rows": rows, "source_domain": DOMAIN, "label_horizon": HORIZON, "feature_signature": SIGNATURE}
    with tempfile.TemporaryDirectory() as path:
        database = Path(path) / "restart-check.sqlite"
        first = roundtrip(database, payload)
        second = roundtrip(database, payload)
    assert first["risk_source"] == second["risk_source"] == "PUBLIC_BENCHMARK_ONLY"
    for name in ("raw", "calibrated"):
        np.testing.assert_allclose(first[name], second[name], rtol=1e-6, atol=1e-7)
    print("PASS: 16 held validation rows, raw and calibrated probabilities match across API restarts; domain and feature mismatches rejected.")


if __name__ == "__main__":
    main()
