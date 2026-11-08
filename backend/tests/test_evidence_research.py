import json

from app import evidence_research


def test_shadow_is_read_only_and_cannot_bypass_consent(client):
    original = client.get("/api/applications/DEMO-001").json()
    result = client.get("/api/evidence-ai/shadow/DEMO-001").json()
    assert result["status"] == "EVIDENCE_AI_VALIDATION_BLOCKED"
    assert result["mode"] == "SHADOW_ONLY"
    assert result["routing_authorized"] is False
    assert result["approval_authorized"] is False
    assert result["material_error_probability"] is None
    assert client.get("/api/applications/DEMO-001").json() == original
    revoked = client.post("/api/applications/DEMO-001/revoke-consent",
                          json={"reason": "Consent withdrawn for controlled test."})
    assert revoked.status_code == 200
    denied = client.get("/api/evidence-ai/shadow/DEMO-001").json()
    assert denied["status"] == "BLOCKED_MANDATORY_GATES"
    assert "consent" in denied["failed_gates"]
    assert denied["field_probabilities"] is None


def test_unverified_evidence_release_fails_closed(client, monkeypatch, tmp_path):
    monkeypatch.setattr(evidence_research, "OUTPUT", tmp_path)
    assert client.get("/api/evidence-ai/experiments/synthetic").json() == {"status": "NO_VERIFIED_RELEASE"}
    run = tmp_path / "synthetic"
    run.mkdir()
    (run / "release.json").write_text(json.dumps({"report_sha256": "invalid"}))
    (run / "report.json").write_text("{}")
    assert client.get("/api/evidence-ai/experiments/synthetic").status_code == 503
    assert client.get("/api/evidence-ai/experiments/other").status_code == 404
    assert client.get("/api/evidence-ai/experiments/synthetic/artifacts/observed.json").status_code == 404


def test_v4_research_summary_has_no_routing_authority(client):
    before = client.get("/api/applications/DEMO-001").json()
    response = client.get("/api/evidence-ai/v4/summary")
    assert response.status_code == 200
    result = response.json()
    assert result["validation_status"] == "EVIDENCE_AI_VALIDATION_BLOCKED"
    assert result["routing_authorized"] is False
    assert result["approval_authorized"] is False
    assert client.get("/api/applications/DEMO-001").json() == before
