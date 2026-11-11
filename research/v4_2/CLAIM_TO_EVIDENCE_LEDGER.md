# Claim-to-Evidence Ledger

Status codes: `VERIFIED_IN_REPO` means a primary repository artifact or direct hash supports the claim's stated form; `REPORTED_ONLY` means a report/log states it but this continuation did not rerun the underlying experiment; `INCONSISTENT` means direct sources disagree; `NOT_FOUND` means no adequate source was located.

| Claim | Repository evidence | Status | Qualification |
|---|---|---|---|
| Generator C is `semantic-ledger-c-v1.0`, seed 2026110802, protocol `cobi-evidence-v4.1-c1.0` | `reports/evidence-v4.1/data/generator-c-v1/C_EVALUATION_MANIFEST.json`, `GENERATOR_C_METRICS.json`, `REPRODUCTION.md` | `VERIFIED_IN_REPO` | Values are present in historical manifests; no new C experiment run |
| 840 customer groups, 1,680 applications, 6,791 docs | `reports/evidence-v4.1/GENERATOR_C_SUMMARY.json`, manifest and historical report | `REPORTED_ONLY` | Not independently recounted in this task |
| Semantic Hybrid threshold 0.500031490427 | `reports/evidence-v4.1/GENERATOR_C_METRICS.json`, evaluation/reproduction artifacts | `VERIFIED_IN_REPO` | Presence/provenance verified; no model selection or threshold rerun |
| Frozen C prediction digest `03d1…7523` | Direct SHA-256 of `reports/evidence-v4.1/data/generator-c-v1/C_PREDICTIONS_FROZEN.csv`; `C_EVALUATION_MANIFEST.json` | `VERIFIED_IN_REPO` | Direct hash matches; no scoring/replay performed |
| Critical detection 520/520; legitimate false flags 400/6,271; review 520/1,680; C1/C3/C5 false flags 0/2,927 | `GENERATOR_C_METRICS.json`, `GENERATOR_C_REPORT.md`, `VERIFICATION_LOG.md` | `REPORTED_ONLY` | Current run intentionally did not rescore C; preserved as historical claims |
| AP 0.5652; Brier 0.0339; Log Loss 0.0939 | Same metrics/report and verification log | `REPORTED_ONLY` | No recalibration/rescoring performed |
| Semantic XGBoost `NOT_EVALUATED` | `GENERATOR_C_METRICS.json`, `GENERATOR_C_REPORT.md`, `REPRODUCTION.md` | `VERIFIED_IN_REPO` | No model artifact/confirmed evaluation found; remains not evaluated |
| D1.1 100 candidate omissions with split 60/15/15/10 and 200 stale cases | Raw D1.1 data, four split manifests, source rule and audit script; `D1_1_AUDIT_SUMMARY.json`; final scoped test | `VERIFIED_IN_REPO` | Candidate corrections remain pending; not approved gold |
| V4 protected manifest is 95/96 with EvidenceResearch mismatch | `reports/evidence-v4/final_manifest.json`, `reports/evidence-v4.1/RECOVERY_AUDIT.md`; direct SHA/current Git blob | `VERIFIED_IN_REPO` | Expected b3f… differs from actual 54da…; the current blob was present at both the UI and V4 manifest commits; original expected bytes were not recovered |
| Current V4.1 worktree release manifest is 14/14 sources and 51/52 artifacts | Current modified `RELEASE_MANIFEST.json`, separate `FINAL_MANIFEST.json`, direct file hashes and backend checksum guard | `VERIFIED_IN_REPO` | One untracked TONG report mismatch in both current records; current `FINAL_MANIFEST` is 100/101, while the stale verification log reports 100/100 for a prior snapshot |
| 37 backend pass, 7 semantic pass, 2 API pass, frontend build and desktop/mobile E2E pass, final 100/100 | `reports/evidence-v4.1/VERIFICATION_LOG.md` | `REPORTED_ONLY` | Historical log was not rerun as a suite in this audit; current backend/API checks were rerun separately and fail two API tests at checksum guard |
