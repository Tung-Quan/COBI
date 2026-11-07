from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import db
from app.main import app


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    seed_path = Path(__file__).parents[1] / "data" / "seed_applications.json"
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.sqlite")
    monkeypatch.setattr(db, "SEED_PATH", seed_path)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def baseline():
    path = Path(__file__).parents[1] / "data" / "seed_applications.json"
    return next(item for item in json.loads(path.read_text(encoding="utf-8")) if item["application_id"] == "DEMO-001")
