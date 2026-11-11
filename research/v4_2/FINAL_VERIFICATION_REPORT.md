# Final Verification Report — COBI V4.2 Phase 1 Closeout

**Date:** 2026-11-11 (Asia/Saigon)  
**Final status:** `PHASE1_COMPLETE_PHASE2_BLOCKED`  
**Repository:** `C:\disk D\COBI`, branch `main`, HEAD `7f5eff1e46a8f0c03a36a11d6892231bf4927182`

## Verification results

| Area | Actual command / check | Result | Exit / classification |
|---|---|---|---|
| V4.2 research contracts, schemas, fixtures, D1.1 and release-audit path | `python -m pytest -q research/v4_2/tests/test_contracts_and_audit.py` | **13 passed** | 0 |
| Existing semantic tests | `backend/.venv/Scripts/python.exe -m pytest -q evidence_ai/tests/test_v4_1_semantics.py` | **7 passed** | 0 |
| Backend regression suite | `.venv/Scripts/python.exe -m pytest -q` from `backend/` | **35 passed, 2 failed** | 1; both stop at the existing V4.1 release-artifact checksum guard |
| V4.1 API tests | `.venv/Scripts/python.exe -m pytest -q tests/test_evidence_research_v41.py` from `backend/` | **0 passed, 2 failed** | 1; same TONG checksum guard; not bypassed |
| Frontend production build | `npm run build` from `frontend/` | **Passed; 1,637 modules transformed** | 0 |
| Frontend E2E | Not run | `COBI_E2E_URL` and disposable DB absent; checked-in flow writes synthetic case/review/consent records | `NOT_RUN`, not counted as passed |
| Read-only release audit | `python -m research.v4_2.tools.audit_release_integrity` | C hash matches; V4 and V4.1 mismatches reported without modifying manifests | 0; command's hard failure condition is the frozen C digest |
| Scoped artifact manifest | `python -m research.v4_2.tools.make_artifact_manifest --check` | **62/62 V4.2 scoped files match**; manifest self-hash excluded | 0 |

The research test count is 13 after adding a regression check that the audit helper uses the exact lowercase V4 manifest path. No test or helper changes the protected manifests or bypasses the backend guard.

## Frozen artifact and manifest results

| Artifact / snapshot | Current measured result |
|---|---|
| Frozen Generator C predictions: `reports/evidence-v4.1/data/generator-c-v1/C_PREDICTIONS_FROZEN.csv` | SHA-256 `03d1a2a6aa3d52eae483cca2d538e8cf71777eea17aa32215160bc5be3dc7523`; matches its recorded digest. No rescore/replay. |
| V4 `reports/evidence-v4/final_manifest.json` | **95/96** current files match. Mismatch: `frontend/src/EvidenceResearch.tsx`, expected `b3f7b74ec8ab8d1c773c970f5f31d3f2181c1f539fb968d37ab0fb4d7eff0947`, actual `54da9de3afae412a20a58e47578fd9ca89276f0f85c87c72bf02d9f21dd18db9`. |
| Separate V4 `reports/evidence-v4/ARTIFACT_MANIFEST.json` | **109/109** current inventory entries match; it does not supersede the 96-entry final manifest. |
| V4.1 committed `RELEASE_MANIFEST.json` at commit `e9102a7e9fb5b79edef1449eb869c7637f2e781f` | Snapshot has 14 source and 19 artifact entries. Using that commit's tree with Git checkout filters: **12/14 source digests and 19/19 artifact digests** match. The two same-commit source mismatches are `EXPERIMENT_PROTOCOL_C.md` and `experiment_protocol_c.json`. |
| V4.1 committed manifest applied to the current modified worktree | **13/14 sources, 9/19 artifacts** match current files; this is not the result for the historical commit tree. |
| V4.1 current modified worktree `RELEASE_MANIFEST.json` | **14/14 source, 51/52 artifact** checksums match. TONG is the single artifact mismatch. |
| Separate current untracked V4.1 `FINAL_MANIFEST.json` | **100/101** entries match. TONG is the single mismatch. The earlier verification log's 100/100 is a historical result for a prior snapshot. |
| V4.2 scoped `FINAL_ARTIFACT_MANIFEST.json` | **62 files**, hashes verified; scope is only `research/v4_2/`. |

Exact provenance, bytes, timestamps, supported cause assessment and owner decisions are in `RELEASE_INTEGRITY_RECONCILIATION.md` and `RELEASE_OWNER_APPROVAL_REQUEST.md`.

## Research artifact checks

- **D1.1:** 200 existing rows are marked stale-as-current; 100 are candidate omissions split train/validation/calibration/locked-test at 60/15/15/10. All 100 reviewer decisions remain blank and `PENDING_ADJUDICATION`; original gold is unchanged.
- **Literature:** scoped search and first-pass screen contain 28 ledger entries (26 unique studies/resources plus two explicit version/duplicate views). The new close-overlap screen includes FinFIRST, HC-RAG/Multi-Doc-2025, EvidenceLens and FinAgent. Search-result exports/counts and independent second screening are unavailable, so novelty remains `NOVELTY_UNESTABLISHED`.
- **Ontology and metrics:** five Draft 2020-12 schemas and eleven illustrative bundles pass the scoped suite. Pair, document and case denominators remain distinct; unknowns and unresolved attributions are explicit.
- **Statistics and policy:** statistical/sample-size plans are prospective drafts; epsilon, population, effect size and costs are unapproved. `RISK_THRESHOLD_PENDING_DOMAIN_APPROVAL` remains in force.
- **Preregistration:** `DRAFT_NOT_SEALED`; no independent timestamped registration or locked test labels exist.

## Controls and interpretation

No Generator C scoring/replay, model training, calibration or threshold change was performed. No unapproved gold labels, checkout logic or protected V4/V4.1 manifests were edited. No tracked/source files outside the V4.2 research directory were changed; the requested frontend build refreshed ignored generated output under `frontend/dist/`. The release audit helper's V4 path case was corrected inside the research namespace and covered by the additional research test.

The two API failures are real guard failures against a release manifest, not passes and not evidence of altered checkout behavior. E2E was not run. Phase 1 documentation is complete to the level supported by existing files and reproducible checks; Phase 2 remains blocked by release-owner decisions, independent labels/data, domain risk approvals and an independently screened novelty review.

